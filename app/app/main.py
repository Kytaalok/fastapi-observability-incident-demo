import asyncio
import logging
import os
import time
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
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
INFLIGHT_REQUESTS = Gauge(
    "http_inflight_requests",
    "Concurrent in-flight HTTP requests",
)


def configure_logging() -> logging.Logger:
    log_file = Path(os.getenv("APP_LOG_FILE", "/var/log/app/app.log"))
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("obs-demo")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s level=%(levelname)s name=%(name)s %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = configure_logging()
app = FastAPI(title="Observability Demo API", version="0.1.0")


@app.middleware("http")
async def metrics_and_logging_middleware(request, call_next):
    start = time.perf_counter()
    path = request.url.path
    method = request.method
    status_code = "500"
    INFLIGHT_REQUESTS.inc()
    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    except Exception:
        logger.exception("unhandled_exception method=%s path=%s", method, path)
        raise
    finally:
        elapsed = time.perf_counter() - start
        REQUEST_COUNT.labels(method=method, path=path, status=status_code).inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
        INFLIGHT_REQUESTS.dec()
        logger.info(
            "request method=%s path=%s status=%s duration_ms=%.2f",
            method,
            path,
            status_code,
            elapsed * 1000,
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
    logger.warning("slow_endpoint delay=%s", delay)
    await asyncio.sleep(delay)
    return {"status": "ok", "delay": delay}


@app.get("/error")
async def error(
    code: int = Query(500, ge=500, le=599),
):
    logger.error("error_endpoint code=%s", code)
    return JSONResponse(
        status_code=code,
        content={"status": "error", "message": "synthetic failure", "code": code},
    )
