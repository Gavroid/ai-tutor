"""Тесты audit log и админ-эндпоинтов."""
from __future__ import annotations

import os

os.environ["APP_SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["AI_API_KEY"] = "mock-key-for-tests"

import pytest
from fastapi.testclient import TestClient

from app.admin import models as admin_models
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    s = SessionLocal()
    try:
        # admin создаётся напрямую (через /register нельзя — защита от саморегистрации)
        from app.users.models import User, Role as UserRole
        from app.auth.security import hash_password

        admin = User(
            email="admin@example.com",
            password_hash=hash_password("strongpass1"),
            display_name="Admin",
            role=UserRole.ADMIN,
        )
        s.add(admin)

        user_service.register_user(
            s,
            UserCreate(
                email="kid@example.com",
                password="strongpass1",
                display_name="Кирилл",
                role="student",
                grade=7,
            ),
        )
        s.commit()
    finally:
        s.close()

    def _gen():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _gen
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _login(c: TestClient, email: str) -> str:
    return c.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "strongpass1"},
    ).json()["access_token"]


def test_register_creates_audit_log(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "strongpass1",
            "display_name": "New",
            "role": "student",
            "grade": 7,
        },
    )
    assert r.status_code == 201

    # Проверяем что audit log записан
    s = SessionLocal()
    try:
        logs = s.query(admin_models.AuditLog).all()
        assert len(logs) >= 1
        register_log = next((l for l in logs if l.action == "user.register"), None)
        assert register_log is not None
        assert register_log.entity == "user"
        assert register_log.details is not None
    finally:
        s.close()


def test_audit_log_requires_admin(client):
    kid_token = _login(client, "kid@example.com")
    r = client.get(
        "/api/v1/admin/audit-log",
        headers={"Authorization": f"Bearer {kid_token}"},
    )
    assert r.status_code == 403


def test_admin_can_view_audit_log(client):
    # Создаём событие через API (admin создаётся в фикстуре напрямую)
    client.post(
        "/api/v1/auth/register",
        json={"email": "u1@example.com", "password": "strongpass1", "display_name": "U1", "role": "student"},
    )
    client.post(
        "/api/v1/auth/register",
        json={"email": "u2@example.com", "password": "strongpass1", "display_name": "U2", "role": "student"},
    )

    admin_token = _login(client, "admin@example.com")
    r = client.get(
        "/api/v1/admin/audit-log",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    logs = r.json()
    assert len(logs) >= 2
    actions = [l["action"] for l in logs]
    assert "user.register" in actions


def test_admin_filter_by_user(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "u1@example.com", "password": "strongpass1", "display_name": "U1", "role": "student"},
    )
    admin_token = _login(client, "admin@example.com")

    # user_id = uid ребёнка (создан в фикстуре)
    s = SessionLocal()
    try:
        from app.users import models as user_models

        kid = s.scalar(
            __import__("sqlalchemy").select(user_models.User).where(user_models.User.email == "kid@example.com")
        )
        kid_id = kid.id
    finally:
        s.close()

    r = client.get(
        f"/api/v1/admin/audit-log?user_id={kid_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    # У kid может не быть своих логов — это OK
    logs = r.json()
    for l in logs:
        assert l["user_id"] == kid_id


def test_admin_stats(client):
    admin_token = _login(client, "admin@example.com")
    r = client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_users"] == 2
    assert body["active_users"] == 2
    assert "admin" in body["by_role"]
    assert "student" in body["by_role"]


def test_deactivate_user_records_audit(client):
    admin_token = _login(client, "admin@example.com")
    s = SessionLocal()
    try:
        from app.users import models as user_models

        kid = s.scalar(
            __import__("sqlalchemy").select(user_models.User).where(user_models.User.email == "kid@example.com")
        )
        kid_id = kid.id
    finally:
        s.close()

    r = client.post(
        f"/api/v1/admin/users/{kid_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200

    s = SessionLocal()
    try:
        kid = s.get(__import__("app.users.models", fromlist=["User"]).User, kid_id)
        assert kid.is_active is False
        log = s.query(admin_models.AuditLog).filter_by(action="user.deactivate").first()
        assert log is not None
        assert log.entity_id == str(kid_id)
    finally:
        s.close()


def test_admin_list_users(client):
    admin_token = _login(client, "admin@example.com")
    r = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    users = r.json()
    assert len(users) == 2
    emails = {u["email"] for u in users}
    assert "admin@example.com" in emails
    assert "kid@example.com" in emails
    # Пароль НЕ утекает
    for u in users:
        assert "password" not in u
        assert "password_hash" not in u


def test_self_deactivation_blocked(client):
    """Админ не может деактивировать себя."""
    admin_token = _login(client, "admin@example.com")
    s = SessionLocal()
    try:
        from app.users import models as user_models

        admin = s.scalar(
            __import__("sqlalchemy").select(user_models.User).where(user_models.User.email == "admin@example.com")
        )
        admin_id = admin.id
    finally:
        s.close()

    r = client.post(
        f"/api/v1/admin/users/{admin_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400


def test_notification_test_endpoint_requires_admin(client):
    """POST /admin/notifications/test требует admin."""
    _create_admin(client)
    kid_token = _login_kid(client)
    r = client.post(
        "/api/v1/admin/notifications/test",
        headers={"Authorization": f"Bearer {kid_token}"},
    )
    assert r.status_code == 403


def test_notification_test_endpoint_works(client):
    """POST /admin/notifications/test создаёт запись (dry_run без SMTP)."""
    _create_admin(client)
    admin_token = _login_admin(client)

    r = client.post(
        "/api/v1/admin/notifications/test?email=test@x.com",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("sent", "dry_run", "failed")
    assert "smtp_configured" in body
    assert "record_id" in body

    # Audit log должен содержать notification.test
    r = client.get(
        "/api/v1/admin/audit-log?action=notification.test",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    events = r.json()
    assert len(events) >= 1


def _create_admin(client):
    """Создаём admin в БД напрямую, если его ещё нет."""
    from app.auth.security import hash_password
    from app.users.models import Role, User

    s = SessionLocal()
    try:
        existing = s.query(User).filter_by(email="admin@example.com").first()
        if existing:
            return  # Уже есть
        admin = User(
            email="admin@example.com",
            password_hash=hash_password("strongpass1"),
            display_name="Admin",
            role=Role.ADMIN,
            is_active=True,
        )
        s.add(admin)
        s.commit()
    finally:
        s.close()


def _login_admin(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "strongpass1"},
    )
    return r.json()["access_token"]


def _login_kid(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "kid@example.com", "password": "strongpass1"},
    )
    return r.json()["access_token"]

def test_audit_log_captures_ip_via_middleware(client):
    """Audit log записи получают IP из request contextvar (middleware)."""
    # Register — пишет user.register в audit log
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "audit-ip-test@example.com",
            "password": "strongpass1",
            "display_name": "IP Test",
            "role": "student",
            "grade": 7,
        },
        headers={"X-Forwarded-For": "203.0.113.42, 10.0.0.1"},
    )
    assert r.status_code == 201, r.text

    # Проверяем что audit log получил IP из X-Forwarded-For (первый IP из списка)
    from app.db.session import SessionLocal

    s = SessionLocal()
    try:
        from sqlalchemy import select
        from app.admin.models import AuditLog

        events = s.scalars(
            select(AuditLog)
            .where(AuditLog.action == "user.register")
            .order_by(AuditLog.id.desc())
        ).all()
        assert len(events) >= 1
        # X-Forwarded-For: первый IP — 203.0.113.42
        assert events[0].ip_address is not None
        assert "203" in events[0].ip_address
    finally:
        s.close()
