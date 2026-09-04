"""Sprint 3.23 — Telegram self-service bind flow.

До Sprint 3.23:
- /start <email> <code> handler в app/bot/telegram_bot.py делал POST на
  /api/v1/auth/telegram-bind, но endpoint **отсутствовал** в auth/router.py →
  404 → binding не записывался.
- Единственный способ привязать chat_id — ручной INSERT через psql.

После Sprint 3.23:
- issue_code(email) генерирует 8-hex-char code для user'а с этим email.
- validate_and_bind(email, code, chat_id) атомарно проверяет код и пишет binding.
- cmd_start использует эти функции через ту же БД (Postgres backend).
- /api/v1/admin/telegram-code — admin-only endpoint для генерации кодов.

Безопасность:
- code expires через 15 минут.
- коды одноразовые (validate_and_bind → delete code).
- /api/v1/admin/telegram-code — только admin, rate-limit 20/час на admin_id.
- audit log: action='telegram.code.issue' / 'telegram.bind.success' / 'telegram.bind.failed'.
"""
from __future__ import annotations

import secrets
import time
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

# Импортируем ВСЕ модели до того как их используем в Base.metadata.
# Без этого при первом запуске сессии SQLite in-memory в Base.metadata
# пустой — issue_code() упадёт на SELECT users.
from app.users import models as _users_models  # noqa: F401
from app.subjects import models as _subjects_models  # noqa: F401
from app.progress import models as _progress_models  # noqa: F401
from app.diagnostics import models as _diagnostics_models  # noqa: F401
from app.admin import models as _admin_models  # noqa: F401
from app.admin import ai_providers as _ai_providers_models  # noqa: F401  # Sprint 3.9.6
from app.notifications import models as _notifications_models  # noqa: F401
from app.auth import password_reset_models as _password_reset_models  # noqa: F401
from app import rag_models as _rag_models  # noqa: F401  # Sprint 3.5.2
from app.sessions import models as _sessions_models  # noqa: F401  # Sprint 34
from app.cgm import models as _cgm_models  # noqa: F401  # Sprint 40
from app.invites import models as _invites_models  # noqa: F401  # Sprint 44

from app.bot.telegram_bot import (
    issue_code,
    validate_and_bind,
    init_db,
)


def _setup_db():
    """Переустановить state telegram_* таблиц + ВСЕ остальные для каждого теста.

    Sprint 3.23: drop_all+create_all — безопасно, т.к. SQLAlchemy-схема создаётся
    заново для каждого теста с нуля (users, telegram_*, и т.д.).
    """
    from app.db.session import Base, engine
    from sqlalchemy import text

    engine.dispose()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    # init_db() создаёт таблицы telegram_* через engine (уже созданные CREATE TABLE
    # IF NOT EXISTS — no-op).
    init_db()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM telegram_bind_codes"))
        conn.execute(text("DELETE FROM telegram_bindings"))


@pytest.fixture
def db_setup():
    _setup_db()


class TestTelegramBindCodes:
    def _make_user(self, *, email: str, role: str = "student"):
        """Sprint 3.23 helper: создать user'а в shared DB для теста."""
        from app.db.session import SessionLocal
        from app.users import service as user_service
        from app.users.schemas import UserCreate
        from app.users.models import User

        db = SessionLocal()
        try:
            user_service.register_user(
                db,
                UserCreate(
                    email=email,
                    password="strongpass1",
                    display_name=email.split("@")[0],
                    role=role,
                    grade=7 if role == "student" else None,
                ),
            )
            db.commit()
        finally:
            db.close()
        db = SessionLocal()
        try:
            u = db.query(User).filter_by(email=email).first()
            u.is_active = True
            db.commit()
        finally:
            db.close()

    def test_issue_code_returns_8_chars(self, db_setup):
        """issue_code возвращает 8 hex chars (32 bits)."""
        self._make_user(email="alice@example.com")
        code = issue_code(email="alice@example.com")
        assert isinstance(code, str)
        assert len(code) == 8
        int(code, 16)  # raises если не hex

    def test_issue_code_deduplicates_active_codes(self, db_setup):
        """Повторная выдача для того же email не плодит несколько активных кодов."""
        self._make_user(email="alice2@example.com")
        issue_code(email="alice2@example.com")
        issue_code(email="alice2@example.com")
        from app.db.session import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id FROM telegram_bind_codes WHERE email = :e AND used_at IS NULL"
                ),
                {"e": "alice2@example.com"},
            ).fetchall()
        assert len(rows) == 1, f"ожидаем 1 активный код, найдено {len(rows)}"

    def test_validate_and_bind_returns_user_id_on_success(self, db_setup):
        """Happy-path: issue_code → validate_and_bind возвращает user_id."""
        self._make_user(email="bob@example.com")
        code = issue_code(email="bob@example.com")
        user_id = validate_and_bind(email="bob@example.com", code=code, chat_id=123456789)
        assert user_id is not None
        assert isinstance(user_id, int)

    def test_validate_and_bind_consumes_code(self, db_setup):
        """После успешного bind код становится нерабочим (одноразовый)."""
        self._make_user(email="chris@example.com")
        code = issue_code(email="chris@example.com")
        validate_and_bind(email="chris@example.com", code=code, chat_id=111222333)
        with pytest.raises(ValueError, match="invalid.*code|already-used"):
            validate_and_bind(email="chris@example.com", code=code, chat_id=444555666)

    def test_validate_and_bind_rejects_wrong_code(self, db_setup):
        """Случайный код → ValueError."""
        self._make_user(email="dave@example.com")
        issue_code(email="dave@example.com")  # чтобы коды вообще были
        with pytest.raises(ValueError, match="invalid.*code"):
            validate_and_bind(
                email="dave@example.com", code="DEADBEEF", chat_id=999888777
            )

    def test_validate_and_bind_rejects_expired_code(self, db_setup):
        """Просроченный код (>15 мин) → ValueError."""
        self._make_user(email="eve@example.com")
        code = issue_code(email="eve@example.com")
        # Вручную сдвигаем expires_at на 20 мин назад
        from sqlalchemy import text
        from app.db.session import engine
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE telegram_bind_codes SET expires_at = :exp WHERE code = :c"),
                {"exp": (datetime.now(UTC) - timedelta(minutes=20)).isoformat(), "c": code},
            )
        with pytest.raises(ValueError, match="expired"):
            validate_and_bind(
                email="eve@example.com", code=code, chat_id=111111111
            )

    def test_issue_code_unknown_email_raises(self, db_setup):
        """issue_code для несуществующего email → ValueError."""
        with pytest.raises(ValueError, match="no active user"):
            issue_code(email="nonexistent@example.com")


# Sprint 3.23: Admin endpoint test требует полной auth-инфраструктуры (issue_token,
# require_admin, audit log) — это Sprint 3.23b scope (separately tested через
# /api/v1/admin/telegram-code endpoint). Сейчас поверим что сам issue_code +
# validate_and_bind работают в unit-test (7 passed). Endpoint покрыт
# ручным /start бот-тестом на проде (Sprint 3.23 smoke).
