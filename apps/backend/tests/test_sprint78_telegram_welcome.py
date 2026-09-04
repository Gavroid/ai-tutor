"""Sprint 78: Telegram bot welcome message tests."""
from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from unittest.mock import MagicMock, patch

import pytest

# === Module-level tests ===

def test_welcome_message_includes_help():
    """Sprint 78: welcome message содержит help commands."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "bot", "telegram_bot.py",
        )
    ) as f:
        content = f.read()
    assert "/homework" in content
    assert "/stats" in content
    assert "/hint" in content
    assert "/pause" in content
    assert "/help" in content


def test_welcome_message_includes_tips():
    """Sprint 78: welcome message содержит tips для родителей."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "bot", "telegram_bot.py",
        )
    ) as f:
        content = f.read()
    assert "Совет" in content or "💡" in content
    assert "T1D" in content or "AI на паузу" in content


def test_sprint_78_welcome_marker_in_code():
    """Sprint 78: код имеет маркер Sprint 78."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "bot", "telegram_bot.py",
        )
    ) as f:
        content = f.read()
    assert "Sprint 78" in content
    assert "Kimi P1-4" in content


# === Mock tests ===

def test_cmd_start_no_args_returns_welcome():
    """Sprint 78: /start без args → приветственное сообщение."""
    from app.bot import telegram_bot

    with patch.object(telegram_bot, "send_message") as mock_send:
        telegram_bot.cmd_start(chat_id=12345, args=[])

    # Should send welcome/help message
    mock_send.assert_called_once()
    args = mock_send.call_args
    assert args[0][0] == 12345  # chat_id
    message = args[0][1]
    assert "Привет" in message
    assert "/start" in message  # tells how to bind


class TestCmdStartSprint78And323:
    """Sprint 78 + 3.23: cmd_start с mocked validate_and_bind."""

    @pytest.fixture
    def db_setup(self):
        """Sprint 3.23: local DB setup для этого test_file (не импортируется из test_telegram_bind)."""
        from app.db.session import Base, SessionLocal, engine
        from app.users import models as _u  # noqa: F401
        from app.subjects import models as _s  # noqa: F401
        from app.progress import models as _p  # noqa: F401
        from app.diagnostics import models as _d  # noqa: F401
        from app.admin import models as _a  # noqa: F401
        from app.notifications import models as _n  # noqa: F401
        from app.auth import password_reset_models as _pr  # noqa: F401
        from app import rag_models as _r  # noqa: F401
        from app.sessions import models as _ss  # noqa: F401
        from app.cgm import models as _c  # noqa: F401
        from app.invites import models as _i  # noqa: F401
        from app.bot.telegram_bot import init_db
        from sqlalchemy import text

        engine.dispose()
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        init_db()
        with engine.begin() as conn:
            try:
                conn.execute(text("DELETE FROM telegram_bind_codes"))
                conn.execute(text("DELETE FROM telegram_bindings"))
            except Exception:
                pass

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

    def test_cmd_start_with_valid_code_sends_enhanced_welcome(self, db_setup):
        """Sprint 78 + 3.23: /start с valid code → enhanced welcome (Kimi P1-4).

        Sprint 3.23: вместо mocked httpx POST на /api/v1/auth/telegram-bind —
        напрямую patch'а validate_and_bind() чтобы вернуть user_id (новый flow).
        """
        from app.bot import telegram_bot

        self._make_user(email="test@example.com", role="student")

        # Patch validate_and_bind вместо httpx.post (новый flow Sprint 3.23).
        with patch.object(telegram_bot, "send_message") as mock_send, \
             patch.object(telegram_bot, "validate_and_bind", return_value=42):
            telegram_bot.cmd_start(
                chat_id=12345, args=["test@example.com", "abcd1234"]
            )

        # Should send enhanced welcome
        assert mock_send.called
        last_call = mock_send.call_args_list[-1]
        message = last_call[0][1]
        # Sprint 78: enhanced welcome includes tips + совет
        assert "Что я умею" in message, "Welcome должен содержать feature overview"
        assert "Совет" in message, "Welcome должен содержать tip для родителей"
        assert "T1D" in message or "AI на паузу" in message, (
            "Welcome должен упоминать T1D"
        )

    def test_cmd_start_invalid_code_returns_error(self, db_setup):
        """Sprint 78 + 3.23: /start с invalid code → error message через ValueError."""
        from app.bot import telegram_bot

        self._make_user(email="test@example.com", role="student")

        # Patch validate_and_bind чтобы бросил ValueError (новый flow).
        with patch.object(telegram_bot, "send_message") as mock_send, \
             patch.object(
                 telegram_bot, "validate_and_bind",
                 side_effect=ValueError("invalid or already-used code"),
             ):
            telegram_bot.cmd_start(chat_id=12345, args=["test@example.com", "wrong"])

        # Should send error
        mock_send.assert_called_once()
        message = mock_send.call_args[0][1]
        assert "❌" in message
        assert "Код не найден" in message or "Invalid code" in message
