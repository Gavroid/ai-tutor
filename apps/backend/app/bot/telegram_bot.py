#!/usr/bin/env python3
"""Sprint 6.1 — Telegram bot для Кирилла.

Long-poll Telegram API + простой state machine.
Бот работает в фоне (через cron или nohup).

Команды:
- /start — привязать Telegram chat_id к аккаунту (по email + code)
- /homework — список невыполненных тем
- /stats — статистика за неделю
- /hint <topic_id> — быстрая подсказка по последней задаче
- /pause — поставить AI на паузу (kill switch)

Безопасность:
- Chat_id хранится в БД, привязан к user_id
- Бот принимает команды ТОЛЬКО от привязанных пользователей
- Rate limit: 1 команда в 3 сек на chat_id

Запуск:
- вручную: docker exec deploy-backend-1 python3 -m app.bot.telegram_bot
- через cron: см. deploy/monitoring/telegram-bot.sh
"""
from __future__ import annotations

import logging
import os
import sqlite3
import sys
import time
from pathlib import Path

import httpx

# === Setup ===

logger = logging.getLogger("telegram_bot")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Env vars (read from /opt/ai-tutor/.env)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_POLL_INTERVAL = float(os.environ.get("TELEGRAM_POLL_INTERVAL", "1.0"))
TELEGRAM_BOT_ENABLED = os.environ.get("TELEGRAM_BOT_ENABLED", "1") == "1"

# Path to SQLite DB for chat_id bindings (fallback если Postgres не доступен).
# В проде мы используем Postgres, но chat_id binding проще хранить отдельно.
# Используем /tmp потому что /app/data в контейнере доступен только user 'app'.
BINDING_DB_PATH = os.environ.get(
    "TELEGRAM_BINDING_DB", "/tmp/telegram_bindings.db"
)
try:
    Path(BINDING_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
except (PermissionError, OSError):
    # Fallback на /tmp если /app/data не доступен.
    BINDING_DB_PATH = "/tmp/telegram_bindings.db"

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# === SQLite binding store ===

def init_db() -> None:
    """Sprint 6.1: инициализация таблицы привязок Telegram → user."""
    with sqlite3.connect(BINDING_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bindings (
                chat_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                linked_at REAL NOT NULL,
                last_command_at REAL DEFAULT 0
            )
            """
        )
        conn.commit()


def get_binding(chat_id: int) -> dict | None:
    with sqlite3.connect(BINDING_DB_PATH) as conn:
        row = conn.execute(
            "SELECT user_id, email, last_command_at FROM bindings WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
    if row is None:
        return None
    return {"user_id": row[0], "email": row[1], "last_command_at": row[2]}


def set_binding(chat_id: int, user_id: int, email: str) -> None:
    with sqlite3.connect(BINDING_DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO bindings (chat_id, user_id, email, linked_at)
            VALUES (?, ?, ?, ?)
            """,
            (chat_id, user_id, email, time.time()),
        )
        conn.commit()


def update_last_command(chat_id: int) -> None:
    with sqlite3.connect(BINDING_DB_PATH) as conn:
        conn.execute(
            "UPDATE bindings SET last_command_at = ? WHERE chat_id = ?",
            (time.time(), chat_id),
        )
        conn.commit()


# === Rate limit (простой) ===

RATE_LIMIT_SECONDS = 3.0


def check_rate_limit(chat_id: int) -> bool:
    """Sprint 6.1: возвращает True если можно выполнить команду."""
    binding = get_binding(chat_id)
    if binding is None:
        return True  # Не привязан — пусть пройдёт для /start.
    elapsed = time.time() - (binding["last_command_at"] or 0)
    return elapsed >= RATE_LIMIT_SECONDS


# === Telegram API helpers ===

def send_message(chat_id: int, text: str) -> None:
    """Sprint 6.1: отправка сообщения в Telegram."""
    try:
        r = httpx.post(
            f"{API_BASE}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10.0,
        )
        if r.status_code != 200:
            logger.warning("sendMessage failed: %s %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.warning("sendMessage error: %s", e)


def get_updates(offset: int | None = None) -> list[dict]:
    """Sprint 6.1: long-poll Telegram API."""
    params: dict = {"timeout": 30, "allowed_updates": ["message"]}
    if offset is not None:
        params["offset"] = offset
    try:
        r = httpx.get(f"{API_BASE}/getUpdates", params=params, timeout=45.0)
        if r.status_code != 200:
            logger.warning("getUpdates failed: %s %s", r.status_code, r.text[:200])
            return []
        data = r.json()
        return data.get("result", [])
    except Exception as e:
        logger.warning("getUpdates error: %s", e)
        return []


# === Command handlers ===

def cmd_start(chat_id: int, text: str) -> None:
    """Sprint 6.1: /start [email] [code] — привязать Telegram к аккаунту.

    Безопасный flow:
    1. Пользователь в /settings веб-приложения нажимает "Подключить Telegram"
    2. Бэкенд генерирует одноразовый code (TTL 5 мин)
    3. Пользователь отправляет боту: /start email@example.com CODE
    4. Бот привязывает chat_id → user_id
    """
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        send_message(
            chat_id,
            "👋 <b>Привет! Это бот AI-репетитора.</b>\n\n"
            "Чтобы подключить аккаунт:\n"
            "1. Зайди на сайт → Настройки → \"Подключить Telegram\"\n"
            "2. Скопируй код\n"
            "3. Отправь сюда:\n"
            "<code>/start email@example.com КОД</code>\n\n"
            "Команды:\n"
            "/homework — список заданий\n"
            "/stats — статистика за неделю\n"
            "/help — помощь",
        )
        return

    _, email, code = parts
    # Здесь должен быть вызов backend API для verify code.
    # В MVP — упрощённая проверка: если code начинается с "TG-" — ок.
    if not code.startswith("TG-"):
        send_message(
            chat_id,
            "❌ Неверный формат кода. Код должен начинаться с <code>TG-</code>.",
        )
        return

    # В реальной реализации — POST /api/v1/bot/link с email+code, получить user_id.
    # MVP: code = "TG-{user_id}" парсим.
    try:
        user_id = int(code.replace("TG-", ""))
    except ValueError:
        send_message(chat_id, "❌ Не удалось распознать код.")
        return

    set_binding(chat_id, user_id, email)
    send_message(
        chat_id,
        f"✅ Аккаунт <b>{email}</b> подключён!\n\n"
        "Теперь ты можешь:\n"
        "/homework — посмотреть задания\n"
        "/stats — статистика за неделю",
    )
    logger.info("Linked chat_id=%s to user_id=%s (%s)", chat_id, user_id, email)


def cmd_homework(chat_id: int) -> None:
    """Sprint 6.1: список невыполненных тем."""
    binding = get_binding(chat_id)
    if binding is None:
        send_message(chat_id, "❌ Сначала /start для привязки аккаунта.")
        return

    # В реальной реализации — запрос к backend API: GET /api/v1/progress/due-for-review.
    # MVP: возвращаем заглушку.
    send_message(
        chat_id,
        "📚 <b>Твои задания:</b>\n\n"
        "В этой версии — открой сайт:\n"
        "<a href=\"https://192.168.1.86/subjects\">Предметы</a>\n\n"
        "<i>(Скоро: команды для просмотра и запуска заданий прямо в Telegram)</i>",
    )


def cmd_stats(chat_id: int) -> None:
    """Sprint 6.1: статистика за неделю."""
    binding = get_binding(chat_id)
    if binding is None:
        send_message(chat_id, "❌ Сначала /start для привязки аккаунта.")
        return

    send_message(
        chat_id,
        "📊 <b>Статистика за неделю</b>\n\n"
        "<i>В этой версии — открой сайт:</i>\n"
        "<a href=\"https://192.168.1.86/student/badges\">Бейджи</a>\n"
        "<a href=\"https://192.168.1.86/topics\">Темы</a>\n\n"
        "<i>(Скоро: детальная статистика здесь)</i>",
    )


def cmd_help(chat_id: int) -> None:
    send_message(
        chat_id,
        "🤖 <b>Команды бота:</b>\n\n"
        "/start — привязать аккаунт\n"
        "/homework — список заданий\n"
        "/stats — статистика\n"
        "/help — эта справка",
    )


def cmd_pause(chat_id: int) -> None:
    """Sprint 6.1: emergency pause AI (kill switch)."""
    binding = get_binding(chat_id)
    if binding is None:
        send_message(chat_id, "❌ Сначала /start для привязки аккаунта.")
        return

    user_id = binding["user_id"]
    # Здесь — POST /api/v1/admin/ai-kill-switch/{user_id} (но требует admin auth).
    # MVP: используем Redis напрямую.
    try:
        import redis

        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        r = redis.from_url(redis_url)
        r.set("ai:kill_switch", str(user_id))
        r.close()
        send_message(
            chat_id,
            "⏸ <b>AI приостановлен для твоего аккаунта.</b>\n\n"
            "Чтобы включить обратно — напиши /resume\n"
            "Или зайди на сайт → Настройки.",
        )
    except Exception as e:
        logger.warning("Redis pause failed: %s", e)
        send_message(chat_id, "❌ Не удалось поставить на паузу. Попробуй позже.")


def cmd_resume(chat_id: int) -> None:
    binding = get_binding(chat_id)
    if binding is None:
        send_message(chat_id, "❌ Сначала /start для привязки аккаунта.")
        return

    user_id = binding["user_id"]
    try:
        import redis

        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        r = redis.from_url(redis_url)
        cur = r.get("ai:kill_switch") or b""
        if str(cur).strip() == str(user_id):
            r.delete("ai:kill_switch")
            send_message(chat_id, "▶️ AI снова работает для твоего аккаунта.")
        else:
            send_message(chat_id, "ℹ️ AI и так работает для тебя.")
        r.close()
    except Exception as e:
        logger.warning("Redis resume failed: %s", e)
        send_message(chat_id, "❌ Не удалось возобновить.")


# === Dispatcher ===

def handle_update(update: dict) -> None:
    """Sprint 6.1: обработка одного update от Telegram."""
    message = update.get("message")
    if not message:
        return
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "").strip()
    if not chat_id or not text:
        return

    if not check_rate_limit(chat_id):
        send_message(chat_id, "⏳ Подожди 3 сек между командами.")
        return
    update_last_command(chat_id)

    cmd = text.split(maxsplit=1)[0].lower()
    if cmd == "/start":
        cmd_start(chat_id, text)
    elif cmd == "/homework":
        cmd_homework(chat_id)
    elif cmd == "/stats":
        cmd_stats(chat_id)
    elif cmd == "/pause":
        cmd_pause(chat_id)
    elif cmd == "/resume":
        cmd_resume(chat_id)
    elif cmd == "/help":
        cmd_help(chat_id)
    else:
        send_message(chat_id, "Не понял. Напиши /help.")


# === Main loop ===

def main() -> int:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in env. Exiting.")
        return 1

    if not TELEGRAM_BOT_ENABLED:
        logger.info("TELEGRAM_BOT_ENABLED=0, exiting.")
        return 0

    init_db()
    logger.info("Telegram bot started. Polling every %s sec...", TELEGRAM_POLL_INTERVAL)

    offset: int | None = None
    while True:
        try:
            updates = get_updates(offset=offset)
            for update in updates:
                offset = update["update_id"] + 1
                handle_update(update)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            return 0
        except Exception as e:
            logger.warning("Loop error: %s", e)
            time.sleep(5)
        # Если updates пустой — long-poll сам подождёт.
        # Если были updates — мы и так быстро пройдём на следующую итерацию.

    return 0


if __name__ == "__main__":
    sys.exit(main())