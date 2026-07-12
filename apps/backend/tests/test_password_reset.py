"""Тесты password reset flow."""
from __future__ import annotations

import os

os.environ["APP_SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["AI_API_KEY"] = "mock-key-for-tests"
os.environ.pop("SMTP_URL", None)

import pytest
from fastapi.testclient import TestClient

from app.auth import password_reset
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.users import service as user_service
from app.users.models import User
from app.users.schemas import UserCreate


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine); engine.dispose(); Base.metadata.create_all(engine)

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


def test_request_reset_existing_email(client):
    r = client.post("/api/v1/auth/password-reset/request", json={"email": "kid@x.com"})
    assert r.status_code == 200
    assert "ok" in r.json()
    # Токен должен быть в БД
    s = SessionLocal()
    try:
        from app.auth.password_reset_models import PasswordResetToken

        tokens = s.query(PasswordResetToken).all()
        assert len(tokens) == 1
        assert tokens[0].used is False
        assert tokens[0].expires_at is not None
    finally:
        s.close()


def test_request_reset_nonexistent_email_returns_200(client):
    """Анти-енумерация: для несуществующего email тоже возвращаем 200."""
    r = client.post("/api/v1/auth/password-reset/request", json={"email": "nope@x.com"})
    assert r.status_code == 200
    # И не создаётся токен
    s = SessionLocal()
    try:
        from app.auth.password_reset_models import PasswordResetToken

        tokens = s.query(PasswordResetToken).all()
        assert len(tokens) == 0
    finally:
        s.close()


def test_full_reset_flow_via_direct(client):
    """Прямой вызов сервиса для генерации токена и подтверждения."""
    s = SessionLocal()
    raw_token = password_reset.request_reset(s, "kid@x.com")
    s.close()
    assert raw_token is not None
    assert len(raw_token) > 30

    s = SessionLocal()
    ok = password_reset.confirm_reset(s, raw_token, "newpassword2")
    s.close()
    assert ok is True


def test_old_password_no_longer_works(client):
    """После сброса старый пароль не работает."""
    s = SessionLocal()
    raw_token = password_reset.request_reset(s, "kid@x.com")
    s.close()
    assert raw_token

    s = SessionLocal()
    ok = password_reset.confirm_reset(s, raw_token, "newpassword2")
    s.close()
    assert ok

    # Старый пароль больше не работает
    r = client.post("/api/v1/auth/login", json={"email": "kid@x.com", "password": "strongpass1"})
    assert r.status_code == 401
    # Новый пароль работает
    r = client.post("/api/v1/auth/login", json={"email": "kid@x.com", "password": "newpassword2"})
    assert r.status_code == 200


def test_expired_token_rejected(client):
    """Просроченный токен → False."""
    import secrets
    from datetime import datetime, timedelta, timezone

    from app.auth.password_reset import _hash_token
    from app.auth.password_reset_models import PasswordResetToken

    s = SessionLocal()
    try:
        user = s.query(User).filter_by(email="kid@x.com").first()
        raw_token = secrets.token_urlsafe(32)
        rec = PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=2),
            used=False,
        )
        s.add(rec)
        s.commit()
    finally:
        s.close()

    s = SessionLocal()
    ok = password_reset.confirm_reset(s, raw_token, "newpass22")
    s.close()
    assert ok is False


def test_used_token_rejected(client):
    """Использованный токен → повторно использовать нельзя."""
    import secrets
    from datetime import datetime, timedelta, timezone

    from app.auth.password_reset import _hash_token
    from app.auth.password_reset_models import PasswordResetToken

    s = SessionLocal()
    try:
        user = s.query(User).filter_by(email="kid@x.com").first()
        raw_token = secrets.token_urlsafe(32)
        rec = PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            used=True,
        )
        s.add(rec)
        s.commit()
    finally:
        s.close()

    s = SessionLocal()
    ok = password_reset.confirm_reset(s, raw_token, "newpass22")
    s.close()
    assert ok is False


def test_rate_limit_on_request(client):
    """5+ запросов в час → новый токен не создаётся."""
    import secrets
    from datetime import datetime, timedelta, timezone

    from app.auth.password_reset_models import PasswordResetToken

    s = SessionLocal()
    try:
        user = s.query(User).filter_by(email="kid@x.com").first()
        for _ in range(5):
            rec = PasswordResetToken(
                user_id=user.id,
                token_hash=secrets.token_hex(32),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            s.add(rec)
        s.commit()
    finally:
        s.close()

    r = client.post("/api/v1/auth/password-reset/request", json={"email": "kid@x.com"})
    assert r.status_code == 200

    s = SessionLocal()
    try:
        count = s.query(PasswordResetToken).count()
        assert count == 5  # всё ещё 5
    finally:
        s.close()


def test_confirm_short_password_blocked_at_api_level(client):
    """Pydantic валидирует min_length=8 на API уровне → 422."""
    import secrets
    from datetime import datetime, timedelta, timezone

    from app.auth.password_reset import _hash_token
    from app.auth.password_reset_models import PasswordResetToken

    s = SessionLocal()
    try:
        user = s.query(User).filter_by(email="kid@x.com").first()
        raw_token = secrets.token_urlsafe(32)
        rec = PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            used=False,
        )
        s.add(rec)
        s.commit()
    finally:
        s.close()

    r = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "short"},
    )
    assert r.status_code == 422


def test_token_single_use(client):
    """Один токен можно использовать только ОДИН раз."""
    s = SessionLocal()
    raw_token = password_reset.request_reset(s, "kid@x.com")
    s.close()

    # Использовали первый раз
    s = SessionLocal()
    ok1 = password_reset.confirm_reset(s, raw_token, "newpassword2")
    s.close()
    assert ok1 is True

    # Пытаемся использовать снова
    s = SessionLocal()
    ok2 = password_reset.confirm_reset(s, raw_token, "another3")
    s.close()
    assert ok2 is False


def test_inactive_user_cant_reset(client):
    """Деактивированный user не может сбросить пароль."""
    s = SessionLocal()
    try:
        user = s.query(User).filter_by(email="kid@x.com").first()
        user.is_active = False
        s.commit()
    finally:
        s.close()

    r = client.post("/api/v1/auth/password-reset/request", json={"email": "kid@x.com"})
    assert r.status_code == 200  # анти-енумерация
    # Но токен не создаётся
    s = SessionLocal()
    try:
        from app.auth.password_reset_models import PasswordResetToken

        # Получим токен — None (т.к. юзер неактивный)
        raw = password_reset.request_reset(s, "kid@x.com")
        assert raw is None
    finally:
        s.close()
