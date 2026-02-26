# Observability + Incident Demo (Prometheus + Grafana + Loki)

Демо-проект на FastAPI в стиле DevOps/SRE: метрики, структурированные JSON-логи, алерты и `RUNBOOK.md` для разбора инцидента.

## Что в проекте

- FastAPI-сервис с эндпоинтами `/health`, `/metrics`, `/slow`, `/error`
- Structured JSON logging с фильтрацией по полям в Loki
- Prometheus (`scrape` + `alert rules`: `High5xxRate`, `HighLatencyP95`)
- Grafana (dashboard с 5 панелями: RPS, 5xx ratio, latency p95/p99, логи, ошибки)
- Loki + Promtail (сбор и парсинг JSON-логов, label `level` для индексной фильтрации)
- `RUNBOOK.md` с шагами triage/диагностики и готовыми LogQL-запросами

## Архитектура

```
Docker Compose -> FastAPI (/metrics, /slow, /error) -> Prometheus (scrape + alerts) -> Grafana dashboard
Docker Compose -> FastAPI (JSON logs) -> Promtail (pipeline: json → labels) -> Loki -> Grafana Logs
```

## Стек

- FastAPI + `prometheus-client`
- Prometheus v2.51.2
- Grafana v10.4.3
- Loki v2.9.8 + Promtail v2.9.8
- Docker / Docker Compose

## Быстрый старт

Запуск всего стека:

```bash
docker compose up --build
```

Открыть UI:

- Swagger UI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Prometheus: `http://localhost:9090`
- Prometheus Alerts: `http://localhost:9090/alerts`
- Grafana: `http://localhost:3000` (`admin` / `admin`)
- Loki Ready: `http://localhost:3100/ready`

## Сценарий Демо Инцидента

1. Открой Grafana dashboard `Observability Incident Demo`.
2. Дай немного обычного трафика:

```bash
curl http://localhost:8000/
```

3. Сгенерируй 5xx (повтори несколько раз):

```bash
curl http://localhost:8000/error
curl 'http://localhost:8000/error?code=503'
```

4. Сгенерируй высокую задержку:

```bash
curl "http://localhost:8000/slow?delay=3"
```

5. Проверь:

- алерты в Prometheus UI (`http://localhost:9090/alerts`)
- панели Grafana (`RPS`, `5xx ratio`, `p95/p99`)
- логи в панели `Application Logs` — JSON с полями `method`, `path`, `status`, `duration_ms`
- ошибки в панели `Errors & Warnings` — только `level=ERROR` и `level=WARNING`
- шаги разбора в `RUNBOOK.md`

## Логирование

Приложение пишет JSON-логи:

```json
{"timestamp": "2026-02-24T23:05:37.676Z", "level": "INFO", "logger": "obs-demo", "event": "request", "method": "GET", "path": "/slow", "status": "200", "duration_ms": 106.18}
```

Promtail извлекает `level` как Loki label. Остальные поля парсятся через LogQL `| json`.

Примеры LogQL-запросов:

```
{job="app"} | json                                          # все логи с парсингом полей
{job="app", level="ERROR"} | json                           # только ошибки
{job="app", level="WARNING"} | json | event="slow_endpoint" # медленные запросы
{job="app"} | json | duration_ms > 1000                     # запросы дольше 1 секунды
```

## Метрики

- `http_requests_total` (Counter) — method, path, status
- `http_request_duration_seconds` (Histogram) — бакеты до 20s
- `http_inflight_requests` (Gauge) — текущие запросы

Эндпоинты `/metrics` и `/health` исключены из инструментирования.
Неизвестные пути нормализуются в `/unknown` для защиты от высокой кардинальности.

## Алерты Prometheus

| Алерт | Условие | Длительность |
|-------|---------|--------------|
| `High5xxRate` | 5xx ratio > 5% | 1 минута |
| `HighLatencyP95` | p95 latency > 1s | 2 минуты |

## Управление

```bash
docker compose up -d          # запуск в фоне
docker compose down           # остановка
docker compose ps             # статус контейнеров
docker compose logs -f app    # логи приложения
docker compose restart app    # перезапуск приложения
```

## Проверки и отладка

```bash
curl http://localhost:8000/health                  # health check
curl http://localhost:8000/metrics                  # метрики Prometheus
curl http://localhost:8000/error                    # синтетическая ошибка 500
curl 'http://localhost:8000/error?code=503'         # синтетическая ошибка 503
curl "http://localhost:8000/slow?delay=3"           # задержка 3 секунды
curl http://localhost:3100/ready                    # готовность Loki
```

Таргеты Prometheus: `http://localhost:9090/targets`

## Структура проекта

```text
.
|-- docker-compose.yml
|-- Vagrantfile
|-- README.md
|-- RUNBOOK.md
|-- UPDATE.md
|-- app
|   |-- Dockerfile
|   |-- requirements.txt
|   `-- app
|       |-- __init__.py
|       `-- main.py
|-- prometheus
|   |-- prometheus.yml
|   `-- alerts.yml
|-- grafana
|   |-- dashboards
|   |   `-- observability.json
|   `-- provisioning
|       |-- dashboards
|       |   `-- dashboards.yml
|       `-- datasources
|           `-- datasources.yml
|-- loki
|   `-- loki-config.yml
`-- promtail
    `-- promtail-config.yml
```

## Примечания

- Алерты вычисляются локально в Prometheus (без Alertmanager в MVP).
- Следующий шаг для развития проекта: добавить Alertmanager + webhook/Telegram/Slack уведомления.
