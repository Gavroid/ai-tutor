"""Sprint 45: Audit log 2.0 tests (hash chain integrity + export)."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.db.session import Base, engine
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def admin_login(client):
    """Sprint 45: admin via direct SQL."""
    from app.auth.security import hash_password
    from app.db.session import engine
    from app.users.models import Role, User
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        user = User(
            email="admin@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="Admin",
            role=Role.ADMIN,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Kirill2026!"},
    )
    return r.json()["access_token"]


def test_record_creates_hash_chain(client, admin_login):
    """Sprint 45: record() создаёт record_hash + previous_hash."""
    from app.admin.service import record
    from app.auth.security import hash_password
    from app.db.session import SessionLocal
    from app.users.models import Role, User

    with SessionLocal() as db:
        admin = db.query(User).filter_by(email="admin@example.com").first()
        e1 = record(db, user=admin, action="test.action1", entity="x", entity_id="1")
        e2 = record(db, user=admin, action="test.action2", entity="x", entity_id="2")
        e3 = record(db, user=admin, action="test.action3", entity="x", entity_id="3")

        # Sprint 45: hashes
        assert e1.record_hash is not None
        assert e2.previous_hash == e1.record_hash
        assert e3.previous_hash == e2.record_hash


def test_verify_chain_returns_valid(client, admin_login):
    """Sprint 45: GET /audit-log/verify → all verified."""
    from app.admin.service import record
    from app.db.session import SessionLocal
    from app.users.models import User

    with SessionLocal() as db:
        admin = db.query(User).filter_by(email="admin@example.com").first()
        for i in range(5):
            record(db, user=admin, action=f"test.action{i}", entity="x", entity_id=str(i))

    r = client.get(
        "/api/v1/admin/audit-log/verify",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["verified"] == 5
    assert data["tampered"] == 0
    assert data["chain_broken_at"] is None
    assert data["first_tampered_id"] is None


def test_verify_chain_detects_tamper(client, admin_login):
    """Sprint 45: изменение записи → tampered."""
    from app.admin.models import AuditLog
    from app.admin.service import record
    from app.db.session import SessionLocal, engine
    from app.users.models import User
    from sqlalchemy import text

    with SessionLocal() as db:
        admin = db.query(User).filter_by(email="admin@example.com").first()
        record(db, user=admin, action="orig.action", entity="x", entity_id="1")
        record(db, user=admin, action="next.action", entity="x", entity_id="2")

    # Tamper: изменим action первой записи напрямую через SQL.
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE audit_logs SET action = 'tampered.action' WHERE entity_id = '1'")
        )

    r = client.get(
        "/api/v1/admin/audit-log/verify",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    data = r.json()
    # Sprint 45: tamper detected.
    assert data["tampered"] >= 1
    assert data["first_tampered_id"] is not None


def test_export_audit_log_json(client, admin_login):
    """Sprint 45: GET /audit-log/export?fmt=json → list of records."""
    from app.admin.service import record
    from app.db.session import SessionLocal
    from app.users.models import User

    with SessionLocal() as db:
        admin = db.query(User).filter_by(email="admin@example.com").first()
        record(db, user=admin, action="export.test", entity="x", entity_id="1")

    r = client.get(
        "/api/v1/admin/audit-log/export?fmt=json",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Sprint 45: новые поля
    assert "record_hash" in data[0]
    assert "previous_hash" in data[0]


def test_export_audit_log_csv(client, admin_login):
    """Sprint 45: GET /audit-log/export?fmt=csv → csv string."""
    from app.admin.service import record
    from app.db.session import SessionLocal
    from app.users.models import User

    with SessionLocal() as db:
        admin = db.query(User).filter_by(email="admin@example.com").first()
        record(db, user=admin, action="export.csv.test", entity="x", entity_id="1")

    r = client.get(
        "/api/v1/admin/audit-log/export?fmt=csv",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data
    assert "audit_log_csv.csv" in data["filename"]
    assert "content" in data
    # Проверяем header
    assert "record_hash" in data["content"]
    assert "previous_hash" in data["content"]


def test_export_audit_log_logs_export_action(client, admin_login):
    """Sprint 45: export сам себя логирует (audit.export)."""
    r = client.get(
        "/api/v1/admin/audit-log/export?fmt=json",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200

    # Проверяем что в audit log появилась запись audit.export
    r2 = client.get(
        "/api/v1/admin/audit-log?action=audit.export&limit=5",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r2.status_code == 200
    data = r2.json()
    assert any(log.get("action") == "audit.export" for log in data)


def test_export_requires_admin(client):
    """Sprint 45: export без auth → 401."""
    r = client.get("/api/v1/admin/audit-log/export")
    assert r.status_code == 401


def test_hash_deterministic(client):
    """Sprint 45: _compute_record_hash детерминированный."""
    from app.admin.service import _compute_record_hash

    h1 = _compute_record_hash(
        user_id=1, action="x", entity="y", entity_id="1",
        details='{"a":1}', ip_address="1.1.1.1",
        created_at_iso="2024-01-01T00:00:00", previous_hash="abc",
    )
    h2 = _compute_record_hash(
        user_id=1, action="x", entity="y", entity_id="1",
        details='{"a":1}', ip_address="1.1.1.1",
        created_at_iso="2024-01-01T00:00:00", previous_hash="abc",
    )
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex

    # Изменение любого поля → другой hash
    h3 = _compute_record_hash(
        user_id=1, action="x", entity="y", entity_id="2",  # entity_id changed
        details='{"a":1}', ip_address="1.1.1.1",
        created_at_iso="2024-01-01T00:00:00", previous_hash="abc",
    )
    assert h1 != h3
