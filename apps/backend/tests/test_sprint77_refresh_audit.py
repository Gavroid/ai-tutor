"""Sprint 77: refresh token audit logging tests (Kimi P1-3)."""

from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Sprint 77: TestClient + DB setup."""
    from app.db.session import Base, engine
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def tokens(client):
    """Sprint 77: login + return tokens (access + refresh)."""
    from app.auth.security import hash_password
    from app.db.session import engine
    from app.users.models import Role, User
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        user = User(
            email="user@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="User",
            role=Role.STUDENT,
            is_active=True,
        )
        db.add(user)
        db.commit()

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "Kirill2026!"},
    )
    return r.json()


# === Tests: refresh token logs audit ===


def test_refresh_logs_audit_record(client, tokens):
    """Sprint 77: refresh endpoint creates audit_log record."""
    refresh_token = tokens["refresh_token"]

    r = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert r.status_code == 200
    assert "access_token" in r.json()

    # Verify audit log entry
    from app.admin.models import AuditLog
    from app.db.session import engine
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        logs = db.query(AuditLog).filter(AuditLog.action == "auth.refresh").all()
        assert len(logs) >= 1, f"Expected >=1 refresh log, got {len(logs)}"
        log = logs[-1]
        assert log.action == "auth.refresh"
        assert log.entity == "user"
        assert log.details is not None


def test_refresh_via_cookie_logs_audit(client, tokens):
    """Sprint 77: refresh via cookie also logs audit."""
    refresh_token = tokens["refresh_token"]

    # Use cookie-based refresh (Sprint 27 migration)
    client.cookies.set("ai_tutor_refresh", refresh_token)

    r = client.post(
        "/api/v1/auth/refresh",
        json={},  # No body, use cookie
    )
    assert r.status_code == 200

    # Verify audit
    from app.admin.models import AuditLog
    from app.db.session import engine
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        logs = db.query(AuditLog).filter(AuditLog.action == "auth.refresh").all()
        # Should be 2 logs now (body + cookie)
        assert len(logs) >= 1  # at least one refresh logged


def test_refresh_invalid_token_no_audit(client, tokens):
    """Sprint 77: invalid refresh token → 401 + NO audit log."""
    r = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_token_garbage_1234567890"},
    )
    assert r.status_code == 401

    # Verify NO audit log для invalid refresh
    from app.admin.models import AuditLog
    from app.db.session import engine
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        logs = db.query(AuditLog).filter(AuditLog.action == "auth.refresh").all()
        # Should be 0 (no successful refresh)
        assert len(logs) == 0, f"Expected 0 audit logs for failed refresh, got {len(logs)}"


def test_refresh_logs_via_field(client, tokens):
    """Sprint 77: details['via'] указывает source (body vs cookie)."""
    refresh_token = tokens["refresh_token"]

    r = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert r.status_code == 200

    # Verify details
    import json

    from app.admin.models import AuditLog
    from app.db.session import engine
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        log = db.query(AuditLog).filter(AuditLog.action == "auth.refresh").order_by(AuditLog.id.desc()).first()
        details = json.loads(log.details) if log.details else {}
        assert details.get("via") in ("body", "cookie")
        assert details.get("rotation") is True
