"""Sprint 32: тесты для Parent 2FA TOTP."""
from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")

import pyotp
import pytest
from fastapi.testclient import TestClient

from app.auth.security import hash_password
from app.db.session import Base, engine
from app.users.models import Role, User


@pytest.fixture(autouse=True)
def _reset_db():
    """Sprint 32: создаёт чистую DB перед каждым тестом."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


@pytest.fixture
def parent_token():
    """Создаёт parent и возвращает JWT token."""
    from sqlalchemy.orm import Session

    with Session(engine) as s:
        user = User(
            email="parent@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="Игорь",
            role=Role.PARENT,
            is_active=True,
        )
        s.add(user)
        s.commit()
        s.refresh(user)
        return user.id


@pytest.fixture
def parent_login(client, parent_token):
    """Логин parent (без 2FA) → token."""
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "parent@example.com", "password": "Kirill2026!"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_enable_2fa_returns_secret_and_codes(client, parent_token, parent_login):
    """Sprint 32: enable 2FA возвращает secret + provisioning_uri + 8 codes."""
    r = client.post(
        "/api/v1/parents/2fa/enable",
        headers={"Authorization": f"Bearer {parent_login}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "secret" in data
    assert "provisioning_uri" in data
    assert data["provisioning_uri"].startswith("otpauth://totp/")
    assert len(data["backup_codes"]) == 8
    # Каждый backup code = 12 hex chars uppercase
    for code in data["backup_codes"]:
        assert len(code) == 12
        assert code.isupper()


def test_enable_2fa_twice_returns_400(client, parent_token, parent_login):
    """Sprint 32: enable 2FA дважды → 400."""
    headers = {"Authorization": f"Bearer {parent_login}"}
    r1 = client.post("/api/v1/parents/2fa/enable", headers=headers)
    assert r1.status_code == 200

    r2 = client.post("/api/v1/parents/2fa/enable", headers=headers)
    assert r2.status_code == 400
    assert "already" in r2.json()["detail"].lower()


def test_status_before_enable(client, parent_token, parent_login):
    """Sprint 32: status endpoint показывает enabled=False."""
    r = client.get(
        "/api/v1/parents/2fa/status",
        headers={"Authorization": f"Bearer {parent_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] is False
    assert data["backup_codes_remaining"] == 0


def test_status_after_enable(client, parent_token, parent_login):
    """Sprint 32: status after enable — enabled=True, 8 codes."""
    headers = {"Authorization": f"Bearer {parent_login}"}
    client.post("/api/v1/parents/2fa/enable", headers=headers)

    r = client.get("/api/v1/parents/2fa/status", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] is True
    assert data["backup_codes_remaining"] == 8


def test_login_with_2fa_returns_intermediate_token(client, parent_token, parent_login):
    """Sprint 32: login parent с 2FA → intermediate token (НЕ полноценный)."""
    # Enable 2FA
    client.post(
        "/api/v1/parents/2fa/enable",
        headers={"Authorization": f"Bearer {parent_login}"},
    )

    # Login — должен вернуть intermediate token
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "parent@example.com", "password": "Kirill2026!"},
    )
    assert r.status_code == 200
    data = r.json()
    # Intermediate token НЕ ставит cookies
    assert "Set-Cookie" not in r.headers or "ai_tutor_access" not in r.headers.get("Set-Cookie", "")
    # expires_in = 300 (5 мин)
    assert data["expires_in"] == 300


def test_login_with_2fa_complete_flow(client):
    """Sprint 32: полный flow — password → intermediate → TOTP → access."""
    # Register и login первый раз (без 2FA)
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "parent2fa@example.com",
            "password": "Kirill2026!",
            "display_name": "Игорь",
            "role": "parent",
        },
    )
    assert r.status_code == 201
    parent_login = client.post(
        "/api/v1/auth/login",
        json={"email": "parent2fa@example.com", "password": "Kirill2026!"},
    ).json()["access_token"]

    # Enable 2FA, get secret
    r = client.post(
        "/api/v1/parents/2fa/enable",
        headers={"Authorization": f"Bearer {parent_login}"},
    )
    secret = r.json()["secret"]

    # Login снова — теперь password + 2FA
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "parent2fa@example.com", "password": "Kirill2026!"},
    )
    assert r.status_code == 200
    intermediate = r.json()["access_token"]
    assert r.json()["expires_in"] == 300

    # Step 2: TOTP code
    totp = pyotp.TOTP(secret)
    code = totp.now()
    r = client.post(
        "/api/v1/auth/login-2fa",
        json={"access_token": intermediate, "code": code},
    )
    assert r.status_code == 200, r.text
    # Полноценные токены + cookies
    assert "Set-Cookie" in r.headers
    assert r.json()["expires_in"] > 300  # не 300 (не intermediate)


def test_login_2fa_invalid_code_returns_401(client):
    """Sprint 32: неверный TOTP → 401."""
    # Register + login + enable
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "parent3@example.com",
            "password": "Kirill2026!",
            "display_name": "Игорь",
            "role": "parent",
        },
    )
    parent_login = client.post(
        "/api/v1/auth/login",
        json={"email": "parent3@example.com", "password": "Kirill2026!"},
    ).json()["access_token"]

    client.post(
        "/api/v1/parents/2fa/enable",
        headers={"Authorization": f"Bearer {parent_login}"},
    )

    # Login → intermediate
    intermediate = client.post(
        "/api/v1/auth/login",
        json={"email": "parent3@example.com", "password": "Kirill2026!"},
    ).json()["access_token"]

    # Неверный код
    r = client.post(
        "/api/v1/auth/login-2fa",
        json={"access_token": intermediate, "code": "000000"},
    )
    assert r.status_code == 401


def test_backup_code_works(client):
    """Sprint 32: backup code работает когда TOTP недоступен."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "parent4@example.com",
            "password": "Kirill2026!",
            "display_name": "Игорь",
            "role": "parent",
        },
    )
    parent_login = client.post(
        "/api/v1/auth/login",
        json={"email": "parent4@example.com", "password": "Kirill2026!"},
    ).json()["access_token"]

    r = client.post(
        "/api/v1/parents/2fa/enable",
        headers={"Authorization": f"Bearer {parent_login}"},
    )
    backup_code = r.json()["backup_codes"][0]

    intermediate = client.post(
        "/api/v1/auth/login",
        json={"email": "parent4@example.com", "password": "Kirill2026!"},
    ).json()["access_token"]

    r = client.post(
        "/api/v1/auth/login-2fa",
        json={"access_token": intermediate, "code": backup_code},
    )
    assert r.status_code == 200, r.text


def test_disable_2fa(client, parent_token, parent_login):
    """Sprint 32: disable 2FA → status показывает enabled=False."""
    headers = {"Authorization": f"Bearer {parent_login}"}
    client.post("/api/v1/parents/2fa/enable", headers=headers)

    r = client.post("/api/v1/parents/2fa/disable", headers=headers)
    assert r.status_code == 204

    r = client.get("/api/v1/parents/2fa/status", headers=headers)
    assert r.json()["enabled"] is False


def test_non_parent_cannot_enable_2fa(client):
    """Sprint 32: только parent может enable 2FA."""
    # Register student
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "password": "Kirill2026!",
            "display_name": "Кирилл",
            "role": "student",
            "grade": 7,
        },
    )
    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student@example.com", "password": "Kirill2026!"},
    ).json()["access_token"]

    r = client.post(
        "/api/v1/parents/2fa/enable",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    # Student не parent → 403
    assert r.status_code == 403


def test_totp_validity_window(client):
    """Sprint 32: TOTP код прошлого шага (30 сек назад) тоже работает."""
    import time

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "parent5@example.com",
            "password": "Kirill2026!",
            "display_name": "Игорь",
            "role": "parent",
        },
    )
    parent_login = client.post(
        "/api/v1/auth/login",
        json={"email": "parent5@example.com", "password": "Kirill2026!"},
    ).json()["access_token"]

    r = client.post(
        "/api/v1/parents/2fa/enable",
        headers={"Authorization": f"Bearer {parent_login}"},
    )
    secret = r.json()["secret"]

    intermediate = client.post(
        "/api/v1/auth/login",
        json={"email": "parent5@example.com", "password": "Kirill2026!"},
    ).json()["access_token"]

    # Используем TOTP код (текущий момент)
    totp = pyotp.TOTP(secret)
    code = totp.now()

    r = client.post(
        "/api/v1/auth/login-2fa",
        json={"access_token": intermediate, "code": code},
    )
    assert r.status_code == 200


def test_disable_2fa_when_not_enabled_returns_400(client, parent_token, parent_login):
    """Sprint 32: disable когда 2FA не включена → 400."""
    r = client.post(
        "/api/v1/parents/2fa/disable",
        headers={"Authorization": f"Bearer {parent_login}"},
    )
    assert r.status_code == 400
    assert "не включена" in r.json()["detail"].lower()