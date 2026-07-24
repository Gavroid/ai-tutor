"""Sprint 16.0 P0-4: тесты для alert_worker.

Тестируем:
- format_alert — форматирование payload
- process_one — dedupe логика
- Dedupe: тот же alert не отправляется дважды за ALERT_DEDUPE_TTL
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_ALERT_CHAT_ID", "12345")

import pytest

from app.bot import alert_worker


def test_format_alert_5xx():
    """Sprint 16.0: format_alert для http_5xx."""
    payload = {
        "kind": "http_5xx",
        "status": 503,
        "method": "POST",
        "path": "/api/v1/ai/explain",
        "request_id": "abc123",
    }
    text = alert_worker.format_alert(payload)
    assert "🚨" in text
    assert "503" in text
    assert "/api/v1/ai/explain" in text
    assert "POST" in text
    assert "abc123" in text


def test_format_alert_generic():
    """Sprint 16.0: format_alert для unknown kind."""
    payload = {"kind": "custom", "data": "test"}
    text = alert_worker.format_alert(payload)
    assert "⚠" in text
    assert "custom" in text or "test" in text


def test_process_one_sends_to_telegram():
    """Sprint 16.0: process_one отправляет алерт в Telegram."""
    mock_redis = MagicMock()
    # set с nx=True → возвращает True (ключ создан)
    mock_redis.set.return_value = True

    payload_str = '{"kind": "http_5xx", "status": 500, "method": "GET", "path": "/health", "request_id": "r1"}'

    with patch.object(alert_worker, "send_telegram", return_value=True) as mock_send:
        result = alert_worker.process_one(mock_redis, payload_str)

    assert result is True
    mock_send.assert_called_once()
    call_args = mock_send.call_args[0][0]
    assert "🚨" in call_args
    assert "500" in call_args


def test_process_one_dedupes_same_alert():
    """Sprint 16.0: повторный alert в течение TTL не отправляется."""
    mock_redis = MagicMock()
    # Первый раз set с nx=True → True (новый ключ)
    # Второй раз set с nx=True → False (ключ уже есть)
    mock_redis.set.side_effect = [True, False]

    payload_str = '{"kind": "http_5xx", "status": 500, "method": "GET", "path": "/health", "request_id": "r1"}'

    with patch.object(alert_worker, "send_telegram", return_value=True):
        # Первый алерт — отправляется
        result1 = alert_worker.process_one(mock_redis, payload_str)
        # Второй алерт с тем же status+method+path — НЕ отправляется
        result2 = alert_worker.process_one(mock_redis, payload_str)

    assert result1 is True
    assert result2 is False


def test_process_one_different_path_not_deduped():
    """Sprint 16.0: разные path → разные dedupe ключи."""
    mock_redis = MagicMock()
    mock_redis.set.return_value = True  # оба раза новый ключ

    p1 = '{"kind": "http_5xx", "status": 500, "method": "GET", "path": "/api/v1/a", "request_id": "r1"}'
    p2 = '{"kind": "http_5xx", "status": 500, "method": "GET", "path": "/api/v1/b", "request_id": "r2"}'

    with patch.object(alert_worker, "send_telegram", return_value=True) as mock_send:
        r1 = alert_worker.process_one(mock_redis, p1)
        r2 = alert_worker.process_one(mock_redis, p2)

    assert r1 is True
    assert r2 is True
    assert mock_send.call_count == 2


def test_process_one_invalid_json():
    """Sprint 16.0: invalid JSON → False (пропускаем, не падаем)."""
    mock_redis = MagicMock()
    result = alert_worker.process_one(mock_redis, "{not valid json")
    assert result is False
