"""Тесты каркаса (Этап 1): healthcheck, OpenAPI, CORS.

БД в этих тестах не нужна — healthcheck не обращается к ней, /ready проверим
как smoke (если SQLite доступна — готов, иначе 503 — это нормально).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_serves_metadata() -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "AI Tutor 7"
    assert body["health"] == "/health"
    assert body["docs"] == "/docs"


def test_health_always_ok() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    # Новые поля
    assert "version" in body
    assert "uptime_seconds" in body
    assert "started_at" in body
    assert body["uptime_seconds"] >= 0
    # started_at должен быть ISO 8601
    assert "T" in body["started_at"]


def test_ready_endpoint_responds() -> None:
    """ready должен вернуть структурированный ответ в любом случае."""
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["status"] in {"ready", "not_ready"}


def test_openapi_available() -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    assert "/health" in spec["paths"]
    assert "/ready" in spec["paths"]


def test_cors_preflight() -> None:
    r = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    # FastAPI/Starlette CORS middleware отвечает 200 на preflight
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"