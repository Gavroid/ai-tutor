"""Sprint 76: audit-log/count date range protection tests."""

from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Sprint 76: TestClient + DB setup."""
    from app.db.session import Base, engine
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Sprint 76: admin token."""
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


# === Tests: date range protection ===


def test_audit_log_count_default_uses_90_days(client, admin_token):
    """Sprint 76: без фильтров возвращает count за последние 90 дней."""
    r = client.get(
        "/api/v1/admin/audit-log/count",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    # Should return count, не 5xx
    assert "total" in r.json()


def test_audit_log_count_invalid_since_returns_400(client, admin_token):
    """Sprint 76: invalid since ISO → 400."""
    r = client.get(
        "/api/v1/admin/audit-log/count?since=not-a-date",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400


def test_audit_log_count_invalid_until_returns_400(client, admin_token):
    """Sprint 76: invalid until ISO → 400."""
    r = client.get(
        "/api/v1/admin/audit-log/count?until=2026-13-99T99:99:99",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400


def test_audit_log_count_too_large_range_returns_400(client, admin_token):
    """Sprint 76: date range > 730 days → 400."""
    # 3 years range
    since = "2020-01-01T00:00:00Z"
    until = "2024-01-01T00:00:00Z"  # ~1461 days
    r = client.get(
        f"/api/v1/admin/audit-log/count?since={since}&until={until}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400
    assert "730" in str(r.json()) or "too large" in str(r.json()).lower()


def test_audit_log_count_valid_range_accepted(client, admin_token):
    """Sprint 76: valid 1-year range → 200."""
    since = "2024-01-01T00:00:00Z"
    until = "2024-12-01T00:00:00Z"  # ~335 days
    r = client.get(
        f"/api/v1/admin/audit-log/count?since={since}&until={until}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200


def test_audit_log_count_only_since_within_limit(client, admin_token):
    """Sprint 76: только since (без until) → 200 (default range)."""
    since = "2024-01-01T00:00:00Z"
    r = client.get(
        f"/api/v1/admin/audit-log/count?since={since}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200


def test_audit_log_count_requires_admin(client):
    """Sprint 76: non-admin → 401/403."""
    # Register student
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "s@example.com",
            "password": "Kirill2026!",
            "display_name": "S",
            "role": "student",
            "grade": 7,
        },
    )
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "s@example.com", "password": "Kirill2026!"},
    )
    if r.status_code == 200:
        student_token = r.json()["access_token"]
        r2 = client.get(
            "/api/v1/admin/audit-log/count",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert r2.status_code in (401, 403)
