"""Sprint 82: /ready endpoint Redis check tests."""
from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Sprint 82: TestClient + DB setup."""
    from app.db.session import engine, Base
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


# === Source verification ===

def test_ready_endpoint_checks_redis():
    """Sprint 82: /ready endpoint имеет Redis check."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "main.py",
        )
    ) as f:
        content = f.read()
    assert "Sprint 82: Redis check" in content
    assert "redis_unavailable" in content  # reason when Redis down
    assert "redis.ping()" in content  # actual ping call


def test_ready_endpoint_returns_db_reason():
    """Sprint 82: /ready reason when DB down."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "main.py",
        )
    ) as f:
        content = f.read()
    assert "db_unavailable" in content


# === Integration tests ===

def test_ready_returns_redis_unavailable_when_redis_down(client):
    """Sprint 82: Redis down → 503 + status=not_ready + reason=redis_unavailable.

    Sprint 3.15: HTTP-семантика readiness — 503 на not_ready (K8s-style).
    """
    # Mock DB connection to succeed
    with patch("app.main.engine") as mock_engine:
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.execute = MagicMock()
        mock_engine.connect.return_value = mock_conn

        # Mock _get_redis to return None (Redis unavailable)
        with patch("app.main._get_redis", return_value=None):
            r = client.get("/ready")
            assert r.status_code == 503, r.text
            data = r.json()
            assert data["status"] == "not_ready"
            assert data["reason"] == "redis_unavailable"


def test_ready_returns_ready_when_all_healthy(client):
    """Sprint 82: DB OK + Redis OK → status=ready + 200."""
    # Mock DB connection to succeed
    with patch("app.main.engine") as mock_engine:
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.execute = MagicMock()
        mock_engine.connect.return_value = mock_conn

        # Mock Redis ping to succeed
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock()
        mock_redis.aclose = AsyncMock()

        with patch("app.main._get_redis", return_value=mock_redis):
            r = client.get("/ready")
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "ready"


def test_ready_returns_redis_error_when_ping_fails(client):
    """Sprint 82: Redis ping raises → 503 + reason=redis_error.

    Sprint 3.15: HTTP-семантика readiness — 503 на not_ready (K8s-style).
    """
    with patch("app.main.engine") as mock_engine:
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_conn.execute = MagicMock()
        mock_engine.connect.return_value = mock_conn

        # Mock Redis ping to raise
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("Redis down"))
        mock_redis.aclose = AsyncMock()

        with patch("app.main._get_redis", return_value=mock_redis):
            r = client.get("/ready")
            assert r.status_code == 503, r.text
            data = r.json()
            assert data["status"] == "not_ready"
            assert data["reason"] == "redis_unavailable"  # also treated as unavailable