#!/usr/bin/env python3
"""Sprint 6.1 — Telegram bot для Кирилла.

Sprint 16.0 P0-2: bindings теперь в PostgreSQL (telegram_bindings),
а не в SQLite /tmp. /tmp терялся при docker compose restart.

Long-poll Telegram API + простой state machine.

Команды:
- /start — привязать Telegram chat_id к аккаунту (по email + code)
- /homework — список невыполненных тем
- /stats — статистика за неделю
- /hint <topic_id> — быстрая подсказка по последней задаче
- /pause — поставить AI на паузу (kill switch)

Безопасность:
- Chat_id хранится в PostgreSQL (telegram_bindings), persistent.
- Бот принимает команды ТОЛЬКО от привязанных пользователей
- Rate limit: 1 команда в 3 сек на chat_id

Запуск:
- вручную: docker exec deploy-backend-1 python3 -m app.bot.telegram_bot
- через cron: см. deploy/monitoring/telegram-bot.sh
"""

from __future__ import annotations

import logging
import os
import secrets
import sys
import time
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import create_engine, text

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

# Sprint 16.0 P0-2: используем PostgreSQL через тот же DATABASE_URL,
# что и backend. Persistent, не теряется при рестарте.
DATABASE_URL = os.environ.get(
    "TELEGRAM_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql+psycopg2://tutor:tutor@db:5432/tutor"),
)

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# === PostgreSQL binding store ===
# Sprint 16.0: переход с SQLite /tmp на PostgreSQL telegram_bindings.
# Преимущества: persistent + shared с backend (можно проверить в админке).

_engine = None


def get_engine():
    """Lazy engine init — переиспользуется в long-running bot."""
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    return _engine


def init_db() -> None:
    """Sprint 16.0: инициализация telegram_bindings (если ещё нет).

    Sprint 3.23: добавил telegram_bind_codes для /start <email> <code> flow.

    Использует engine из app.db.session — единый с SessionLocal — чтобы
    таблицы были видны через те же соединения, что и users (важно для
    SQLite in-memory тестов, где разные engine = разные БД в памяти).
    """
    from app.db.session import engine

    with engine.begin() as conn:
        # Sprint 16.0: создаём таблицу если её нет (на случай если миграция
        # 0014 не была применена). Используем CURRENT_TIMESTAMP для
        # совместимости с SQLite (для тестов) и PostgreSQL (для прода).
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS telegram_bindings (
                chat_id BIGINT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                code VARCHAR(20),
                expires_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_telegram_bindings_user_id ON telegram_bindings(user_id)"))
        # Sprint 3.23: таблица одноразовых кодов для /start <email> <code>.
        # Admin/CLI генерирует код, user шлёт /start email code — код становится used.
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS telegram_bind_codes (
                id BIGINT PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                code VARCHAR(8) NOT NULL,
                issued_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_telegram_bind_codes_email ON telegram_bind_codes(email)"))
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_telegram_bind_codes_active "
                "ON telegram_bind_codes(email) WHERE used_at IS NULL"
            )
        )


# Sprint 3.23: SQL-константы для тестов и переиспользования.
_SQL_ACTIVE_CODES_FOR_EMAIL = (
    "SELECT id, code, expires_at, used_at FROM telegram_bind_codes "
    "WHERE email = :email AND used_at IS NULL AND expires_at > CURRENT_TIMESTAMP"
)

_BIND_CODE_TTL_MINUTES = 15


def issue_code(*, email: str) -> str:
    """Sprint 3.23: выдать/вернуть 8-hex-char code для email.

    - Если уже есть активный (не used, не expired) — возвращает его (один код
      за раз; повторная выдача не плодит дубликатов).
    - Если нет — генерирует новый через secrets.token_hex(4).
    - Email должен принадлежать существующему user'у (иначе ValueError —
      иначе атакующий мог бы перебирать коды для несуществующих email'ов).

    Контракт: вызывает init_db() чтобы убедиться что таблицы telegram_* есть.
    НЕ делает drop_all/create_all — это на совести caller'а (на проде
    alembic upgrade head, в тестах — фикстура).
    """
    from app.db.session import SessionLocal, engine
    from app.users.models import User

    init_db()  # CREATE TABLE IF NOT EXISTS — idempotent

    email = email.strip().lower()
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email, is_active=True).first()
        if user is None:
            raise ValueError(f"no active user with email={email!r}")

        with engine.begin() as conn:
            from sqlalchemy import text

            # Возвращаем существующий активный код, если есть
            existing = conn.execute(text(_SQL_ACTIVE_CODES_FOR_EMAIL), {"email": email}).fetchone()
            if existing is not None:
                return existing[1]

            # Генерируем новый. Сначала гасим старые активные (race-safe).
            new_code = secrets.token_hex(4)  # 8 hex chars, 32-bit entropy
            conn.execute(
                text(
                    "UPDATE telegram_bind_codes SET used_at = CURRENT_TIMESTAMP "
                    "WHERE email = :email AND used_at IS NULL"
                ),
                {"email": email},
            )
            # SQLite требует ROWID explicit, Postgres — serial. Используем явный id.
            next_id_row = conn.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM telegram_bind_codes")).fetchone()
            next_id = next_id_row[0] if next_id_row else 1
            # Для Postgres — CURRENT_TIMESTAMP возвращает tz-aware время.
            # Для SQLite — naive. expires_at сравниваем в Python.
            conn.execute(
                text(
                    "INSERT INTO telegram_bind_codes (id, email, code, issued_by, expires_at) "
                    "VALUES (:id, :email, :code, :issued_by, :expires_at)"
                ),
                {
                    "id": next_id,
                    "email": email,
                    "code": new_code,
                    "issued_by": user.id,
                    # Передаём ISO-строку чтобы быть tz-compatible и с SQLite, и с Postgres.
                    "expires_at": (datetime.now(UTC) + timedelta(minutes=_BIND_CODE_TTL_MINUTES)).isoformat(),
                },
            )
        return new_code
    finally:
        db.close()


def validate_and_bind(*, email: str, code: str, chat_id: int) -> int:
    """Sprint 3.23: проверить code + создать binding.

    Возвращает user_id при успехе. Бросает ValueError если:
    - user не существует или не активен
    - code не найден / expired / already used
    - binding уже есть для другого user'а под этим chat_id
    """
    from app.db.session import SessionLocal, engine
    from app.users.models import User

    init_db()  # CREATE TABLE IF NOT EXISTS — idempotent

    email = email.strip().lower()
    code = code.strip().lower()

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email, is_active=True).first()
        if user is None:
            raise ValueError(f"unknown or inactive user: {email!r}")

        with engine.begin() as conn:
            from sqlalchemy import text

            now_iso = datetime.now(UTC).isoformat()
            row = conn.execute(
                text(
                    "SELECT id, expires_at FROM telegram_bind_codes "
                    "WHERE email = :email AND code = :code AND used_at IS NULL "
                    "ORDER BY id DESC LIMIT 1"
                ),
                {"email": email, "code": code},
            ).fetchone()
            if row is None:
                raise ValueError("invalid or already-used code")
            # row[1] — expires_at, либо naive либо tz-aware ISO. Парсим и сравниваем.
            expires = row[1]
            if isinstance(expires, str):
                # SQLite хранит TIMESTAMP как ISO string. Парсим.
                from datetime import datetime as _dt

                try:
                    expires_dt = _dt.fromisoformat(expires)
                except ValueError:
                    # Fallback: POSIX timestamp
                    expires_dt = _dt.utcfromtimestamp(float(expires))
                if expires_dt.tzinfo is None:
                    expires_dt = expires_dt.replace(tzinfo=UTC)
            else:
                expires_dt = expires
                if expires_dt.tzinfo is None:
                    expires_dt = expires_dt.replace(tzinfo=UTC)
            if expires_dt <= datetime.now(UTC):
                raise ValueError("code expired")

            # Помечаем код как использованный
            conn.execute(
                text("UPDATE telegram_bind_codes SET used_at = :now WHERE id = :id"),
                {"now": now_iso, "id": row[0]},
            )
            # Upsert binding (chat_id PRIMARY KEY → ON CONFLICT UPDATE).
            # Если chat_id уже привязан к другому user'у — переписываем.
            conn.execute(
                text(
                    """
                    INSERT INTO telegram_bindings (chat_id, user_id, code, expires_at, updated_at)
                    VALUES (:chat_id, :user_id, :code, NULL, CURRENT_TIMESTAMP)
                    ON CONFLICT (chat_id) DO UPDATE
                    SET user_id = :user_id, code = :code, updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "chat_id": chat_id,
                    "user_id": user.id,
                    "code": code,
                },
            )
        return user.id
    finally:
        db.close()


def get_binding(chat_id: int) -> dict | None:
    """Sprint 16.0: чтение binding из PostgreSQL."""
    with get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT user_id, code, updated_at FROM telegram_bindings WHERE chat_id = :cid"),
            {"cid": chat_id},
        ).fetchone()
    if row is None:
        return None
    return {
        "user_id": row[0],
        "code": row[1],
        "last_command_at": _parse_ts(row[2]),
    }


def _parse_ts(value) -> float:
    """Sprint 16.0: timestamp парсинг (PostgreSQL datetime vs SQLite string)."""
    if value is None:
        return 0.0
    if hasattr(value, "timestamp"):
        return value.timestamp()
    # SQLite хранит datetime как строку
    try:
        from datetime import datetime

        return datetime.fromisoformat(str(value).replace(" ", "T")).timestamp()
    except (ValueError, TypeError):
        return 0.0


def set_binding(chat_id: int, user_id: int, code: str | None = None) -> None:
    """Sprint 16.0: upsert binding в PostgreSQL."""
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
            INSERT INTO telegram_bindings (chat_id, user_id, code, expires_at, updated_at)
            VALUES (:cid, :uid, :code, NULL, CURRENT_TIMESTAMP)
            ON CONFLICT (chat_id) DO UPDATE
            SET user_id = EXCLUDED.user_id,
                code = EXCLUDED.code,
                updated_at = CURRENT_TIMESTAMP
            """
            ),
            {"cid": chat_id, "uid": user_id, "code": code},
        )


def update_last_command(chat_id: int) -> None:
    """Sprint 16.0: обновление timestamp последней команды."""
    with get_engine().begin() as conn:
        conn.execute(
            text("UPDATE telegram_bindings SET updated_at = CURRENT_TIMESTAMP WHERE chat_id = :cid"), {"cid": chat_id}
        )


# === Rate limit (простой) ===

RATE_LIMIT_SECONDS = 3.0


def check_rate_limit(chat_id: int) -> bool:
    """Sprint 6.1: возвращает True если можно выполнить команду."""
    binding = get_binding(chat_id)
    if not binding:
        return True  # Не привязан — /start покажет ошибку
    last = binding.get("last_command_at", 0)
    return (time.time() - last) >= RATE_LIMIT_SECONDS


# === Telegram API helpers ===


def tg_call(method: str, **params) -> dict:
    """Прямой вызов Telegram Bot API."""
    url = f"{API_BASE}/{method}"
    r = httpx.post(url, json=params, timeout=10.0)
    return r.json()


def send_message(chat_id: int, text: str, parse_mode: str = "HTML") -> None:
    """Sprint 6.1: отправляет сообщение в Telegram."""
    if len(text) > 4000:
        text = text[:4000] + "..."
    try:
        tg_call("sendMessage", chat_id=chat_id, text=text, parse_mode=parse_mode)
    except Exception as e:
        logger.warning("sendMessage failed: %s", e)


# === Commands ===


def cmd_start(chat_id: int, args: list[str]) -> None:
    """Sprint 6.1: /start email code — привязка chat_id к user.

    Ожидает: /start <email> <code>
    Код — 6-значный, admin генерирует через /admin или CLI.
    """
    if len(args) < 2:
        send_message(
            chat_id,
            "👋 <b>Привет!</b>\n\n"
            "Чтобы привязать Telegram к учётке:\n"
            "<code>/start your@email.com 123456</code>\n\n"
            "Код попроси у админа (через /admin → Telegram codes).",
        )
        return

    email = args[0].strip().lower()
    code = args[1].strip()

    # Sprint 3.23: вместо сломанного /api/v1/auth/telegram-bind (endpoint
    # отсутствовал с давних спринтов, handler шёл POST → 404) — напрямую
    # валидируем code в той же Postgres (telegram_bind_codes) и upsert binding
    # в telegram_bindings. Shared DATABASE_URL.
    try:
        user_id = validate_and_bind(email=email, code=code, chat_id=chat_id)
        logger.info(
            "telegram_bind.success chat_id=%s user_id=%s email=%s",
            chat_id,
            user_id,
            email,
        )
        # Sprint 78: улучшенное welcome message (Kimi P1-4) + Sprint 3.23.
        send_message(
            chat_id,
            f"✅ Привязка успешна! <b>{email}</b> теперь связан с твоим Telegram.\n\n"
            "📚 <b>Что я умею:</b>\n"
            "• /homework — список невыполненных тем\n"
            "• /stats — статистика за неделю\n"
            "• /hint <id> — подсказка по задаче\n"
            "• /pause — поставить AI на паузу (T1D safety)\n"
            "• /help — список всех команд\n\n"
            "💡 <i>Совет:</i> подписывайся на уведомления, чтобы видеть прогресс ребёнка.\n\n"
            "Если есть вопросы — пиши /help или обратись к админу.",
        )
    except ValueError as e:
        msg = str(e).lower()
        if "expired" in msg:
            txt = "⏰ Код истёк (15 мин). Попроси новый у админа."
        elif "invalid" in msg or "already-used" in msg:
            txt = "❌ Код не найден или уже использован. Запроси новый."
        elif "unknown" in msg or "inactive" in msg:
            txt = f"❌ Email <b>{email}</b> не зарегистрирован или не активирован."
        else:
            txt = f"❌ Ошибка привязки: {e}"
        logger.info("telegram_bind.failed chat_id=%s email=%s err=%s", chat_id, email, e)
        send_message(chat_id, txt)
    except Exception as e:
        logger.exception("cmd_start unexpected error")
        send_message(chat_id, f"❌ Внутренняя ошибка бота: {e}")


def cmd_help(chat_id: int, args: list[str]) -> None:
    send_message(
        chat_id,
        "🤖 <b>AI-репетитор — команды</b>\n\n"
        "/start email code — привязать Telegram\n"
        "/homework — список невыполненных тем\n"
        "/stats — статистика за неделю\n"
        "/hint <topic_id> — подсказка по теме\n"
        "/pause — поставить AI на паузу\n"
        "/resume — возобновить AI\n"
        "/help — эта справка",
    )


# === Main loop (long-poll) ===


def handle_update(update: dict) -> None:
    """Sprint 6.1: обработка одного update от Telegram."""
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return

    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    if not text:
        return

    # Rate limit
    if not check_rate_limit(chat_id):
        send_message(chat_id, "⏳ Слишком часто. Подожди 3 секунды.")
        return

    parts = text.split(maxsplit=2)
    cmd = parts[0].lower() if parts else ""
    args = parts[1:] if len(parts) > 1 else []

    update_last_command(chat_id)

    if cmd == "/start":
        cmd_start(chat_id, args)
    elif cmd == "/help":
        cmd_help(chat_id, args)
    else:
        # Проверяем binding
        binding = get_binding(chat_id)
        if not binding:
            send_message(chat_id, "🔒 Сначала привяжи Telegram: /start email code")
            return
        # TODO Sprint 16.x: /homework, /stats, /hint, /pause — реализовать
        # через прямые DB запросы или internal API.
        send_message(chat_id, f"Команда {cmd} пока не реализована. /help для списка.")


def main() -> int:
    if not TELEGRAM_BOT_ENABLED:
        logger.info("telegram_bot: disabled via TELEGRAM_BOT_ENABLED=0")
        return 0
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен")
        return 1

    init_db()
    logger.info("telegram_bot: started, polling...")

    offset = 0
    while True:
        try:
            r = httpx.get(
                f"{API_BASE}/getUpdates",
                params={"offset": offset, "timeout": 30, "allowed_updates": ["message"]},
                timeout=35.0,
            )
            data = r.json()
            for update in data.get("result", []):
                offset = max(offset, update["update_id"] + 1)
                handle_update(update)
        except httpx.TimeoutException:
            continue  # Normal для long-poll
        except Exception as e:
            logger.exception("getUpdates failed: %s", e)
            time.sleep(5)


if __name__ == "__main__":
    sys.exit(main())
