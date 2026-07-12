"""Sprint 5.1 — Prometheus метрики для FastAPI.

Endpoint: GET /metrics — выдаёт текст в формате Prometheus.
Middleware автоматически собирает:
- http_requests_total{method, path, status}
- http_request_duration_seconds{method, path}
- ai_tokens_total{role} (input/output) — обновляется извне
"""
from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
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


def metrics_endpoint() -> Response:
    """Возвращает /metrics в формате Prometheus."""
    data = generate_latest()
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
