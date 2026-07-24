"""Sprint 16.2 P2-3: регистрация teacher/admin через /auth/register должна быть 403.

Защита через PUBLIC_REGISTRATION_ALLOWED_ROLES = {"student", "parent"}.
Admin/teacher — только через CLI seed_users.py.
"""
from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "mock-token")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.users.models import User, Role
from app.auth.security import hash_password


@pytest.fixture
def client():
    """Создаёт чистую in-memory DB перед каждым тестом."""
    from app.db.session import engine, Base
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


def test_register_admin_returns_403(client):
    """Sprint 1.1 / Sprint 16.2 P2-3: admin нельзя создать через /auth/register."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newadmin@test.com",
            "password": "strongpass1",
            "display_name": "New Admin",
            "role": "admin",
        },
    )
    assert r.status_code == 403
    assert "admin" in r.json().get("detail", "").lower()


def test_register_teacher_returns_403(client):
    """Sprint 1.1: teacher нельзя создать через /auth/register."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newteacher@test.com",
            "password": "strongpass1",
            "display_name": "New Teacher",
            "role": "teacher",
        },
    )
    assert r.status_code == 403
    assert "teacher" in r.json().get("detail", "").lower()


def test_register_student_returns_201(client):
    """Sprint 1.1: student МОЖНО создать через /auth/register."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newstudent@test.com",
            "password": "strongpass1",
            "display_name": "New Student",
            "role": "student",
        },
    )
    assert r.status_code == 201
    assert r.json()["email"] == "newstudent@test.com"
    assert r.json()["role"] == "student"


def test_register_parent_returns_201(client):
    """Sprint 1.1: parent МОЖНО создать через /auth/register."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newparent@test.com",
            "password": "strongpass1",
            "display_name": "New Parent",
            "role": "parent",
        },
    )
    assert r.status_code == 201
    assert r.json()["role"] == "parent"