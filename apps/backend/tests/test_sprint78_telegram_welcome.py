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


def test_cmd_start_with_valid_code_sends_enhanced_welcome():
    """Sprint 78: /start с valid code → enhanced welcome (Kimi P1-4)."""
    from app.bot import telegram_bot

    # Mock HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"user_id": 42}

    with patch.object(telegram_bot, "send_message") as mock_send, \
         patch.object(telegram_bot, "set_binding"), \
         patch("app.bot.telegram_bot.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        telegram_bot.cmd_start(chat_id=12345, args=["test@example.com", "123456"])

    # Should send enhanced welcome
    assert mock_send.called
    last_call = mock_send.call_args_list[-1]
    message = last_call[0][1]
    # Sprint 78: enhanced welcome includes tips + совет
    assert "Что я умею" in message, "Welcome должен содержать feature overview"
    assert "Совет" in message, "Welcome должен содержать tip для родителей"
    assert "T1D" in message or "AI на паузу" in message, "Welcome должен упоминать T1D"


def test_cmd_start_invalid_code_returns_error():
    """Sprint 78: /start с invalid code → error message."""
    from app.bot import telegram_bot

    # Mock HTTP error response
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {"detail": "Invalid code"}

    with patch.object(telegram_bot, "send_message") as mock_send, \
         patch("app.bot.telegram_bot.httpx.post") as mock_post:
        mock_post.return_value = mock_response

        telegram_bot.cmd_start(chat_id=12345, args=["test@example.com", "wrong"])

    # Should send error
    mock_send.assert_called_once()
    message = mock_send.call_args[0][1]
    assert "❌" in message
    assert "Invalid code" in message