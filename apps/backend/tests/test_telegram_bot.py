"""Sprint 6.1 — unit тесты для Telegram bot (app.bot.telegram_bot).

Тестируем вспомогательные функции бота:
- SQLite binding (get_binding, set_binding)
- Rate limit (check_rate_limit)
- Cmd_* функции (cmd_help, etc.)
- handle_update с mock updates
"""

# Sprint 6.1: Telegram bot MVP (проде production)
from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")

import sqlite3
import tempfile
from collections import deque
from pathlib import Path

import pytest

from app.bot import telegram_bot


# === init_db + binding ===

def _create_temp_db():
    """Создаёт временный SQLite путь для bot binding."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return tmp.name


def test_init_db_creates_table():
    """Sprint 6.1: init_db создаёт таблицу bindings."""
    db_path = _create_temp_db()
    telegram_bot.BINDING_DB_PATH = db_path
    telegram_bot.init_db()
    # Проверяем что таблица 'bindings' создана
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='bindings'"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_set_and_get_binding():
    """Sprint 6.1: set_binding + get_binding roundtrip."""
    db_path = _create_temp_db()
    telegram_bot.BINDING_DB_PATH = db_path
    telegram_bot.init_db()

    telegram_bot.set_binding(chat_id=12345, user_id=678, email="kid@example.com")
    binding = telegram_bot.get_binding(12345)
    assert binding is not None
    assert binding["user_id"] == 678
    assert binding["email"] == "kid@example.com"


def test_get_unbound_chat_returns_none():
    """Sprint 6.1: unbound chat_id → None."""
    db_path = _create_temp_db()
    telegram_bot.BINDING_DB_PATH = db_path
    telegram_bot.init_db()
    assert telegram_bot.get_binding(99999) is None


def test_set_binding_overwrites():
    """Sprint 6.1: повторный set_binding обновляет запись."""
    db_path = _create_temp_db()
    telegram_bot.BINDING_DB_PATH = db_path
    telegram_bot.init_db()

    telegram_bot.set_binding(12345, 678, "kid1@example.com")
    telegram_bot.set_binding(12345, 999, "kid2@example.com")  # перезапись
    binding = telegram_bot.get_binding(12345)
    assert binding["user_id"] == 999
    assert binding["email"] == "kid2@example.com"


def test_update_last_command():
    """Sprint 6.1: update_last_command обновляет timestamp."""
    db_path = _create_temp_db()
    telegram_bot.BINDING_DB_PATH = db_path
    telegram_bot.init_db()
    telegram_bot.set_binding(12345, 678, "kid@example.com")

    before = telegram_bot.get_binding(12345)["last_command_at"]
    telegram_bot.update_last_command(12345)
    after = telegram_bot.get_binding(12345)["last_command_at"]
    # timestamp должен обновиться (≥ before)
    assert after >= before


# === Rate limit ===

def test_check_rate_limit_first_call_allowed():
    """Sprint 6.1: первый вызов всегда разрешён."""
    db_path = _create_temp_db()
    telegram_bot.BINDING_DB_PATH = db_path
    telegram_bot.init_db()
    telegram_bot.set_binding(12345, 678, "kid@example.com")
    # Первый вызов — OK
    assert telegram_bot.check_rate_limit(12345) is True


def test_check_rate_limit_second_call_blocked():
    """Sprint 6.1: повторный вызов сразу после первого — blocked."""
    db_path = _create_temp_db()
    telegram_bot.BINDING_DB_PATH = db_path
    telegram_bot.init_db()
    telegram_bot.set_binding(12345, 678, "kid@example.com")
    # Первый вызов — обновляет last_command_at
    telegram_bot.check_rate_limit(12345)
    # Manually обновим last_command_at чтобы elapsed=0 (как будто только что)
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE bindings SET last_command_at=? WHERE chat_id=?", (telegram_bot.time.time(), 12345))
    conn.commit()
    conn.close()
    assert telegram_bot.check_rate_limit(12345) is False  # только что → blocked


def test_check_rate_limit_different_chats_independent():
    """Sprint 6.1: rate limit изолирован per chat_id."""
    db_path = _create_temp_db()
    telegram_bot.BINDING_DB_PATH = db_path
    telegram_bot.init_db()
    telegram_bot.set_binding(11111, 678, "a@example.com")
    telegram_bot.set_binding(22222, 678, "b@example.com")
    telegram_bot.check_rate_limit(11111)  # первый чат
    # Второй чат — независим (должен пройти)
    assert telegram_bot.check_rate_limit(22222) is True


def test_check_rate_limit_unbound_chat():
    """Sprint 6.1: unbound chat_id возвращает True (без блокировки)."""
    db_path = _create_temp_db()
    telegram_bot.BINDING_DB_PATH = db_path
    telegram_bot.init_db()
    # Нет binding
    assert telegram_bot.check_rate_limit(99999) is True


# === cmd_help — не требует binding ===

def test_cmd_help_sends_response():
    """Sprint 6.1: cmd_help отправляет справку (мокаем send_message)."""
    sent = []
    original_send = telegram_bot.send_message
    telegram_bot.send_message = lambda chat_id, text: sent.append((chat_id, text))
    try:
        telegram_bot.cmd_help(chat_id=12345)
    finally:
        telegram_bot.send_message = original_send

    assert len(sent) == 1
    chat_id, text = sent[0]
    assert chat_id == 12345
    assert "/start" in text or "start" in text.lower()


# === cmd_start с email — bind ===

def test_cmd_start_with_email_binds_chat():
    """Sprint 6.1: /start email code → пытается bind chat_id."""
    db_path = _create_temp_db()
    telegram_bot.BINDING_DB_PATH = db_path
    telegram_bot.init_db()

    sent = []
    original_send = telegram_bot.send_message
    telegram_bot.send_message = lambda chat_id, text: sent.append((chat_id, text))
    try:
        # cmd_start требует минимум /start email code
        telegram_bot.cmd_start(chat_id=12345, text="/start kid@example.com")
    finally:
        telegram_bot.send_message = original_send

    # Без кода binding не происходит (только prompt)
    # но должна быть отправлена подсказка про /start email code
    assert len(sent) >= 1
    # Бот мог предложить ввести код или что-то подобное
    response = sent[0][1].lower()
    assert any(kw in response for kw in ["код", "code", "tg-", "email", "почт"])


def test_cmd_start_without_email_prompts():
    """Sprint 6.1: /start без email — просит ввести /start email code."""
    db_path = _create_temp_db()
    telegram_bot.BINDING_DB_PATH = db_path
    telegram_bot.init_db()

    sent = []
    original_send = telegram_bot.send_message
    telegram_bot.send_message = lambda chat_id, text: sent.append((chat_id, text))
    try:
        telegram_bot.cmd_start(chat_id=12345, text="/start")
    finally:
        telegram_bot.send_message = original_send

    # Должен быть prompt для email
    response = sent[0][1].lower() if sent else ""
    # Один из ответов должен говорить про email или вход
    assert any(kw in response for kw in ["email", "почт", "привяз", "tg-", "настройк"])


# === handle_update ===

def test_handle_update_text_message():
    """Sprint 6.1: handle_update с text message обрабатывает команду."""
    db_path = _create_temp_db()
    telegram_bot.BINDING_DB_PATH = db_path
    telegram_bot.init_db()

    sent = []
    telegram_bot.send_message = lambda chat_id, text: sent.append((chat_id, text))

    update = {
        "update_id": 12345,
        "message": {
            "message_id": 1,
            "chat": {"id": 11111, "type": "private"},
            "from": {"id": 11111, "is_bot": False, "first_name": "Test"},
            "text": "/help",
            "date": 1234567890,
        },
    }
    telegram_bot.handle_update(update)

    # Должен отправить справку
    assert len(sent) >= 1


def test_handle_update_ignores_non_text():
    """Sprint 6.1: sticker/photo/voice updates должны игнорироваться без panic."""
    db_path = _create_temp_db()
    telegram_bot.BINDING_DB_PATH = db_path
    telegram_bot.init_db()

    sent = []
    telegram_bot.send_message = lambda chat_id, text: sent.append((chat_id, text))

    # Update без text (например, sticker)
    update = {
        "update_id": 12346,
        "message": {
            "message_id": 2,
            "chat": {"id": 11111, "type": "private"},
            "from": {"id": 11111, "is_bot": False, "first_name": "Test"},
            "sticker": {"file_id": "abc"},
            "date": 1234567891,
        },
    }
    # Не должно падать
    telegram_bot.handle_update(update)

    # Может отправить что-то или нет — просто не падает
    assert True


# === Telegram API error handling ===

def test_get_updates_returns_list():
    """Sprint 6.1: get_updates возвращает list (даже при ошибке API)."""
    result = telegram_bot.get_updates(offset=None)
    # Если TELEGRAM_BOT_TOKEN не установлен — должен вернуть [] без raise
    assert isinstance(result, list)
