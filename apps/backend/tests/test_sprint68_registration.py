"""Sprint 68: registration security + invite code flow tests.

Покрывает:
- /register: student registration (PUBLIC_REGISTRATION_ALLOWED_ROLES)
- /register: teacher registration BLOCKED (Sprint 16.1)
- /register: admin registration BLOCKED (Sprint 16.1)
- /register-with-invite: invite code redemption (Sprint 44)
- /auth/redeem-invite: validate before register
"""

from __future__ import annotations

import os

# Sprint 64: disable OpenTelemetry для tests
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Sprint 68: TestClient fixture."""
    from app.db.session import Base, engine
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


# === Tests: /auth/register role-based access ===


def test_register_student_allowed(client):
    """Sprint 68: student registration через API (PUBLIC_REGISTRATION_ALLOWED_ROLES)."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "password": "Kirill2026!",
            "display_name": "Student",
            "role": "student",
            "grade": 7,
        },
    )
    assert r.status_code == 201
    assert r.json()["email"] == "student@example.com"
    assert r.json()["role"] == "student"


def test_register_parent_allowed(client):
    """Sprint 68: parent registration через API."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "parent@example.com",
            "password": "Kirill2026!",
            "display_name": "Parent",
            "role": "parent",
        },
    )
    assert r.status_code == 201
    assert r.json()["role"] == "parent"


def test_register_teacher_blocked(client):
    """Sprint 68: teacher registration через API → 403 (Sprint 16.1 PUBLIC_REGISTRATION_ALLOWED_ROLES)."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "teacher@example.com",
            "password": "Kirill2026!",
            "display_name": "Teacher",
            "role": "teacher",
        },
    )
    assert r.status_code == 403
    assert "not available for self-registration" in r.json()["detail"]


def test_register_admin_blocked(client):
    """Sprint 68: admin registration через API → 403."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@example.com",
            "password": "Kirill2026!",
            "display_name": "Admin",
            "role": "admin",
        },
    )
    assert r.status_code == 403


# === Tests: duplicate email ===


def test_register_duplicate_email_rejected(client):
    """Sprint 68: duplicate email → 409."""
    r1 = client.post(
        "/api/v1/auth/register",
        json={
            "email": "dup@example.com",
            "password": "Kirill2026!",
            "display_name": "First",
            "role": "student",
            "grade": 7,
        },
    )
    assert r1.status_code == 201

    r2 = client.post(
        "/api/v1/auth/register",
        json={
            "email": "dup@example.com",
            "password": "Kirill2026!",
            "display_name": "Second",
            "role": "student",
            "grade": 7,
        },
    )
    assert r2.status_code == 409
    assert "already registered" in r2.json()["detail"].lower()


# === Tests: validation ===


def test_register_short_password_rejected(client):
    """Sprint 68: password < 8 chars → 422."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "short@example.com",
            "password": "abc",
            "display_name": "Short",
            "role": "student",
            "grade": 7,
        },
    )
    assert r.status_code == 422


def test_register_invalid_email_rejected(client):
    """Sprint 68: invalid email → 422."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "Kirill2026!",
            "display_name": "Invalid",
            "role": "student",
            "grade": 7,
        },
    )
    assert r.status_code == 422


# === Tests: invite code flow (Sprint 44) ===


def test_register_with_invalid_invite_rejected(client):
    """Sprint 68: invalid invite code → 400."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "inv@example.com",
            "password": "Kirill2026!",
            "display_name": "Inv",
            "role": "student",
            "grade": 7,
            "invite_code": "NONEXISTENT123",
        },
    )
    assert r.status_code == 400
    assert "invalid" in r.json()["detail"].lower()


def test_register_without_invite_works_for_student(client):
    """Sprint 68: student registration без invite_code работает (backward compat)."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "noinv@example.com",
            "password": "Kirill2026!",
            "display_name": "NoInv",
            "role": "student",
            "grade": 7,
        },
    )
    # 201 — backward compatibility сохранена
    assert r.status_code == 201
