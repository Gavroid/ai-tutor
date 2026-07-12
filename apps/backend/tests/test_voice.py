"""Тесты voice transcription."""
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


def test_voice_requires_auth(client):
    """POST /voice/transcribe без auth → 401."""
    fake_audio = b"RIFF" + b"\x00" * 100  # WAV-like header
    r = client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("test.wav", fake_audio, "audio/wav")},
    )
    assert r.status_code == 401


def test_voice_rejects_unsupported_format(client):
    """POST /voice/transcribe с .txt → 400."""
    r = client.post(
        "/api/v1/voice/transcribe?language=ru",
        files={"file": ("test.txt", b"hello", "text/plain")},
        headers={"Authorization": f"Bearer {_login(client)}"},
    )
    assert r.status_code == 400
    assert "txt" in r.json()["detail"]


def test_voice_rejects_oversize(client):
    """Файл > 25 MB → 413."""
    r = client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("big.wav", b"\x00" * (26 * 1024 * 1024), "audio/wav")},
        headers={"Authorization": f"Bearer {_login(client)}"},
    )
    assert r.status_code == 413


def test_voice_no_engine_returns_503(client, monkeypatch):
    """Без WHISPER_API_URL и без whisper CLI → 503."""
    monkeypatch.delenv("WHISPER_API_URL", raising=False)

    r = client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("test.wav", b"RIFF" + b"\x00" * 100, "audio/wav")},
        headers={"Authorization": f"Bearer {_login(client)}"},
    )
    assert r.status_code == 503


def _login(c: TestClient) -> str:
    r = c.post(
        "/api/v1/auth/login",
        json={"email": "kid@x.com", "password": "strongpass1"},
    )
    return r.json()["access_token"]
