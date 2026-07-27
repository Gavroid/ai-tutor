"""Sprint 72: voice endpoint error handling tests.

Sprint 16.1 P1-5 already added proper error handling:
- 413: file too large
- 503: OPENAI_API_KEY not configured
- 504: Whisper API timeout
- 502: Whisper API HTTP error / 5xx / config error
"""
from __future__ import annotations

import io
import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


# === Module-level tests ===

def test_max_audio_size_constant_exists():
    """Sprint 72: MAX_AUDIO_SIZE_BYTES constant defined."""
    from app.voice.router import MAX_AUDIO_SIZE_BYTES

    assert MAX_AUDIO_SIZE_BYTES == 25 * 1024 * 1024  # 25 MB


def test_whisper_api_url_defined():
    """Sprint 72: WHISPER_API_URL defined."""
    from app.voice.router import WHISPER_API_URL

    assert "transcriptions" in WHISPER_API_URL or "whisper" in WHISPER_API_URL.lower()


# === Fixtures ===

@pytest.fixture
def client():
    """Sprint 72: TestClient + DB setup."""
    from app.db.session import engine, Base
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def user_token(client):
    """Sprint 72: student token."""
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.users.models import User, Role
    from app.auth.security import hash_password

    with Session(engine) as db:
        user = User(
            email="user@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="User",
            role=Role.STUDENT,
            is_active=True,
        )
        db.add(user)
        db.commit()

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "Kirill2026!"},
    )
    return r.json()["access_token"]


# === Tests: 413 file too large ===

def test_voice_file_too_large_returns_413(client, user_token):
    """Sprint 72: file > 25 MB → 413."""
    large_content = b"x" * (26 * 1024 * 1024)  # 26 MB
    files = {"file": ("large.webm", io.BytesIO(large_content), "audio/webm")}

    r = client.post(
        "/api/v1/voice/transcribe",
        files=files,
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 413
    assert "слишком большой" in r.json()["detail"].lower() or "too large" in str(r.json()["detail"]).lower()


# === Tests: 503 OPENAI_API_KEY not configured ===

def test_voice_no_api_key_returns_503(client, user_token):
    """Sprint 72: OPENAI_API_KEY missing → 503 (не fallback заглушка)."""
    files = {"file": ("test.webm", io.BytesIO(b"fake audio"), "audio/webm")}

    with patch.dict(os.environ, {}, clear=False):
        # Remove both keys
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("WHISPER_API_KEY", None)

        r = client.post(
            "/api/v1/voice/transcribe",
            files=files,
            headers={"Authorization": f"Bearer {user_token}"},
        )
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "asr_not_configured"


# === Tests: 504 timeout ===

def test_voice_whisper_timeout_returns_504(client, user_token):
    """Sprint 72: Whisper API timeout → 504."""
    import httpx
    files = {"file": ("test.webm", io.BytesIO(b"fake audio"), "audio/webm")}

    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        with patch("app.voice.router.httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client.return_value = mock_instance

            r = client.post(
                "/api/v1/voice/transcribe",
                files=files,
                headers={"Authorization": f"Bearer {user_token}"},
            )
    assert r.status_code == 504
    assert r.json()["detail"]["code"] == "asr_timeout"


# === Tests: 502 HTTP error ===

def test_voice_whisper_500_returns_502(client, user_token):
    """Sprint 72: Whisper API 500 → 502."""
    import httpx
    files = {"file": ("test.webm", io.BytesIO(b"fake audio"), "audio/webm")}

    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        with patch("app.voice.router.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            r = client.post(
                "/api/v1/voice/transcribe",
                files=files,
                headers={"Authorization": f"Bearer {user_token}"},
            )
    assert r.status_code == 502
    assert r.json()["detail"]["code"] in ("asr_unavailable", "asr_configuration_error")


# === Tests: auth required ===

def test_voice_requires_auth(client):
    """Sprint 72: /voice/transcribe требует auth."""
    files = {"file": ("test.webm", io.BytesIO(b"fake audio"), "audio/webm")}
    r = client.post("/api/v1/voice/transcribe", files=files)
    assert r.status_code == 401
