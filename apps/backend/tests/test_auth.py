"""Тесты Этапа 2: регистрация, вход, профиль, JWT, роли.

БД: SQLite in-memory, таблицы создаются через Base.metadata.create_all в фикстуре.
Это даёт реальные запросы SQL без поднятия Postgres в тестах.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from app.auth.security import get_current_user  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.users.models import User  # noqa: E402


@pytest.fixture()
def client():
    # Переиспользуем engine, настроенный через conftest.py на sqlite+pysqlite:///:memory:
    # Каждый тест получает чистую БД: drop → dispose → create.
    from app.db.session import engine as default_engine

    Base.metadata.drop_all(default_engine)
    default_engine.dispose()
    Base.metadata.create_all(default_engine)

    from app.db.session import SessionLocal

    def _override_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

    # Чистим таблицы после теста, чтобы fixture была изолированной
    Base.metadata.drop_all(default_engine)


def _register_student(c: TestClient, email="kirill@example.com", password="strongpass1", name="Кирилл"):
    return c.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": name, "role": "student", "grade": 7},
    )


def test_register_student_creates_profile(client):
    r = _register_student(client)
    assert r.status_code == 201, r.text
    user = r.json()
    assert user["email"] == "kirill@example.com"
    assert user["role"] == "student"
    assert user["display_name"] == "Кирилл"
    assert "password" not in user and "password_hash" not in user

    # Профиль ученика создался автоматически
    token = _login(client, "kirill@example.com", "strongpass1")
    r2 = client.get("/api/v1/students/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["grade"] == 7
    assert r2.json()["preferred_language"] == "ru"


def test_register_duplicate_email_returns_409(client):
    _register_student(client)
    r = _register_student(client, email="dup@example.com")
    assert r.status_code == 201
    r = _register_student(client, email="dup@example.com")
    assert r.status_code == 409


def test_admin_role_self_registration_blocked(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "evil@example.com", "password": "strongpass1", "display_name": "Bad", "role": "admin"},
    )
    assert r.status_code == 422  # validation error


def test_weak_password_rejected(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": "123", "display_name": "A", "role": "student"},
    )
    assert r.status_code == 422


def _login(c: TestClient, email: str, password: str) -> str:
    r = c.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_login_returns_jwt_pair(client):
    _register_student(client)
    r = client.post("/api/v1/auth/login", json={"email": "kirill@example.com", "password": "strongpass1"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and len(body["access_token"]) > 30
    assert isinstance(body["refresh_token"], str) and len(body["refresh_token"]) > 30
    assert body["expires_in"] > 0


def test_login_wrong_password_401(client):
    _register_student(client)
    # Правильная длина пароля, но неверное значение.
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "kirill@example.com", "password": "wrongpass99"},
    )
    assert r.status_code == 401


def test_me_requires_token(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_me_returns_current_user(client):
    _register_student(client)
    token = _login(client, "kirill@example.com", "strongpass1")
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "kirill@example.com"


def test_student_profile_update(client):
    _register_student(client)
    token = _login(client, "kirill@example.com", "strongpass1")
    r = client.patch(
        "/api/v1/students/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"grade": 7, "daily_minutes": 30, "learning_style": "step_by_step", "goals": "сдать контрольную"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["daily_minutes"] == 30
    assert body["learning_style"] == "step_by_step"
    assert body["goals"] == "сдать контрольную"


def test_parent_role_has_no_student_profile(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "mom@example.com", "password": "strongpass1", "display_name": "Мама", "role": "parent"},
    )
    token = _login(client, "mom@example.com", "strongpass1")
    r = client.get("/api/v1/students/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_invalid_token_rejected(client):
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


def test_health_still_ok(client):
    """Регрессия: эндпоинты Этапа 1 продолжают работать."""
    r = client.get("/health")
    assert r.status_code == 200