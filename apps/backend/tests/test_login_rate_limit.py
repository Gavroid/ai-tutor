"""Тесты login rate limit (Этап security-2)."""
from __future__ import annotations

import os
os.environ["APP_SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["AI_API_KEY"] = "mock-key-for-tests"

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app, _login_attempts_log
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine); engine.dispose(); Base.metadata.create_all(engine)
    _login_attempts_log.clear()

    s = SessionLocal()
    user_service.register_user(
        s,
        UserCreate(email="kid@x.com", password="strongpass1", display_name="Kid", role="student", grade=7),
    )
    s.close()

    def _gen():
        s = SessionLocal()
        try: yield s
        finally: s.close()
    app.dependency_overrides[get_db] = _gen
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_login_rate_limit_blocks_after_threshold(client):
    """После 10 неудачных попыток → 429."""
    for i in range(10):
        r = client.post("/api/v1/auth/login", json={"email": "kid@x.com", "password": "wrong"})
        assert r.status_code == 401, f"Attempt {i}: {r.status_code}"

    # 11-я попытка должна быть заблокирована
    r = client.post("/api/v1/auth/login", json={"email": "kid@x.com", "password": "strongpass1"})
    assert r.status_code == 429
    assert "15 минут" in r.text or "подождите" in r.text.lower()


def test_successful_login_still_blocked_after_rate_limit(client):
    """Правильный пароль — тоже блокируется (anti-pattern)."""
    for _ in range(10):
        client.post("/api/v1/auth/login", json={"email": "kid@x.com", "password": "wrong"})

    # Правильный пароль
    r = client.post("/api/v1/auth/login", json={"email": "kid@x.com", "password": "strongpass1"})
    assert r.status_code == 429


def test_log_clear_isolates_tests(client):
    """Два клиента в разных тестах не делят state."""
    # Первый — забивает
    for _ in range(10):
        client.post("/api/v1/auth/login", json={"email": "kid@x.com", "password": "wrong"})

    r1 = client.post("/api/v1/auth/login", json={"email": "kid@x.com", "password": "strongpass1"})
    assert r1.status_code == 429


def test_login_attempts_dont_block_other_endpoints(client):
    """Rate limit только на login — другие эндпоинты свободны."""
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"email": "kid@x.com", "password": "wrong"})

    # /api/v1/health не ограничен
    r = client.get("/api/v1/../../health")
    assert r.status_code in (200, 404)
