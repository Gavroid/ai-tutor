"""Sprint 7.2: voice rate-limit."""
from __future__ import annotations

import io
from collections import deque

import pytest
from fastapi.testclient import TestClient

from app.auth.security import create_access_token
from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.users import service as user_service
from app.users.schemas import UserCreate
from app.voice import router as voice_router


@pytest.fixture(autouse=True)
def reset_rate_limit():
    """Между тестами очищаем in-memory rate-limit state."""
    voice_router._voice_calls.clear()
    yield
    voice_router._voice_calls.clear()


@pytest.fixture()
def authed_student():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        user = user_service.register_user(
            db,
            UserCreate(
                email="voice-test@example.com",
                password="strongpass1",
                display_name="VoiceKid",
                role="student",
                grade=7,
            ),
        )
        db.commit()
        token, _ = create_access_token(user)
        return {"user_id": user.id, "token": token}
    finally:
        db.close()


def _wav_bytes() -> bytes:
    """Минимальный fake .wav (RIFF-заголовок + немного данных)."""
    return b"RIFF" + b"\x00" * 36 + b"\x00" * 100


class TestVoiceRateLimit:
    """/voice/transcribe возвращает 429 после 20 calls/min."""

    def test_under_limit_allowed(self, authed_student):
        """19 calls подряд без 429."""
        c = TestClient(app)
        token = authed_student["token"]
        for i in range(19):
            r = c.post(
                "/api/v1/voice/transcribe",
                files={"file": ("test.wav", io.BytesIO(_wav_bytes()), "audio/wav")},
                headers={"Authorization": f"Bearer {token}"},
            )
            # Принимаем 200 (если есть WHISPER) ИЛИ 503 (если не настроен),
            # ГЛАВНОЕ — НЕ 429.
            assert r.status_code != 429, f"Call #{i+1} неожиданно 429"

    def test_over_limit_returns_429(self, authed_student, monkeypatch):
        """На 21-м вызове — 429."""
        import time
        c = TestClient(app)
        token = authed_student["token"]
        # Заполняем 20-ю записями СЕЙЧАС (внутри окна).
        voice_router._voice_calls.clear()
        now = time.time()
        voice_router._voice_calls[authed_student["user_id"]] = deque(
            [now - i * 0.1 for i in range(20)]
        )
        r = c.post(
            "/api/v1/voice/transcribe",
            files={"file": ("test.wav", io.BytesIO(_wav_bytes()), "audio/wav")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 429
        assert "rate limit" in r.json()["detail"].lower()

    def test_separate_users_independent(self, authed_student):
        """Rate-limit per-user, не общий."""
        import time
        now = time.time()
        voice_router._voice_calls[authed_student["user_id"]] = deque(
            [now - i * 0.1 for i in range(20)]
        )
        # Этот user уже заблокирован.
        c = TestClient(app)
        token = authed_student["token"]
        r = c.post(
            "/api/v1/voice/transcribe",
            files={"file": ("test.wav", io.BytesIO(_wav_bytes()), "audio/wav")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 429
        # Другой user — НЕ заблокирован.
        db = SessionLocal()
        try:
            other = user_service.register_user(
                db,
                UserCreate(
                    email="other@example.com",
                    password="strongpass1",
                    display_name="Other",
                    role="student",
                    grade=7,
                ),
            )
            db.commit()
            other_token, _ = create_access_token(other)
        finally:
            db.close()
        r = c.post(
            "/api/v1/voice/transcribe",
            files={"file": ("test.wav", io.BytesIO(_wav_bytes()), "audio/wav")},
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert r.status_code != 429

    def test_anonymous_401(self, authed_student):
        """Без токена — 401 (rate-limit не должен ломать auth)."""
        c = TestClient(app)
        r = c.post(
            "/api/v1/voice/transcribe",
            files={"file": ("test.wav", io.BytesIO(_wav_bytes()), "audio/wav")},
        )
        assert r.status_code in (401, 403)
