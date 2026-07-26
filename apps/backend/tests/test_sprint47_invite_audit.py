"""Sprint 47: audit logging для invites (Sprint 44+45 integration)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.db.session import engine, Base
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def admin_login(client):
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.users.models import User, Role
    from app.auth.security import hash_password

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


def _get_audit_logs(client, admin_token, action: str):
    """Helper: получить audit logs по action."""
    r = client.get(
        f"/api/v1/admin/audit-log?action={action}&limit=50",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    return r.json()


def test_create_invite_logs_audit(client, admin_login):
    """Sprint 47: create_invite → audit log с hash chain."""
    r = client.post(
        "/api/v1/admin/invites",
        json={"role": "student", "note": "Test create"},
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 201
    code = r.json()["code"]

    # Sprint 47: audit log появился
    logs = _get_audit_logs(client, admin_login, "invite.create")
    assert len(logs) >= 1
    log = logs[0]
    assert log["action"] == "invite.create"
    assert log["entity"] == "invite"
    assert log["entity_id"] == code
    # Sprint 45: hash chain populated
    assert log["record_hash"] is not None


def test_delete_invite_logs_audit(client, admin_login):
    """Sprint 47: delete_invite → audit log."""
    # Создаём invite
    r = client.post(
        "/api/v1/admin/invites",
        json={"role": "student"},
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    code = r.json()["code"]

    # Удаляем
    r2 = client.delete(
        f"/api/v1/admin/invites/{code}",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r2.status_code == 204

    # Sprint 47: audit log появился
    logs = _get_audit_logs(client, admin_login, "invite.delete")
    assert len(logs) >= 1
    log = logs[0]
    assert log["action"] == "invite.delete"
    assert log["entity_id"] == code


def test_redeem_invite_logs_audit(client, admin_login):
    """Sprint 47: /auth/redeem-invite → audit log (user=None)."""
    # Создаём invite
    r = client.post(
        "/api/v1/admin/invites",
        json={"role": "student"},
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    code = r.json()["code"]

    # Redeem (public, no auth)
    r2 = client.post(
        "/api/v1/auth/redeem-invite",
        json={"code": code},
    )
    assert r2.status_code == 200

    # Sprint 47: audit log появился
    logs = _get_audit_logs(client, admin_login, "invite.redeem")
    assert len(logs) >= 1
    log = logs[0]
    assert log["action"] == "invite.redeem"
    assert log["entity_id"] == code
    # user=None для public endpoint
    assert log["user_id"] is None
    # details содержит role
    import json
    details = json.loads(log["details"]) if isinstance(log["details"], str) else log["details"]
    assert details["role"] == "student"


def test_invite_audit_chain_integrity(client, admin_login):
    """Sprint 47: invite audit logs в hash chain (Sprint 45 integration)."""
    # Создаём 2 invites + redeem 1
    r1 = client.post(
        "/api/v1/admin/invites",
        json={"role": "student"},
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    code1 = r1.json()["code"]

    r2 = client.post(
        "/api/v1/admin/invites",
        json={"role": "parent"},
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    code2 = r2.json()["code"]

    client.post("/api/v1/auth/redeem-invite", json={"code": code1})

    # Sprint 47: verify chain — все invite audit logs валидны
    r3 = client.get(
        "/api/v1/admin/audit-log/verify",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    data = r3.json()
    assert data["tampered"] == 0
    assert data["chain_broken_at"] is None
    # Минимум 3 валидных записи: create+create+redeem
    assert data["verified"] >= 3


def test_register_via_invite_logs_two_audits(client, admin_login):
    """Sprint 47: register with invite → invite.create + user.register."""
    r = client.post(
        "/api/v1/admin/invites",
        json={"role": "student"},
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    code = r.json()["code"]

    # Register через invite
    r2 = client.post(
        "/api/v1/auth/register",
        json={
            "email": "friend@example.com",
            "password": "Kirill2026!",
            "display_name": "Friend",
            "role": "student",
            "grade": 7,
            "invite_code": code,
        },
    )
    assert r2.status_code == 201

    # Должны быть: invite.create + user.register (2 записи)
    # Sprint 47: invite.redeem НЕ вызывается (register использует invite напрямую)
    create_logs = _get_audit_logs(client, admin_login, "invite.create")
    register_logs = _get_audit_logs(client, admin_login, "user.register")
    assert len(create_logs) >= 1
    assert len(register_logs) >= 1
    # register log содержит invite_code
    import json
    details = json.loads(register_logs[0]["details"]) if isinstance(register_logs[0]["details"], str) else register_logs[0]["details"]
    assert details.get("invite_code") == code

    # Verify chain integrity
    r3 = client.get(
        "/api/v1/admin/audit-log/verify",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    data = r3.json()
    assert data["tampered"] == 0
    assert data["chain_broken_at"] is None