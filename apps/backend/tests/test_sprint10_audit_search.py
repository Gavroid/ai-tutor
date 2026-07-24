"""Sprint 10.4 — тесты audit log search/filter.

Тесты проверяют:
- Фильтр по entity (users, exercises, ai-kill-switch и т.д.)
- Новый endpoint audit-log/count возвращает total count
- Pagination через limit/offset
- Комбинированные фильтры (entity + user_id + since)
- Pagination для маленьких/больших результатов
- ISO date parsing для since/until
- Bad date → 400
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")

import json

import pytest
from fastapi.testclient import TestClient

from app.admin import models as audit_models
from app.admin import service as audit_service
from app.auth.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.users import models as user_models


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    yield TestClient(app)
    Base.metadata.drop_all(engine)
    engine.dispose()


def _create_admin(s) -> int:
    user = user_models.User(
        email="admin@example.com",
        password_hash=hash_password("strongpass1"),
        display_name="Admin",
        role="admin",
        is_active=True,
    )
    s.add(user)
    s.commit()
    s.refresh(user)
    return user.id


def _login_admin(client) -> str:
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "strongpass1"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _add_log(s, action, entity="users", user_id=None, days_ago=0, details=None) -> int:
    """Добавляет audit_log запись с заданным action/entity."""
    when = datetime.now(timezone.utc) - timedelta(days=days_ago)
    entry = audit_models.AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=None,
        details=json.dumps(details) if details else None,
        ip_address="127.0.0.1",
        created_at=when,
    )
    s.add(entry)
    s.commit()
    s.refresh(entry)
    return entry.id


# === Filter by entity ===

def test_audit_filter_by_entity(client):
    """Sprint 10.4: GET /admin/audit-log?entity=exercises вернёт только exercises логи."""
    s = SessionLocal()
    try:
        admin_id = _create_admin(s)
        _add_log(s, "user.create", entity="users", user_id=admin_id)
        _add_log(s, "exercise.submit", entity="exercises", user_id=admin_id)
        _add_log(s, "exercise.complete", entity="exercises", user_id=admin_id)
        _add_log(s, "ai.explain", entity="ai", user_id=admin_id)
    finally:
        s.close()

    token = _login_admin(client)
    r = client.get(
        "/api/v1/admin/audit-log?entity=exercises",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    for entry in body:
        assert entry["entity"] == "exercises"
        assert entry["action"] in ["exercise.submit", "exercise.complete"]


def test_audit_filter_combines_entity_and_action(client):
    """Sprint 10.4: filter по entity AND action."""
    s = SessionLocal()
    try:
        admin_id = _create_admin(s)
        _add_log(s, "exercise.submit", entity="exercises", user_id=admin_id)
        _add_log(s, "exercise.complete", entity="exercises", user_id=admin_id)
        _add_log(s, "user.create", entity="users", user_id=admin_id)
    finally:
        s.close()

    token = _login_admin(client)
    r = client.get(
        "/api/v1/admin/audit-log?entity=exercises&action=exercise.submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert len(body) == 1
    assert body[0]["action"] == "exercise.submit"
    assert body[0]["entity"] == "exercises"


# === Count endpoint ===

def test_audit_log_count_basic(client):
    """Sprint 10.4: GET /admin/audit-log/count возвращает total."""
    s = SessionLocal()
    try:
        admin_id = _create_admin(s)
        for i in range(7):
            _add_log(s, f"user.create.{i}", entity="users", user_id=admin_id)
    finally:
        s.close()

    token = _login_admin(client)
    r = client.get(
        "/api/v1/admin/audit-log/count",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert body["total"] == 7


def test_audit_log_count_filters(client):
    """Sprint 10.4: count с фильтром по entity."""
    s = SessionLocal()
    try:
        admin_id = _create_admin(s)
        _add_log(s, "user.create", entity="users", user_id=admin_id)
        _add_log(s, "user.create", entity="users", user_id=admin_id)
        _add_log(s, "exercise.submit", entity="exercises", user_id=admin_id)
    finally:
        s.close()

    token = _login_admin(client)
    r = client.get(
        "/api/v1/admin/audit-log/count?entity=users",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert body["total"] == 2


# === Pagination ===

def test_audit_pagination_limit_offset(client):
    """Sprint 10.4: pagination через limit/offset."""
    s = SessionLocal()
    try:
        admin_id = _create_admin(s)
        for i in range(10):
            _add_log(s, f"event.{i}", entity="test", user_id=admin_id)
    finally:
        s.close()

    token = _login_admin(client)
    r = client.get(
        "/api/v1/admin/audit-log?limit=3&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    body1 = r.json()
    assert len(body1) == 3

    r = client.get(
        "/api/v1/admin/audit-log?limit=3&offset=6",
        headers={"Authorization": f"Bearer {token}"},
    )
    body2 = r.json()
    assert len(body2) == 3

    # Pagination не должна возвращать дубликаты
    ids1 = {e["id"] for e in body1}
    ids2 = {e["id"] for e in body2}
    assert ids1.isdisjoint(ids2)


def test_audit_limit_max_500(client):
    """Sprint 16.0 P0-8: limit > 500 теперь возвращает 422, не silent clamp."""
    s = SessionLocal()
    try:
        admin_id = _create_admin(s)
        _add_log(s, "test.event", entity="users", user_id=admin_id)
    finally:
        s.close()

    token = _login_admin(client)
    # limit=99999 — должно быть 422 (Query validator: le=500)
    r = client.get(
        "/api/v1/admin/audit-log?limit=99999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422

    # limit=500 (на границе) — должно быть 200
    r = client.get(
        "/api/v1/admin/audit-log?limit=500",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


# === Date filters ===

def test_audit_since_filter(client):
    """Sprint 10.4: фильтр since — только events после даты."""
    from urllib.parse import quote

    s = SessionLocal()
    try:
        admin_id = _create_admin(s)
        _add_log(s, "old.event", entity="users", user_id=admin_id, days_ago=10)
        _add_log(s, "new.event", entity="users", user_id=admin_id, days_ago=1)
    finally:
        s.close()

    token = _login_admin(client)
    since = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    # URL-encode '+' (требуется для ISO datetime)
    since_encoded = quote(since, safe="")
    r = client.get(
        f"/api/v1/admin/audit-log?since={since_encoded}",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    # Только новая запись
    assert len(body) == 1
    assert body[0]["action"] == "new.event"


def test_audit_bad_since_returns_400(client):
    """Sprint 10.4: некорректный since → 400."""
    s = SessionLocal()
    try:
        _create_admin(s)
    finally:
        s.close()

    token = _login_admin(client)
    r = client.get(
        "/api/v1/admin/audit-log?since=not-a-date",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    assert "Некорректный since" in r.json()["detail"]


# === Auth required ===

def test_audit_log_requires_admin(client):
    """Sprint 10.4: audit endpoints требуют admin role."""
    s = SessionLocal()
    try:
        # Создаём student (без admin)
        u = user_models.User(
            email="student@example.com",
            password_hash=hash_password("strongpass1"),
            display_name="Student",
            role="student",
            is_active=True,
        )
        s.add(u)
        s.commit()
    finally:
        s.close()

    # Login как student
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "student@example.com", "password": "strongpass1"},
    )
    student_token = r.json()["access_token"]

    # GET /audit-log → 403
    r = client.get(
        "/api/v1/admin/audit-log",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 403

    # GET /audit-log/count → 403
    r = client.get(
        "/api/v1/admin/audit-log/count",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 403


def test_audit_log_no_auth_returns_401(client):
    """Sprint 10.4: без auth → 401."""
    r = client.get("/api/v1/admin/audit-log")
    assert r.status_code == 401


# === Combined filters ===

def test_audit_combined_filters_all(client):
    """Sprint 10.4: все фильтры вместе."""
    from urllib.parse import quote

    s = SessionLocal()
    try:
        admin_id = _create_admin(s)
        # 3 events matching all criteria
        for _ in range(3):
            _add_log(s, "user.delete", entity="users", user_id=admin_id, days_ago=1)
        # noise
        _add_log(s, "old.event", entity="users", user_id=admin_id, days_ago=30)
        _add_log(s, "wrong.entity", entity="ai", user_id=admin_id, days_ago=1)
        _add_log(s, "wrong.user", entity="users", user_id=None, days_ago=1)
    finally:
        s.close()

    token = _login_admin(client)
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    since_encoded = quote(since, safe="")
    r = client.get(
        f"/api/v1/admin/audit-log?action=user.delete&entity=users"
        f"&since={since_encoded}&limit=100",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    # 3 events matching delete + users + last 7 days
    assert len(body) == 3
    for e in body:
        assert e["action"] == "user.delete"
        assert e["entity"] == "users"


# === Empty results ===

def test_audit_no_matching_logs_returns_empty_list(client):
    """Sprint 10.4: нет matching записей → пустой list, не 500."""
    s = SessionLocal()
    try:
        admin_id = _create_admin(s)
        _add_log(s, "user.create", entity="users", user_id=admin_id)
    finally:
        s.close()

    token = _login_admin(client)
    r = client.get(
        "/api/v1/admin/audit-log?action=non.existent",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert body == []


def test_audit_log_count_zero(client):
    """Sprint 10.4: count с фильтром не находит → total=0."""
    s = SessionLocal()
    try:
        _create_admin(s)
    finally:
        s.close()

    token = _login_admin(client)
    r = client.get(
        "/api/v1/admin/audit-log/count",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.json() == {"total": 0}
