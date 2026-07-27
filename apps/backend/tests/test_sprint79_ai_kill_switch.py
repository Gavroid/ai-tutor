"""Sprint 79: AI kill switch tests."""
from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Sprint 79: TestClient + DB setup."""
    from app.db.session import engine, Base
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Sprint 79: admin token."""
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.users.models import User, Role
    from app.auth.security import hash_password

    with Session(engine) as db:
        admin = User(
            email="admin@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="Admin",
            role=Role.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Kirill2026!"},
    )
    return r.json()["access_token"]


# === AI kill switch tests ===

def test_ai_kill_switch_endpoint_registered(client):
    """Sprint 79: /admin/ai-kill-switch endpoint registered."""
    from app.main import app

    paths = [getattr(route, "path", str(route)) for route in app.routes]
    assert any("/ai-kill-switch" in p for p in paths), "AI kill switch endpoint not found"


def test_ai_kill_switch_empty(client, admin_token):
    """Sprint 79: empty kill switch returns empty list."""
    # Mock Redis
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value="")
    mock_redis.aclose = AsyncMock()

    with patch("app.admin.router._get_redis_for_admin", new=AsyncMock(return_value=mock_redis)):
        r = client.get(
            "/api/v1/admin/ai-kill-switch",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert r.status_code == 200
    data = r.json()
    assert "user_ids" in data


def test_ai_kill_switch_requires_admin(client):
    """Sprint 79: kill switch доступен только admin."""
    r = client.get("/api/v1/admin/ai-kill-switch")
    assert r.status_code == 401


def test_ai_kill_switch_add_user(client, admin_token):
    """Sprint 79: POST /ai-kill-switch/{user_id} добавляет user."""
    # Mock Redis
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value="")
    mock_redis.set = AsyncMock()
    mock_redis.aclose = AsyncMock()

    with patch("app.admin.router._get_redis_for_admin", new=AsyncMock(return_value=mock_redis)):
        r = client.post(
            "/api/v1/admin/ai-kill-switch/42",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True


def test_ai_kill_switch_persistent_via_redis():
    """Sprint 79: kill switch stored в Redis (multi-worker safe)."""
    # Verify _write_kill_switch uses Redis SET (not local var)
    from app.admin import router as admin_router

    # Read source code (mock approach for documentation)
    import inspect
    source = inspect.getsource(admin_router._write_kill_switch)
    assert "redis.set" in source, "kill switch должен использовать Redis SET"
    assert "ai:kill_switch" in source, "kill switch должен использовать key 'ai:kill_switch'"