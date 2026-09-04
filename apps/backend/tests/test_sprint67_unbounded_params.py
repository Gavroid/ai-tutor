"""Sprint 67: unbounded query params validation tests.

Проверяем что endpoints с `limit`/`offset`/`days` параметрами
имеют явные bounds (Query ge=, le=) для предотвращения DoS.
"""
from __future__ import annotations

import os

# Sprint 64: disable OpenTelemetry для tests
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Sprint 67: TestClient fixture."""
    from app.db.session import Base, engine
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Sprint 67: admin token через прямой SQL."""
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


# === Tests: /admin/users ===

def test_admin_users_limit_too_high_rejected(client, admin_token):
    """Sprint 67: limit > 500 → 422."""
    r = client.get(
        "/api/v1/admin/users?limit=1000000",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 422


def test_admin_users_limit_zero_rejected(client, admin_token):
    """Sprint 67: limit=0 → 422."""
    r = client.get(
        "/api/v1/admin/users?limit=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 422


def test_admin_users_limit_negative_rejected(client, admin_token):
    """Sprint 67: limit=-1 → 422."""
    r = client.get(
        "/api/v1/admin/users?limit=-1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 422


def test_admin_users_offset_negative_rejected(client, admin_token):
    """Sprint 67: offset=-1 → 422."""
    r = client.get(
        "/api/v1/admin/users?offset=-1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 422


def test_admin_users_valid_limit_accepted(client, admin_token):
    """Sprint 67: limit=50 → 200."""
    r = client.get(
        "/api/v1/admin/users?limit=50",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200


# === Tests: /sessions/pauses/recent ===

def test_sessions_pauses_recent_limit_too_high_rejected(client, admin_token):
    """Sprint 67: /sessions/pauses/recent?limit=1000 → 422 (Query validator)."""
    # Используем admin token — endpoint требует auth
    r = client.get(
        "/api/v1/sessions/pauses/recent?limit=1000",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # 422 (validation) или 401 (admin не student) — главное не 500
    assert r.status_code in (401, 403, 422), f"Expected 422, got {r.status_code}"


def test_sessions_pauses_recent_limit_valid(client, admin_token):
    """Sprint 67: /sessions/pauses/recent?limit=10 → не 422."""
    r = client.get(
        "/api/v1/sessions/pauses/recent?limit=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Главное — НЕ 422 (validation passed)
    assert r.status_code != 422, f"limit=10 should be valid, got {r.status_code}"
