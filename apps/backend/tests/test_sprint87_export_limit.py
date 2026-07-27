"""Sprint 87: audit log export max_records limit tests."""
from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Sprint 87: TestClient + DB setup."""
    from app.db.session import engine, Base
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Sprint 87: admin token."""
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


# === Tests ===

def test_export_default_max_records(client, admin_token):
    """Sprint 87: default max_records = 10000."""
    r = client.get(
        "/api/v1/admin/audit-log/export",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200


def test_export_max_records_validation(client, admin_token):
    """Sprint 87: max_records > 100000 → 422."""
    r = client.get(
        "/api/v1/admin/audit-log/export?max_records=200000",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 422


def test_export_max_records_min_validation(client, admin_token):
    """Sprint 87: max_records < 1 → 422."""
    r = client.get(
        "/api/v1/admin/audit-log/export?max_records=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 422


def test_export_max_records_custom(client, admin_token):
    """Sprint 87: max_records=5000 — valid."""
    r = client.get(
        "/api/v1/admin/audit-log/export?max_records=5000",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200


def test_export_max_records_max(client, admin_token):
    """Sprint 87: max_records=100000 — valid (max limit)."""
    r = client.get(
        "/api/v1/admin/audit-log/export?max_records=100000",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200


def test_export_requires_admin(client):
    """Sprint 87: export требует admin."""
    r = client.get("/api/v1/admin/audit-log/export")
    assert r.status_code == 401


# === Source verification ===

def test_max_records_query_param_defined():
    """Sprint 87: max_records Query param с bounds."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "admin", "router.py",
        )
    ) as f:
        content = f.read()
    assert "max_records: int = Query(10000, ge=1, le=100000)" in content
    assert "Sprint 87" in content
    assert ".limit(max_records)" in content