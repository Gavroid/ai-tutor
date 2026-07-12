"""Тесты OAuth endpoints (без реальных credentials)."""
from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    s = SessionLocal()
    user_service.register_user(
        s,
        UserCreate(
            email="kid@x.com",
            password="strongpass1",
            display_name="Kid",
            role="student",
            grade=7,
        ),
    )
    s.close()

    def _gen():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _gen
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_oauth_providers_endpoint(client):
    """GET /auth/oauth/providers возвращает список доступных провайдеров."""
    r = client.get("/api/v1/auth/oauth/providers")
    assert r.status_code == 200
    body = r.json()
    assert "providers" in body
    # Должны быть google, yandex, github
    names = [p["name"] for p in body["providers"]]
    assert "google" in names
    assert "yandex" in names
    assert "github" in names
    # Без credentials все configured=False
    assert all(p["configured"] is False for p in body["providers"])


def test_oauth_login_unknown_provider(client):
    """GET /auth/oauth/unknown/login → 404."""
    r = client.get("/api/v1/auth/oauth/unknown/login", follow_redirects=False)
    assert r.status_code == 404


def test_oauth_login_without_credentials(client):
    """GET /auth/oauth/google/login без OAUTH_GOOGLE_CLIENT_ID → 503."""
    r = client.get("/api/v1/auth/oauth/google/login", follow_redirects=False)
    assert r.status_code == 503
    assert "OAUTH_GOOGLE_CLIENT_ID" in r.json()["detail"]


def test_oauth_login_redirect_to_google(client, monkeypatch):
    """GET /auth/oauth/google/login с credentials → 302 redirect to Google."""
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_SECRET", "test-secret")

    r = client.get(
        "/api/v1/auth/oauth/google/login?redirect_to=/subjects",
        follow_redirects=False,
    )
    assert r.status_code == 307  # FastAPI redirect status
    assert "accounts.google.com" in r.headers["location"]
    assert "client_id=test-client-id" in r.headers["location"]
    assert "redirect_uri=" in r.headers["location"]
    assert "scope=openid" in r.headers["location"]
    assert "state=%2Fsubjects" in r.headers["location"]  # URL-encoded


def test_oauth_callback_invalid_code(client, monkeypatch):
    """GET /auth/oauth/google/callback с невалидным code → 400."""
    import httpx

    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_SECRET", "test-secret")

    # Мокаем httpx.AsyncClient чтобы вернуть ошибку
    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            import httpx

            req = httpx.Request("POST", "https://oauth2.googleapis.com/token")
            return httpx.Response(400, json={"error": "invalid_grant"}, request=req)

    monkeypatch.setattr("httpx.AsyncClient", FakeAsyncClient)

    r = client.get("/api/v1/auth/oauth/google/callback?code=fake", follow_redirects=False)
    assert r.status_code == 400
