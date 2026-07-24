"""Sprint 44: Public invite flow tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture
def client():
    from app.db.session import engine, Base
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def admin_login(client):
    """Sprint 44: admin login (через прямой SQL)."""
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


def test_create_invite_admin(client, admin_login):
    """Sprint 44: admin может создать invite."""
    r = client.post(
        "/api/v1/admin/invites",
        json={"role": "student", "note": "Friend of Kirill"},
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert "code" in data
    assert len(data["code"]) == 8
    assert data["role"] == "student"
    assert data["note"] == "Friend of Kirill"
    assert data["is_valid"] is True


def test_list_invites(client, admin_login):
    """Sprint 44: list invites возвращает созданные."""
    client.post(
        "/api/v1/admin/invites",
        json={"role": "student", "note": "Test"},
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    r = client.get(
        "/api/v1/admin/invites",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["code"]


def test_create_invite_requires_admin(client):
    """Sprint 44: без auth → 401."""
    r = client.post(
        "/api/v1/admin/invites",
        json={"role": "student"},
    )
    assert r.status_code == 401


def test_redeem_invite_valid(client, admin_login):
    """Sprint 44: public redeem-invite для валидного кода."""
    # Создаём invite
    r = client.post(
        "/api/v1/admin/invites",
        json={"role": "student"},
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    code = r.json()["code"]

    # Redeem (public, без auth)
    r2 = client.post(
        "/api/v1/auth/redeem-invite",
        json={"code": code},
    )
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["valid"] is True
    assert data["role"] == "student"
    assert data["remaining_uses"] == 1


def test_redeem_invite_invalid_404(client):
    """Sprint 44: несуществующий code → 404."""
    r = client.post(
        "/api/v1/auth/redeem-invite",
        json={"code": "BADCODE"},
    )
    assert r.status_code == 404


def test_register_with_invite_creates_user(client, admin_login):
    """Sprint 44: register с valid invite создаёт user."""
    r = client.post(
        "/api/v1/admin/invites",
        json={"role": "student"},
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    code = r.json()["code"]

    # Register with invite
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
    assert r2.status_code == 201, r2.text
    data = r2.json()
    assert data["email"] == "friend@example.com"

    # Verify invite marked as used
    r3 = client.get(
        f"/api/v1/admin/invites/{code}",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    invite = r3.json()
    assert invite["uses_count"] == 1
    assert invite["is_valid"] is False  # used up


def test_register_with_invalid_invite_fails(client):
    """Sprint 44: register с невалидным invite → 400."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "friend@example.com",
            "password": "Kirill2026!",
            "display_name": "Friend",
            "role": "student",
            "grade": 7,
            "invite_code": "BADCODE",
        },
    )
    assert r.status_code == 400


def test_invite_max_uses(client, admin_login):
    """Sprint 44: max_uses=2 → можно использовать дважды."""
    r = client.post(
        "/api/v1/admin/invites",
        json={"role": "student", "max_uses": 2},
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    code = r.json()["code"]

    # First registration
    r1 = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user1@example.com",
            "password": "Kirill2026!",
            "display_name": "User 1",
            "role": "student",
            "grade": 7,
            "invite_code": code,
        },
    )
    assert r1.status_code == 201

    # Second registration
    r2 = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user2@example.com",
            "password": "Kirill2026!",
            "display_name": "User 2",
            "role": "student",
            "grade": 7,
            "invite_code": code,
        },
    )
    assert r2.status_code == 201

    # Third should fail
    r3 = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user3@example.com",
            "password": "Kirill2026!",
            "display_name": "User 3",
            "role": "student",
            "grade": 7,
            "invite_code": code,
        },
    )
    assert r3.status_code == 400


def test_delete_invite(client, admin_login):
    """Sprint 44: unused invite можно удалить."""
    r = client.post(
        "/api/v1/admin/invites",
        json={"role": "student"},
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    code = r.json()["code"]

    r2 = client.delete(
        f"/api/v1/admin/invites/{code}",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r2.status_code == 204

    # Verify deleted
    r3 = client.get(
        f"/api/v1/admin/invites/{code}",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r3.status_code == 404