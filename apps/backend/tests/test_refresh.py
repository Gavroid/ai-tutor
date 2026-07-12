"""Тесты /auth/refresh."""
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
from app.users.models import User
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


def _login(client, email="kid@x.com", password="strongpass1"):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    return r.json()


def test_refresh_with_valid_token(client):
    pair = _login(client)
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]})
    assert r.status_code == 200
    new_pair = r.json()
    assert "access_token" in new_pair
    assert "refresh_token" in new_pair
    assert "expires_in" in new_pair
    # expires_in должен быть > 0
    assert new_pair["expires_in"] > 0


def test_refresh_with_access_token_rejected(client):
    """Нельзя использовать access_token как refresh_token."""
    pair = _login(client)
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": pair["access_token"]})
    assert r.status_code == 401
    assert "refresh" in r.text.lower()


def test_refresh_with_invalid_token(client):
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token-xxxxxxxx"})
    assert r.status_code == 401


def test_refresh_with_short_token_rejected(client):
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": "abc"})
    assert r.status_code == 422  # Pydantic валидирует


def test_new_access_token_works(client):
    """Refresh → новый access — им можно пользоваться."""
    pair = _login(client)
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]})
    new_pair = r.json()

    # /me с новым токеном
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_pair['access_token']}"})
    assert r.status_code == 200
    assert r.json()["email"] == "kid@x.com"


def test_refresh_for_inactive_user_rejected(client):
    """Деактивированный user не может обновить токен."""
    pair = _login(client)
    s = SessionLocal()
    try:
        user = s.query(User).filter_by(email="kid@x.com").first()
        user.is_active = False
        s.commit()
    finally:
        s.close()

    r = client.post("/api/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]})
    assert r.status_code == 401


def test_refresh_missing_token_field(client):
    """Без поля refresh_token → 422."""
    r = client.post("/api/v1/auth/refresh", json={})
    assert r.status_code == 422
