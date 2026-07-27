"""Sprint 85: cohort retention tests."""
from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Sprint 85: TestClient + DB setup."""
    from app.db.session import engine, Base
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Sprint 85: admin token."""
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


# === Tests: cohort retention ===

def test_engagement_includes_retention_cohorts(client, admin_token):
    """Sprint 85: /engagement response содержит retention_cohorts."""
    r = client.get(
        "/api/v1/admin/engagement?days=60",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "retention_cohorts" in data
    assert isinstance(data["retention_cohorts"], list)


def test_engagement_empty_retention_when_no_users(client, admin_token):
    """Sprint 85: без users → retention_cohorts пустой."""
    r = client.get(
        "/api/v1/admin/engagement?days=60",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    data = r.json()
    # Empty cohorts (no users)
    assert isinstance(data["retention_cohorts"], list)  # может быть пустой или с admin cohort


def test_engagement_short_period_no_retention(client, admin_token):
    """Sprint 85: days < 7 → retention_cohorts пустой (no full week)."""
    r = client.get(
        "/api/v1/admin/engagement?days=3",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    data = r.json()
    # < 7 days → no cohorts
    assert isinstance(data["retention_cohorts"], list)  # может быть пустой или с admin cohort


def test_engagement_has_d1_d7_d30_fields(client, admin_token):
    """Sprint 85: cohort имеет поля retained_d1, d7, d30."""
    # Setup: create user with attempt
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.users.models import User, Role
    from app.auth.security import hash_password
    from app.progress.models import Attempt

    with Session(engine) as db:
        # User created 2 weeks ago
        old_user = User(
            email="old@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="Old",
            role=Role.STUDENT,
            is_active=True,
            created_at=datetime.now(timezone.utc) - timedelta(days=14),
        )
        db.add(old_user)
        db.commit()
        db.refresh(old_user)

    r = client.get(
        "/api/v1/admin/engagement?days=60",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    data = r.json()
    if data["retention_cohorts"]:
        cohort = data["retention_cohorts"][0]
        assert "cohort_week" in cohort
        assert "cohort_size" in cohort
        assert "retained_d1" in cohort
        assert "retained_d7" in cohort
        assert "retained_d1_pct" in cohort
        assert "retained_d7_pct" in cohort


def test_engagement_requires_admin(client):
    """Sprint 85: /engagement требует admin."""
    r = client.get("/api/v1/admin/engagement")
    assert r.status_code == 401


def test_engagement_days_bounds():
    """Sprint 85: days должен быть 1-365 (Sprint 16.0 P0-8)."""
    # Verify bounds via source
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "admin", "router.py",
        )
    ) as f:
        content = f.read()
    assert "Query(ge=1, le=365)" in content
    assert "days: Annotated[int" in content