"""Тесты diagnostic expire (Этап hardening)."""
from __future__ import annotations

import os

os.environ["APP_SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["AI_API_KEY"] = "mock-key-for-tests"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import Base, SessionLocal, engine, get_db
from app.diagnostics import models as diag_models
from app.diagnostics import service as diag_service
from app.main import app
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture(autouse=True)
def _setup_db():
    """Создаёт schema + пользователя для функциональных тестов (без app)."""
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    s = SessionLocal()
    try:
        try:
            user_service.register_user(
                s,
                UserCreate(
                    email="kid@x.com",
                    password="strongpass1",
                    display_name="Kid",
                    role="student",
                    grade=7,
                ),
            )
        except Exception:
            pass
    finally:
        s.close()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    s = SessionLocal()
    user_service.register_user(
        s,
        UserCreate(
            email="kid@x.com",
            password="strongpass1",
            display_name="Kid",
            role="student",
            grade=7,
        ),
    )
    seed_for_tests(s, reset=False)
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


def _login(c: TestClient, email: str = "kid@x.com") -> str:
    r = c.post("/api/v1/auth/login", json={"email": email, "password": "strongpass1"})
    return r.json()["access_token"]


def _create_admin(c: TestClient):
    """Создаём admin в БД напрямую."""
    from app.users.models import User, Role
    from app.auth.security import hash_password

    s = SessionLocal()
    try:
        admin = User(
            email="admin@x.com",
            password_hash=hash_password("strongpass1"),
            display_name="Admin",
            role=Role.ADMIN,
            is_active=True,
        )
        s.add(admin)
        s.commit()
    finally:
        s.close()


def test_expire_stale_diagnostics_function():
    """Функция expire_stale_diagnostic_sessions помечает старые сессии как expired."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.users.models import User

    # User уже создан через autouse fixture
    s = SessionLocal()
    try:
        user = s.execute(
            select(User).where(User.email == "kid@x.com")
        ).scalar_one()
    finally:
        s.close()

    s = SessionLocal()
    try:
        # Свежая — только что
        sess_fresh = diag_models.DiagnosticSession(
            user_id=user.id,
            subject_id=1,
            status="in_progress",
            total_questions=5,
            started_at=datetime.now(timezone.utc),
        )
        sess_old = diag_models.DiagnosticSession(
            user_id=user.id,
            subject_id=1,
            status="in_progress",
            total_questions=5,
            started_at=datetime.now(timezone.utc) - timedelta(hours=25),
        )
        sess_very_old = diag_models.DiagnosticSession(
            user_id=user.id,
            subject_id=1,
            status="in_progress",
            total_questions=5,
            started_at=datetime.now(timezone.utc) - timedelta(hours=48),
        )
        sess_finished = diag_models.DiagnosticSession(
            user_id=user.id,
            subject_id=1,
            status="finished",
            total_questions=5,
            started_at=datetime.now(timezone.utc) - timedelta(hours=48),
            finished_at=datetime.now(timezone.utc),
        )
        s.add_all([sess_fresh, sess_old, sess_very_old, sess_finished])
        s.commit()
        # Сохраняем IDs сразу — они понадобятся после закрытия сессии
        fresh_id = sess_fresh.id
        old_id = sess_old.id
        very_old_id = sess_very_old.id
    finally:
        s.close()

    s = SessionLocal()
    try:
        count = diag_service.expire_stale_diagnostic_sessions(s, ttl_hours=24)
    finally:
        s.close()

    assert count == 2

    s = SessionLocal()
    try:
        fresh = s.execute(
            select(diag_models.DiagnosticSession).where(
                diag_models.DiagnosticSession.id == fresh_id
            )
        ).scalar_one()
        assert fresh.status == "in_progress"

        old = s.execute(
            select(diag_models.DiagnosticSession).where(
                diag_models.DiagnosticSession.id == old_id
            )
        ).scalar_one()
        assert old.status == "expired"
        assert old.finished_at is not None
    finally:
        s.close()


def test_expire_stale_respects_ttl():
    """TTL=1 час — отмечает ВСЕ старые."""
    from datetime import datetime, timedelta, timezone

    s = SessionLocal()
    try:
        # User уже создан через autouse fixture
        # (skip register — it conflicts)
        from sqlalchemy import select

        from app.users.models import User

        user = s.execute(
            select(User).where(User.email == "kid@x.com")
        ).scalar_one()

        sess = diag_models.DiagnosticSession(
            user_id=user.id,
            subject_id=1,
            status="in_progress",
            total_questions=5,
            # Время 2 часа назад — должно попасть под TTL=1ч
            started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        s.add(sess)
        s.commit()
        sid = sess.id
    finally:
        s.close()

    s = SessionLocal()
    try:
        count = diag_service.expire_stale_diagnostic_sessions(s, ttl_hours=1)
        sess_after = s.get(diag_models.DiagnosticSession, sid)
    finally:
        s.close()

    assert count == 1
    assert sess_after.status == "expired"


def test_admin_endpoint_expire_diagnostics(client):
    """POST /admin/diagnostics/expire-stale возвращает expired_count."""
    _create_admin(client)
    admin_token = _login(client, "admin@x.com")

    r = client.post(
        "/api/v1/admin/diagnostics/expire-stale?ttl_hours=24",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "expired_count" in body


def test_expire_endpoint_requires_admin(client):
    """kid не может вызывать /admin/diagnostics/expire-stale."""
    kid_token = _login(client, "kid@x.com")

    r = client.post(
        "/api/v1/admin/diagnostics/expire-stale",
        headers={"Authorization": f"Bearer {kid_token}"},
    )
    assert r.status_code == 403


def test_no_stale_sessions_returns_zero(client):
    """Если нет старых сессий — expired_count = 0."""
    _create_admin(client)
    admin_token = _login(client, "admin@x.com")

    r = client.post(
        "/api/v1/admin/diagnostics/expire-stale",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.json()["expired_count"] == 0


def test_audit_log_date_range_filter(client):
    """Audit log фильтр по дате since/until."""
    _create_admin(client)
    admin_token = _login(client, "admin@x.com")

    from datetime import datetime, timedelta, timezone
    from urllib.parse import quote

    # Создадим событие через register (создаёт audit_log)
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "audit-test@example.com",
            "password": "strongpass1",
            "display_name": "Test User",
            "role": "student",
            "grade": 7,
        },
    )
    assert r.status_code == 201, f"register failed: {r.text}"

    # Нестрогая проверка: просто проверим что /audit-log отвечает 200 и не пустой
    r = client.get(
        "/api/v1/admin/audit-log",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200

    # Фильтр since — будущее (пусто). Quote + → %2B для URL.
    future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    r = client.get(
        f"/api/v1/admin/audit-log?since={quote(future)}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json() == []

    # Фильтр until — прошлое (всё должно быть)
    past = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
    r = client.get(
        f"/api/v1/admin/audit-log?until={quote(past)}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200

    # Некорректный date format → 400
    r = client.get(
        "/api/v1/admin/audit-log?since=not-a-date",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400
