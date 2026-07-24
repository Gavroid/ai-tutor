"""Sprint 16.0 — обновлённые unit тесты для Telegram bot.

Переход с SQLite (/tmp) на PostgreSQL (telegram_bindings).
Тесты используют основную in-memory DB фикстуру (shared с backend).
"""
from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "mock-token-for-tests")
os.environ.setdefault("TELEGRAM_DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.bot import telegram_bot
from app.users.models import User, Role
from app.auth.security import hash_password


@pytest.fixture
def db_session():
    """Sprint 16.0: in-memory SQLite с telegram_bindings таблицей."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    # Создаём минимальные таблицы для теста
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                display_name VARCHAR(255) NOT NULL DEFAULT '',
                role VARCHAR(20) NOT NULL DEFAULT 'student',
                is_active BOOLEAN NOT NULL DEFAULT 1
            )
        """))
        conn.execute(text("""
            CREATE TABLE telegram_bindings (
                chat_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                code VARCHAR(20),
                expires_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        # Создаём тестового пользователя
        conn.execute(text(
            "INSERT INTO users (email, password_hash, display_name, role, is_active) "
            "VALUES (:e, :p, 'Kid', 'student', 1)"
        ), {"e": "kid@example.com", "p": hash_password("testpass1")})

    # Подменяем engine в боте
    telegram_bot._engine = engine
    return engine


def test_init_db_creates_table(db_session):
    """Sprint 16.0: init_db создаёт telegram_bindings если её нет."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    telegram_bot._engine = engine
    telegram_bot.init_db()
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='telegram_bindings'"
        )).fetchone()
    assert row is not None


def test_set_and_get_binding(db_session):
    """Sprint 16.0: set_binding + get_binding roundtrip через PostgreSQL."""
    telegram_bot.set_binding(chat_id=12345, user_id=1, code="ABC123")
    binding = telegram_bot.get_binding(12345)
    assert binding is not None
    assert binding["user_id"] == 1
    assert binding["code"] == "ABC123"


def test_get_unbound_chat_returns_none(db_session):
    """Sprint 16.0: unbound chat_id → None."""
    assert telegram_bot.get_binding(99999) is None


def test_set_binding_overwrites(db_session):
    """Sprint 16.0: повторный set_binding обновляет запись (ON CONFLICT)."""
    telegram_bot.set_binding(chat_id=12345, user_id=1, code="FIRST")
    telegram_bot.set_binding(chat_id=12345, user_id=1, code="SECOND")
    binding = telegram_bot.get_binding(12345)
    assert binding["code"] == "SECOND"


def test_update_last_command(db_session):
    """Sprint 16.0: update_last_command обновляет timestamp."""
    telegram_bot.set_binding(chat_id=12345, user_id=1)
    before = telegram_bot.get_binding(12345)["last_command_at"]
    telegram_bot.update_last_command(12345)
    after = telegram_bot.get_binding(12345)["last_command_at"]
    assert after >= before


def test_handle_update_requires_binding(db_session, monkeypatch):
    """Sprint 16.0: /homework без binding → 'сначала /start'."""
    sent = []
    monkeypatch.setattr(telegram_bot, "send_message", lambda cid, text: sent.append((cid, text)))

    update = {"message": {"chat": {"id": 99999}, "text": "/homework"}}
    telegram_bot.handle_update(update)
    assert any("привяжи" in t for _, t in sent)


def test_handle_update_ignores_non_text(db_session, monkeypatch):
    """Sprint 16.0: updates без текста игнорируются."""
    sent = []
    monkeypatch.setattr(telegram_bot, "send_message", lambda cid, text: sent.append(text))

    update = {"message": {"chat": {"id": 12345}, "photo": []}}  # no text
    telegram_bot.handle_update(update)
    assert sent == []


def test_handle_update_routes_help(db_session, monkeypatch):
    """Sprint 16.0: /help отвечает справкой."""
    sent = []
    monkeypatch.setattr(telegram_bot, "send_message", lambda cid, text: sent.append(text))

    update = {"message": {"chat": {"id": 12345}, "text": "/help"}}
    telegram_bot.handle_update(update)
    assert any("/homework" in t and "/start" in t for t in sent)
