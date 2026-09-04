"""Sprint 86: AI budget hot-reload tests."""

from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Sprint 86: TestClient + DB setup."""
    from app.db.session import Base, engine
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Sprint 86: admin token."""
    from app.auth.security import hash_password
    from app.db.session import engine
    from app.users.models import Role, User
    from sqlalchemy.orm import Session

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


# === Module tests ===


def test_reload_limits_function_exists():
    """Sprint 86: reload_limits() функция существует."""
    from app.ai import budget as budget_module

    assert hasattr(budget_module, "reload_limits")
    assert callable(budget_module.reload_limits)


def test_reload_limits_updates_values():
    """Sprint 86: reload_limits() обновляет module-level constants."""
    from app.ai import budget as budget_module

    original_daily = budget_module.DAILY_REQUESTS_LIMIT
    try:
        budget_module.reload_limits(daily_requests=500)
        assert budget_module.DAILY_REQUESTS_LIMIT == 500
    finally:
        # Restore
        budget_module.DAILY_REQUESTS_LIMIT = original_daily


def test_reload_limits_validates_values():
    """Sprint 86: invalid values → ValueError."""
    from app.ai import budget as budget_module

    with pytest.raises(ValueError):
        budget_module.reload_limits(daily_requests=0)
    with pytest.raises(ValueError):
        budget_module.reload_limits(daily_tokens=10)
    with pytest.raises(ValueError):
        budget_module.reload_limits(alert_threshold=150)


def test_reload_limits_partial_update():
    """Sprint 86: partial update — None params оставляют значение как есть."""
    from app.ai import budget as budget_module

    original_daily = budget_module.DAILY_REQUESTS_LIMIT
    original_tokens = budget_module.DAILY_TOKENS_LIMIT
    try:
        budget_module.reload_limits(daily_requests=300)
        assert budget_module.DAILY_REQUESTS_LIMIT == 300
        assert budget_module.DAILY_TOKENS_LIMIT == original_tokens
    finally:
        budget_module.DAILY_REQUESTS_LIMIT = original_daily


# === Endpoint tests ===


def test_reload_endpoint_registered(client):
    """Sprint 86: /admin/config/reload-ai-budget endpoint registered."""
    from app.main import app

    paths = [getattr(route, "path", str(route)) for route in app.routes]
    assert any("/config/reload-ai-budget" in p for p in paths)


def test_reload_endpoint_requires_admin(client):
    """Sprint 86: endpoint требует admin."""
    r = client.post("/api/v1/admin/config/reload-ai-budget?daily_requests=500")
    assert r.status_code == 401


def test_reload_endpoint_updates_limits(client, admin_token):
    """Sprint 86: POST endpoint обновляет limits."""
    from app.ai import budget as budget_module

    original = budget_module.DAILY_REQUESTS_LIMIT
    try:
        r = client.post(
            "/api/v1/admin/config/reload-ai-budget?daily_requests=600",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["daily_requests"] == 600
        assert budget_module.DAILY_REQUESTS_LIMIT == 600
    finally:
        budget_module.DAILY_REQUESTS_LIMIT = original


def test_reload_endpoint_validates(client, admin_token):
    """Sprint 86: endpoint returns 400 для invalid values."""
    r = client.post(
        "/api/v1/admin/config/reload-ai-budget?daily_requests=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400
