"""Sprint 83: WebSocket keepalive + max lifetime tests."""
from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest


# === Source verification ===

def test_ws_constants_defined():
    """Sprint 83: WS_MAX_LIFETIME_SECONDS и WS_PING_INTERVAL_SECONDS."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "ai", "websocket.py",
        )
    ) as f:
        content = f.read()
    assert "WS_MAX_LIFETIME_SECONDS = 3600" in content, "Max lifetime должен быть 1 час"
    assert "WS_PING_INTERVAL_SECONDS = 30" in content, "Ping interval 30 sec"


def test_ws_keepalive_sends_ping():
    """Sprint 83: keepalive отправляет ping."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "ai", "websocket.py",
        )
    ) as f:
        content = f.read()
    assert "_send_pings" in content
    assert "send_json({\"type\": \"ping\"" in content or 'send_json({"type": "ping"' in content


def test_ws_max_lifetime_enforced():
    """Sprint 83: max lifetime вызывает close."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "ai", "websocket.py",
        )
    ) as f:
        content = f.read()
    assert "Max lifetime exceeded" in content
    assert "ws_max_lifetime" in content.lower() or "WS_MAX_LIFETIME" in content


def test_ws_ping_task_cancelled_on_exit():
    """Sprint 83: ping_task отменяется при cleanup."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "ai", "websocket.py",
        )
    ) as f:
        content = f.read()
    assert "ping_task.cancel" in content, "ping_task должен отменяться"


def test_ws_uses_wait_for_timeout():
    """Sprint 83: receive_text с asyncio.wait_for timeout."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "ai", "websocket.py",
        )
    ) as f:
        content = f.read()
    assert "asyncio.wait_for" in content
    assert "TimeoutError" in content


# === Integration tests ===

def test_ws_module_imports():
    """Sprint 83: websocket module imports successfully."""
    from app.ai import websocket as ws_module

    assert hasattr(ws_module, "ai_chat_stream")
    assert hasattr(ws_module, "WS_MAX_LIFETIME_SECONDS")
    assert hasattr(ws_module, "WS_PING_INTERVAL_SECONDS")
    assert ws_module.WS_MAX_LIFETIME_SECONDS == 3600
    assert ws_module.WS_PING_INTERVAL_SECONDS == 30