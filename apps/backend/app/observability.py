"""Sprint 5.1 — Prometheus метрики для FastAPI.

Endpoint: GET /metrics — выдаёт текст в формате Prometheus.
Middleware автоматически собирает:
- http_requests_total{method, path, status}
- http_request_duration_seconds{method, path}
- ai_tokens_total{role} (input/output) — обновляется извне
"""

from __future__ import annotations

import shutil
import time
from collections.abc import Callable
from pathlib import Path

from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)

# === Метрики ===

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

AI_TOKENS_TOTAL = Counter(
    "ai_tokens_total",
    "Total AI tokens consumed",
    ["role"],  # input / output
)

AI_REQUESTS_TOTAL = Counter(
    "ai_requests_total",
    "Total AI requests",
    ["mode", "status"],  # mode: explain/hint/check/generate/chat; status: ok/error
)

ACTIVE_SESSIONS = Counter(
    "active_sessions_total",
    "Cumulative session events (login/register)",
    ["event"],  # login / register / logout
)

OPS_DB_UP = Gauge("ai_tutor_db_up", "Database probe status: 1=up, 0=down")
OPS_REDIS_UP = Gauge("ai_tutor_redis_up", "Redis probe status: 1=up, 0=down")
OPS_UPLOAD_DISK_USED_PERCENT = Gauge(
    "ai_tutor_upload_disk_used_percent",
    "Disk used percent for the upload filesystem",
)
OPS_BACKUP_LATEST_AGE_SECONDS = Gauge(
    "ai_tutor_backup_latest_age_seconds",
    "Age of the latest production backup manifest in seconds; -1 means not visible",
)


# === Ops probes for Stage 23 alertability ===


def _probe_db() -> float:
    try:
        from sqlalchemy import text

        from app.db.session import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return 1.0
    except Exception:
        return 0.0


def _probe_redis() -> float:
    try:
        import os

        import redis as redis_lib

        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        client = redis_lib.Redis.from_url(redis_url, socket_timeout=2)
        try:
            return 1.0 if client.ping() else 0.0
        finally:
            client.close()
    except Exception:
        return 0.0


def _upload_dir_path() -> Path:
    try:
        from app.config import get_settings

        return Path(get_settings().upload_dir)
    except Exception:
        return Path("/app/uploads")


def _backup_out_path() -> Path:
    import os

    return Path(os.environ.get("OPS_BACKUP_OUT_PATH", "/app/ops/backup_out"))


def _latest_backup_age_seconds() -> float:
    try:
        candidates = sorted(
            _backup_out_path().glob("manifest-*.md5"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    except Exception:
        return -1.0
    if not candidates:
        return -1.0
    return max(0.0, time.time() - candidates[0].stat().st_mtime)


def collect_ops_metrics() -> dict[str, float]:
    upload_path = _upload_dir_path()
    usage = shutil.disk_usage(upload_path if upload_path.exists() else "/")
    disk_used_pct = round(((usage.total - usage.free) / usage.total) * 100, 4) if usage.total else 0.0
    return {
        "ai_tutor_db_up": _probe_db(),
        "ai_tutor_redis_up": _probe_redis(),
        "ai_tutor_upload_disk_used_percent": disk_used_pct,
        "ai_tutor_backup_latest_age_seconds": _latest_backup_age_seconds(),
    }


def update_ops_metrics() -> None:
    metrics = collect_ops_metrics()
    OPS_DB_UP.set(metrics["ai_tutor_db_up"])
    OPS_REDIS_UP.set(metrics["ai_tutor_redis_up"])
    OPS_UPLOAD_DISK_USED_PERCENT.set(metrics["ai_tutor_upload_disk_used_percent"])
    OPS_BACKUP_LATEST_AGE_SECONDS.set(metrics["ai_tutor_backup_latest_age_seconds"])


# === Middleware ===

# Пути, которые не нужно логировать (шум)
_IGNORE_PATHS = frozenset({"/metrics", "/health", "/ready", "/"})


def _route_template(request: Request) -> str:
    """Получить template пути (например /api/v1/teacher/materials/{material_id}).

    Если не нашли — используем path (но обрезаем длинные id-сегменты чтобы
    не плодить cardinality).
    """
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    # fallback: обрезаем очевидные id
    p = request.url.path
    parts = p.split("/")
    cleaned = []
    for part in parts:
        if part.isdigit() and len(part) > 2:
            cleaned.append("{id}")
        else:
            cleaned.append(part)
    return "/".join(cleaned)


async def metrics_middleware(request: Request, call_next: Callable) -> Response:
    """FastAPI middleware — собирает HTTP-метрики.

    NOTE: В FastAPI middleware call_next — coroutine, нужен await.
    """
    if request.url.path in _IGNORE_PATHS:
        return await call_next(request)

    method = request.method
    start = time.time()
    status = 500  # default если exception
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        duration = time.time() - start
        path = _route_template(request)
        HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status=str(status)).inc()
        HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(duration)


def metrics_payload() -> bytes:
    """Return Prometheus text payload, aggregating workers when multiprocess is enabled."""
    import os

    update_ops_metrics()
    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if multiproc_dir and os.path.isdir(multiproc_dir):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry)
    return generate_latest()


def metrics_endpoint() -> Response:
    """Возвращает /metrics в формате Prometheus."""
    data = metrics_payload()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


# === Утилиты для AI-вызовов ===


def record_ai_request(mode: str, status: str, input_tokens: int = 0, output_tokens: int = 0) -> None:
    """Регистрирует AI-запрос и его токены.

    mode: explain/hint/check/generate/chat
    status: ok/error
    """
    AI_REQUESTS_TOTAL.labels(mode=mode, status=status).inc()
    if input_tokens:
        AI_TOKENS_TOTAL.labels(role="input").inc(input_tokens)
    if output_tokens:
        AI_TOKENS_TOTAL.labels(role="output").inc(output_tokens)
