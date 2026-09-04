"""Stage 6: ops status endpoint tests."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("UPLOAD_DIR", "/tmp/ai-tutor-test-uploads")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from app.db.session import Base, engine
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(engine)


@pytest.fixture()
def admin_token(client: TestClient) -> str:
    from app.auth.security import hash_password
    from app.db.session import engine
    from app.users.models import Role, User
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        db.add(
            User(
                email="admin@example.com",
                password_hash=hash_password("Kirill2026!"),
                display_name="Admin",
                role=Role.ADMIN,
                is_active=True,
            )
        )
        db.commit()

    r = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "Kirill2026!"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_ops_status_requires_admin(client: TestClient) -> None:
    r = client.get("/api/v1/admin/ops/status")
    assert r.status_code == 401


def test_ops_status_returns_required_checks(client: TestClient, admin_token: str) -> None:
    r = client.get("/api/v1/admin/ops/status", headers={"Authorization": f"Bearer {admin_token}"})

    assert r.status_code == 200
    body = r.json()
    assert "ok" in body
    assert body["checked_at"]
    checks = body["checks"]
    assert checks["database"]["ok"] is True
    assert "redis" in checks
    assert "teacher_registry" in checks
    assert "backup" in checks
    assert "commit_marker" in checks


def test_ops_status_uses_configurable_backup_and_marker_paths(
    client: TestClient,
    admin_token: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cron_path = tmp_path / "ai-tutor-backup"
    script_path = tmp_path / "backup.sh"
    marker_path = tmp_path / ".mvp-rescue-commit"
    cron_path.write_text("0 3 * * * root backup\n")
    script_path.write_text("#!/bin/sh\n")
    marker_path.write_text("abc123\n")

    monkeypatch.setenv("OPS_BACKUP_CRON_PATH", str(cron_path))
    monkeypatch.setenv("OPS_BACKUP_SCRIPT_PATH", str(script_path))
    monkeypatch.setenv("OPS_COMMIT_MARKER_PATH", str(marker_path))

    r = client.get("/api/v1/admin/ops/status", headers={"Authorization": f"Bearer {admin_token}"})

    assert r.status_code == 200
    checks = r.json()["checks"]
    assert checks["backup"]["cron_exists"] is True
    assert checks["backup"]["cron_path"] == str(cron_path)
    assert checks["backup"]["script_exists"] is True
    assert checks["backup"]["script_path"] == str(script_path)
    assert checks["commit_marker"] == {
        "ok": True,
        "path": str(marker_path),
        "commit": "abc123",
    }
