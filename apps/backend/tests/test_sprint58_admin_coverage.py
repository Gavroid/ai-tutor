"""Sprint 58: admin router coverage tests.

Покрывает endpoints в app/admin/router.py:
- /audit-log (list + filter)
- /audit-log/count
- /audit-log/verify
- /audit-log/export
- /audit-log/purge
- /users (list)
- /users/{user_id}/deactivate
- /stats
- /engagement
- /diagnostics/expire-stale
- /notifications/test
- /ai-kill-switch (GET/POST/DELETE)
"""
from __future__ import annotations

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
    """Sprint 58: admin login через прямой SQL."""
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


def test_audit_log_list_no_filter(client, admin_login):
    """Sprint 58: GET /audit-log без filter."""
    r = client.get(
        "/api/v1/admin/audit-log",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_audit_log_list_with_action_filter(client, admin_login):
    """Sprint 58: GET /audit-log с filter по action."""
    r = client.get(
        "/api/v1/admin/audit-log?action=audit.export&limit=5",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200


def test_audit_log_list_with_pagination(client, admin_login):
    """Sprint 58: GET /audit-log с pagination."""
    r = client.get(
        "/api/v1/admin/audit-log?limit=10&offset=0",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200


def test_audit_log_list_with_since_until(client, admin_login):
    """Sprint 58: GET /audit-log с date range."""
    r = client.get(
        "/api/v1/admin/audit-log?since=2024-01-01T00:00:00&until=2026-12-31T23:59:59",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200


def test_audit_log_list_unauthorized(client):
    """Sprint 58: GET /audit-log без auth → 401."""
    r = client.get("/api/v1/admin/audit-log")
    assert r.status_code == 401


def test_audit_log_count(client, admin_login):
    """Sprint 58: GET /audit-log/count."""
    r = client.get(
        "/api/v1/admin/audit-log/count",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    # Response содержит total или count (в зависимости от endpoint)
    assert isinstance(data.get("total", data.get("count", 0)), int)


def test_audit_log_count_with_filter(client, admin_login):
    """Sprint 58: GET /audit-log/count с filter."""
    r = client.get(
        "/api/v1/admin/audit-log/count?action=test.action",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200


def test_audit_log_count_invalid_action(client, admin_login):
    """Sprint 58: GET /audit-log/count с invalid action param."""
    r = client.get(
        "/api/v1/admin/audit-log/count?action=",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    # Empty action filter должен работать
    assert r.status_code == 200


def test_audit_log_verify_empty(client, admin_login):
    """Sprint 58: GET /audit-log/verify на empty DB."""
    r = client.get(
        "/api/v1/admin/audit-log/verify",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "verified" in data
    assert "tampered" in data
    assert "total_checked" in data


def test_audit_log_verify_with_limit(client, admin_login):
    """Sprint 58: GET /audit-log/verify с custom limit."""
    r = client.get(
        "/api/v1/admin/audit-log/verify?limit=100",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200


def test_audit_log_verify_invalid_limit(client, admin_login):
    """Sprint 58: GET /audit-log/verify с invalid limit (>10000)."""
    r = client.get(
        "/api/v1/admin/audit-log/verify?limit=99999",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    # Should return 422 (validation error)
    assert r.status_code == 422


def test_audit_log_export_json(client, admin_login):
    """Sprint 58: GET /audit-log/export?fmt=json."""
    r = client.get(
        "/api/v1/admin/audit-log/export?fmt=json&limit=5",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_audit_log_export_csv(client, admin_login):
    """Sprint 58: GET /audit-log/export?fmt=csv."""
    r = client.get(
        "/api/v1/admin/audit-log/export?fmt=csv&limit=5",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data
    assert "content" in data
    assert "audit_log_csv.csv" in data["filename"]


def test_audit_log_export_invalid_format(client, admin_login):
    """Sprint 58: GET /audit-log/export с invalid fmt."""
    r = client.get(
        "/api/v1/admin/audit-log/export?fmt=xml",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    # 422 — pattern validation error
    assert r.status_code == 422


def test_audit_log_export_unauthorized(client):
    """Sprint 58: GET /audit-log/export без auth → 401."""
    r = client.get("/api/v1/admin/audit-log/export?fmt=json")
    assert r.status_code == 401


def test_audit_log_purge(client, admin_login):
    """Sprint 58: POST /audit-log/purge."""
    r = client.post(
        "/api/v1/admin/audit-log/purge?ttl_days=90",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "ok" in data
    assert "deleted_count" in data


def test_audit_log_purge_custom_ttl(client, admin_login):
    """Sprint 58: POST /audit-log/purge с custom TTL."""
    r = client.post(
        "/api/v1/admin/audit-log/purge?ttl_days=30",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200


def test_users_list(client, admin_login):
    """Sprint 58: GET /users."""
    r = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_users_list_with_filter(client, admin_login):
    """Sprint 58: GET /users с role filter."""
    r = client.get(
        "/api/v1/admin/users?role=student",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200


def test_users_list_unauthorized(client):
    """Sprint 58: GET /users без auth → 401."""
    r = client.get("/api/v1/admin/users")
    assert r.status_code == 401


def test_user_deactivate(client, admin_login):
    """Sprint 58: POST /users/{id}/deactivate."""
    # Создаём user для deactivate
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "todelete@example.com",
            "password": "Kirill2026!",
            "display_name": "ToDelete",
            "role": "student",
            "grade": 7,
        },
    )
    assert r.status_code == 201
    user_id = r.json()["id"]

    # Deactivate
    r2 = client.post(
        f"/api/v1/admin/users/{user_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r2.status_code == 200
    assert r2.json().get("ok") is True


def test_user_deactivate_nonexistent(client, admin_login):
    """Sprint 58: deactivate несуществующего user → 404."""
    r = client.post(
        "/api/v1/admin/users/999999/deactivate",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 404


def test_user_deactivate_self_protection(client, admin_login):
    """Sprint 58: admin не может deactivate себя."""
    # Получаем свой ID
    r = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    admin_id = r.json()["id"]

    # Try to deactivate self
    r2 = client.post(
        f"/api/v1/admin/users/{admin_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    # Должно быть запрещено (400 или 409)
    assert r2.status_code in (400, 409)


def test_admin_stats(client, admin_login):
    """Sprint 58: GET /stats."""
    r = client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "total_users" in data or "by_role" in data


def test_admin_engagement(client, admin_login):
    """Sprint 58: GET /engagement."""
    r = client.get(
        "/api/v1/admin/engagement",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200


def test_admin_engagement_with_days(client, admin_login):
    """Sprint 58: GET /engagement с days param."""
    r = client.get(
        "/api/v1/admin/engagement?days=7",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200


def test_admin_diagnostics_expire_stale(client, admin_login):
    """Sprint 58: POST /diagnostics/expire-stale."""
    r = client.post(
        "/api/v1/admin/diagnostics/expire-stale",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code in (200, 204)


def test_admin_notifications_test(client, admin_login):
    """Sprint 58: POST /notifications/test."""
    r = client.post(
        "/api/v1/admin/notifications/test",
        json={"email": "test@example.com", "subject": "Test", "body": "Test"},
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    # Может быть 200 или 503 (если SMTP не настроен)
    assert r.status_code in (200, 400, 503)


def test_ai_kill_switch_list(client, admin_login):
    """Sprint 58: GET /ai-kill-switch."""
    r = client.get(
        "/api/v1/admin/ai-kill-switch",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r.status_code == 200


def test_ai_kill_switch_add_remove(client, admin_login):
    """Sprint 58: POST + DELETE /ai-kill-switch/{user_id}."""
    # Add
    r1 = client.post(
        "/api/v1/admin/ai-kill-switch/999",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r1.status_code in (200, 201)

    # Verify
    r2 = client.get(
        "/api/v1/admin/ai-kill-switch",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r2.status_code == 200

    # Remove
    r3 = client.delete(
        "/api/v1/admin/ai-kill-switch/999",
        headers={"Authorization": f"Bearer {admin_login}"},
    )
    assert r3.status_code in (200, 204)


def test_admin_endpoints_require_auth(client):
    """Sprint 58: все admin endpoints требуют auth."""
    endpoints = [
        "/api/v1/admin/audit-log",
        "/api/v1/admin/audit-log/count",
        "/api/v1/admin/audit-log/verify",
        "/api/v1/admin/audit-log/export?fmt=json",
        "/api/v1/admin/users",
        "/api/v1/admin/stats",
        "/api/v1/admin/engagement",
        "/api/v1/admin/ai-kill-switch",
    ]
    for ep in endpoints:
        r = client.get(ep) if not ep.endswith("audit-log/purge") else client.post(ep)
        # Должно быть 401 (без auth)
        assert r.status_code == 401, f"{ep} should be 401, got {r.status_code}"
