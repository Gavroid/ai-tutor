"""Sprint 50: Alert worker v2 (drain queue + persistent log + exponential backoff)."""

from __future__ import annotations

import json
import os
import signal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import redis


@pytest.fixture(autouse=True)
def _patch_alert_log_file(tmp_path, monkeypatch):
    """Sprint 50: каждый тест использует свой tmp log файл."""
    log_file = tmp_path / "alerts.jsonl"
    monkeypatch.setenv("ALERT_LOG_FILE", str(log_file))
    # Перезагружаем модуль чтобы подхватить env
    import importlib

    from app.bot import alert_worker

    importlib.reload(alert_worker)
    return log_file


@pytest.fixture
def tmp_log_file(tmp_path):
    """Sprint 50: temp file для JSONL log."""
    return tmp_path / "alerts.jsonl"


def test_drain_queue_uses_lpop_not_blpop():
    """Sprint 50: drain_queue использует LPOP (sync), не BLPOP."""
    from app.bot.alert_worker import _drain_queue

    mock_r = MagicMock()
    mock_r.lpop.side_effect = [json.dumps({"kind": "http_5xx", "status": 500, "method": "GET", "path": "/x"}), None]

    with patch("app.bot.alert_worker.process_one", return_value=True) as mock_proc:
        count = _drain_queue(mock_r, max_items=10)
    assert count == 1
    # Проверяем что lpop был вызван (не blpop)
    assert mock_r.lpop.called
    assert not mock_r.blpop.called


def test_drain_queue_respects_max_items():
    """Sprint 50: drain останавливается после max_items."""
    from app.bot.alert_worker import _drain_queue

    mock_r = MagicMock()
    # Возвращает payloads бесконечно
    mock_r.lpop.side_effect = lambda *args, **kwargs: json.dumps({"kind": "x"}) if True else None

    with patch("app.bot.alert_worker.process_one", return_value=True):
        count = _drain_queue(mock_r, max_items=3)
    assert count == 3


def test_drain_queue_handles_connection_error():
    """Sprint 50: drain прерывается при connection error."""
    from app.bot import alert_worker
    from app.bot.alert_worker import _drain_queue

    mock_r = MagicMock()
    from redis.exceptions import ConnectionError

    mock_r.lpop.side_effect = ConnectionError("Redis down")

    count = _drain_queue(mock_r, max_items=10)
    assert count == 0


def test_log_to_file_creates_directory(tmp_log_file):
    """Sprint 50: _log_to_file создаёт директорию если нет."""
    from app.bot.alert_worker import _log_to_file

    # Записываем — _log_to_file должен создать parent dir + файл.
    _log_to_file({"test": "data"}, "sent", 123)

    assert tmp_log_file.exists()
    content = tmp_log_file.read_text()
    assert "test" in content
    assert "sent" in content
    assert "123" in content


def test_log_to_file_creates_nested_directory(tmp_path, monkeypatch):
    """Sprint 50: _log_to_file создаёт nested directories."""
    nested_log = tmp_path / "deeply" / "nested" / "dir" / "alerts.jsonl"
    monkeypatch.setenv("ALERT_LOG_FILE", str(nested_log))

    import importlib

    from app.bot import alert_worker

    importlib.reload(alert_worker)

    alert_worker._log_to_file({"x": 1}, "sent", 1)
    assert nested_log.exists()


def test_log_to_file_includes_timestamp_and_payload(tmp_log_file):
    """Sprint 50: JSONL содержит timestamp, status, telegram_message_id, payload."""
    from app.bot.alert_worker import _log_to_file

    payload = {"kind": "http_5xx", "method": "GET", "path": "/x"}
    _log_to_file(payload, "sent", 42)

    entry = json.loads(tmp_log_file.read_text().strip())
    assert entry["status"] == "sent"
    assert entry["telegram_message_id"] == 42
    assert entry["payload"] == payload
    assert "timestamp" in entry
    # ISO 8601 timestamp
    from datetime import datetime

    datetime.fromisoformat(entry["timestamp"])  # raises if invalid


def test_log_to_file_appends_multiple_lines(tmp_log_file):
    """Sprint 50: JSONL — одна строка на entry."""
    from app.bot.alert_worker import _log_to_file

    _log_to_file({"a": 1}, "sent", 1)
    _log_to_file({"b": 2}, "deduped", None)
    _log_to_file({"c": 3}, "error", None)

    lines = tmp_log_file.read_text().strip().split("\n")
    assert len(lines) == 3
    # Каждая строка — валидный JSON
    for line in lines:
        entry = json.loads(line)
        assert "timestamp" in entry
        assert "status" in entry


def test_signal_handler_sets_shutdown_reason():
    """Sprint 50: SIGTERM записывает reason."""
    from app.bot import alert_worker
    from app.bot.alert_worker import _signal_handler

    # Сбросим initial value
    alert_worker._shutdown_reason = "running"
    alert_worker._running = True

    # Вызовем SIGTERM handler
    _signal_handler(signal.SIGTERM, None)

    assert alert_worker._shutdown_reason == "SIGTERM"
    assert alert_worker._running is False


def test_signal_handler_handles_sigint():
    """Sprint 50: SIGINT также останавливает worker."""
    from app.bot import alert_worker
    from app.bot.alert_worker import _signal_handler

    alert_worker._shutdown_reason = "running"
    alert_worker._running = True

    _signal_handler(signal.SIGINT, None)

    assert alert_worker._shutdown_reason == "SIGINT"
    assert alert_worker._running is False


def test_format_alert_5xx():
    """Sprint 50: format_alert для http_5xx."""
    from app.bot.alert_worker import format_alert

    payload = {
        "kind": "http_5xx",
        "method": "GET",
        "path": "/api/v1/test",
        "status": 500,
        "request_id": "abc-123",
    }
    text = format_alert(payload)
    assert "5xx" in text
    assert "GET" in text
    assert "/api/v1/test" in text
    assert "500" in text


def test_format_alert_generic():
    """Sprint 50: format_alert generic fallback."""
    from app.bot.alert_worker import format_alert

    text = format_alert({"kind": "unknown_kind", "data": "x"})
    assert "alert" in text.lower()


def test_process_one_dedupes(tmp_log_file):
    """Sprint 50: process_one dedupes + логирует в файл."""
    from app.bot.alert_worker import process_one

    mock_r = MagicMock()
    # SET NX EX returns False → уже dedupe'нуто
    mock_r.set.return_value = False

    payload = json.dumps(
        {
            "kind": "http_5xx",
            "status": 500,
            "method": "GET",
            "path": "/test",
        }
    )
    result = process_one(mock_r, payload)
    assert result is False
    # Должна быть запись deduped в log
    assert tmp_log_file.exists()
    assert "deduped" in tmp_log_file.read_text()


def test_process_one_invalid_json(tmp_log_file):
    """Sprint 50: process_one handles invalid JSON gracefully."""
    from app.bot.alert_worker import process_one

    mock_r = MagicMock()
    result = process_one(mock_r, "INVALID JSON{")
    assert result is False
    assert "error" in tmp_log_file.read_text()


def test_send_telegram_missing_token(monkeypatch):
    """Sprint 50: send_telegram возвращает None если нет token."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_ALERT_CHAT_ID", "")

    # Reimport чтобы подхватить env
    import importlib

    from app.bot import alert_worker

    importlib.reload(alert_worker)

    result = alert_worker.send_telegram("test")
    assert result is None


def test_main_returns_error_if_no_token(monkeypatch):
    """Sprint 50: main() returns 1 если нет TELEGRAM_BOT_TOKEN."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_ALERT_CHAT_ID", "")

    import importlib

    from app.bot import alert_worker

    importlib.reload(alert_worker)

    result = alert_worker.main()
    assert result == 1


def test_module_constants_present():
    """Sprint 50: module-level config constants."""
    from app.bot import alert_worker

    assert hasattr(alert_worker, "ALERT_LOG_FILE")
    assert hasattr(alert_worker, "ALERT_DRAIN_MAX_ITEMS")
    assert hasattr(alert_worker, "_shutdown_reason")
    assert hasattr(alert_worker, "_running")
    assert isinstance(alert_worker._running, bool)
