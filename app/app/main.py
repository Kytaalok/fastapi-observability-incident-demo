import asyncio
import json
import logging
import os
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest


REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0),
)
INFLIGHT_REQUESTS = Gauge(
    "http_inflight_requests",
    "Concurrent in-flight HTTP requests",
)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        extra = getattr(record, "_extra", None)
        if extra:
            entry.update(extra)
        if record.exc_info and record.exc_info[0] is not None:
            entry["exc_info"] = "".join(
                traceback.format_exception(*record.exc_info)
            )
        return json.dumps(entry, ensure_ascii=False)


def configure_logging() -> logging.Logger:
    log_file = Path(os.getenv("APP_LOG_FILE", "/var/log/app/app.log"))
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("obs-demo")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = JSONFormatter()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def log(level: int, event: str, **fields: object) -> None:
    record = logger.makeRecord(
        logger.name, level, "(app)", 0, event, (), None,
    )
    record._extra = fields  # type: ignore[attr-defined]
    logger.handle(record)


logger = configure_logging()
app = FastAPI(title="Observability Demo API", version="0.1.0")


KNOWN_PATHS = {"/" , "/health", "/metrics", "/slow", "/error", "/docs", "/openapi.json"}
SKIP_INSTRUMENTATION = {"/metrics", "/health"}


@app.middleware("http")
async def metrics_and_logging_middleware(request, call_next):
    path = request.url.path
    method = request.method

    if path in SKIP_INSTRUMENTATION:
        return await call_next(request)

    label_path = path if path in KNOWN_PATHS else "/unknown"

    start = time.perf_counter()
    status_code = "500"
    INFLIGHT_REQUESTS.inc()
    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    except Exception:
        logger.exception(
            "unhandled_exception",
            extra={"_extra": {"method": method, "path": path}},
        )
        raise
    finally:
        elapsed = time.perf_counter() - start
        duration_ms = round(elapsed * 1000, 2)
        REQUEST_COUNT.labels(method=method, path=label_path, status=status_code).inc()
        REQUEST_LATENCY.labels(method=method, path=label_path).observe(elapsed)
        INFLIGHT_REQUESTS.dec()
        log(
            logging.INFO, "request",
            method=method, path=path, status=status_code, duration_ms=duration_ms,
        )


@app.get("/")
async def root():
    return {"service": "observability-demo", "status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/slow")
async def slow(
    delay: float = Query(2.5, ge=0.0, le=20.0),
):
    log(logging.WARNING, "slow_endpoint", delay=delay)
    await asyncio.sleep(delay)
    return {"status": "ok", "delay": delay}


@app.get("/error")
async def error(
    code: int = Query(500, ge=500, le=599),
):
    log(logging.ERROR, "error_endpoint", code=code)
    return JSONResponse(
        status_code=code,
        content={"status": "error", "message": "synthetic failure", "code": code},
    )
