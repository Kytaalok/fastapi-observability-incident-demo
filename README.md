# Observability + Incident Demo (Prometheus + Grafana + Loki)

Демо-проект на FastAPI в стиле DevOps/SRE: метрики, логи, алерты и минимальный `runbook` для разбора инцидента.

## Что в проекте

- FastAPI-сервис с эндпоинтами `/health`, `/metrics`, `/slow`, `/error`
- Prometheus (`scrape` + `alert rules`)
- Grafana (готовый dashboard JSON)
- Loki + Promtail (сбор логов приложения)
- `RUNBOOK.md` с шагами triage/диагностики

## Архитектура

`Docker Compose -> FastAPI (/metrics, /slow, /error) -> Prometheus (scrape + alerts) -> Grafana dashboard`

`Docker Compose -> Promtail -> Loki -> Grafana Logs`

## Стек

- FastAPI
- `prometheus-client`
- Prometheus
- Grafana
- Loki
- Promtail
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
- Loki Ready (опционально): `http://localhost:3100/ready`

## Сценарий Демо Инцидента

1. Открой Grafana dashboard `Observability Incident Demo`.
2. Дай немного обычного трафика:

```bash
curl.exe http://localhost:8000/health
```

3. Сгенерируй 5xx (повтори несколько раз):

```bash
curl.exe http://localhost:8000/error
```

4. Сгенерируй высокую задержку:

```bash
curl.exe "http://localhost:8000/slow?delay=2"
```

5. Проверь:

- алерты в Prometheus UI
- панели Grafana (`RPS`, `5xx ratio`, `p95/p99`)
- логи в Loki (панель `Application Logs`)
- шаги разбора в `RUNBOOK.md`

## Что Делает `docker compose up --build`

- Собирает контейнер FastAPI-приложения из `app/Dockerfile`
- Поднимает сервис приложения (`app`) с логированием в файл
- Поднимает Prometheus и загружает `prometheus/prometheus.yml` + `prometheus/alerts.yml`
- Поднимает Loki и Promtail для сбора логов приложения
- Поднимает Grafana и автоматически подключает datasource'ы (Prometheus, Loki)
- Автоматически импортирует dashboard `grafana/dashboards/observability.json`

## Управление

```bash
docker compose up -d
docker compose down
docker compose ps
docker compose logs -f app
docker compose restart app
```

## Проверки И Отладка

Проверка эндпоинтов приложения:

```bash
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/metrics
curl.exe http://localhost:8000/error
curl.exe "http://localhost:8000/slow?delay=2"
```

Проверка таргетов Prometheus:

- `http://localhost:9090/targets`

Проверка алертов:

- `http://localhost:9090/alerts`

Проверка логов приложения через Docker:

```bash
docker compose logs -f app
```

Проверка готовности Loki:

```bash
curl.exe http://localhost:3100/ready
```

## Структура Проекта

```text
.
|-- docker-compose.yml
|-- Vagrantfile
|-- .gitignore
|-- README.md
|-- RUNBOOK.md
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
