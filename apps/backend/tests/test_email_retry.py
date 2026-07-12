"""Тесты email retry (Этап hardening)."""
from __future__ import annotations

import os

# setdefault — не перезаписывает существующее значение
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")
# SMTP_URL — модульный уровень, но гарантируем что он стоит
os.environ.setdefault("SMTP_URL", "smtp://user:pass@smtp.example.com:587")

import asyncio
import pytest
from unittest.mock import patch

from app.db.session import Base, SessionLocal, engine, get_db
from app.notifications import models as notif_models
from app.notifications import service
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture(autouse=True)
def _ensure_smtp_url(monkeypatch):
    """Гарантируем SMTP_URL установлен для каждого теста в этом модуле."""
    monkeypatch.setenv("SMTP_URL", "smtp://user:pass@smtp.example.com:587")
    yield


@pytest.fixture()
def db():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    s = SessionLocal()
    try:
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
    finally:
        s.close()

    def _gen():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    from app.main import app

    app.dependency_overrides[get_db] = _gen
    yield SessionLocal
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_email_sent_on_first_attempt(db):
    """Если SMTP работает — статус 'sent' с первой попытки."""
    with patch("app.notifications.service._send_via_smtp") as mock:
        mock.return_value = None  # успех

        s = db()
        try:
            rec = asyncio.run(
                service.send_email(
                    s,
                    user_id=1,
                    to_email="kid@example.com",
                    subject="Test",
                    body="Body",
                )
            )
            # Проверяем внутри сессии, потом закрываем
            assert rec.status == "sent"
            assert rec.error is None
            assert mock.call_count == 1
        finally:
            s.close()


def test_email_retries_on_failure(db):
    """Если SMTP падает 2 раза, потом успех — статус 'sent'."""
    with patch("app.notifications.service._send_via_smtp") as mock:
        mock.side_effect = [Exception("conn reset"), Exception("timeout"), None]

        s = db()
        try:
            with patch("asyncio.sleep"):
                rec = asyncio.run(
                    service.send_email(
                        s,
                        user_id=1,
                        to_email="kid@example.com",
                        subject="Test",
                        body="Body",
                    )
                )
            assert rec.status == "sent"
            assert rec.error is None
            assert mock.call_count == 3
        finally:
            s.close()


def test_email_fails_after_max_retries(db):
    """Если SMTP падает всегда — статус 'failed', error содержит последнюю ошибку."""
    with patch("app.notifications.service._send_via_smtp") as mock:
        mock.side_effect = Exception("permanent failure")

        s = db()
        try:
            with patch("asyncio.sleep"):
                rec = asyncio.run(
                    service.send_email(
                        s,
                        user_id=1,
                        to_email="kid@example.com",
                        subject="Test",
                        body="Body",
                        max_retries=3,
                    )
                )
            assert rec.status == "failed"
            assert "permanent failure" in rec.error
            assert mock.call_count == 3
        finally:
            s.close()


def test_email_dry_run_without_smtp(db, monkeypatch):
    """Если SMTP_URL не задан — статус 'dry_run', без retries."""
    monkeypatch.delenv("SMTP_URL", raising=False)

    s = db()
    try:
        rec = asyncio.run(
            service.send_email(
                s,
                user_id=1,
                to_email="kid@example.com",
                subject="Test",
                body="Body",
            )
        )
        assert rec.status == "dry_run"
        assert "SMTP_URL" in rec.error
    finally:
        s.close()


def test_email_records_audit_trail_in_db(db):
    """EmailNotification запись в БД сохраняется независимо от результата."""
    with patch("app.notifications.service._send_via_smtp") as mock:
        mock.side_effect = Exception("failed")

        s = db()
        try:
            with patch("asyncio.sleep"):
                asyncio.run(
                    service.send_email(
                        s,
                        user_id=1,
                        to_email="kid@example.com",
                        subject="Important",
                        body="Body",
                        max_retries=2,
                    )
                )
        finally:
            s.close()

    # Проверяем в НОВОЙ сессии
    s2 = SessionLocal()
    try:
        records = s2.query(notif_models.EmailNotification).all()
        assert len(records) == 1
        assert records[0].status == "failed"
        assert "failed" in records[0].error
    finally:
        s2.close()
