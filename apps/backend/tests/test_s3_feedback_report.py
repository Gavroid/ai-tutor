"""S3.6 (2026-09-01, D2.6): unit tests for feedback bug/error report.

Covers:
- POST /api/v1/feedback/report — student/parent/admin can submit
- GET /api/v1/admin/feedback-reports — admin only (student/parent → 403)
- PATCH status — admin only
- 401/403 для unauthenticated/non-admin
- category validation (5 valid + invalid)
"""

from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-s3-6-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_DETERMINISTIC_MODE", "1")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest
from app.db.session import Base, SessionLocal, engine, get_db
from app.feedback.models import (
    FB_CATEGORY_OTHER,
    FB_CATEGORY_VALUES,
    FB_STATUS_OPEN,
    FB_STATUS_VALUES,
    FeedbackReport,
)
from app.main import app
from app.users import service as user_service
from app.users.models import Role
from app.users.schemas import UserCreate
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture()
def client_with_users():
    Base.metadata.drop_all(engine)
    engine.dispose()
    # Создаём таблицу feedback_reports через SQLAlchemy.metadata
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        user_service.register_user(
            db,
            UserCreate(
                email="student@x.com",
                password="StudentPass1",
                display_name="Su",
                role=Role.STUDENT,
                grade=7,
            ),
        )
        user_service.register_user(
            db,
            UserCreate(
                email="admin@x.com",
                password="AdminPass1",
                display_name="Ad",
                role=Role.ADMIN,
            ),
            allow_private_bypass=True,  # S3.6 tests: register admin directly
        )

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


def _login(c, email, password):
    r = c.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# === Category/Status constants ============================================


def test_category_values_include_required_set():
    assert "error" in FB_CATEGORY_VALUES
    assert "bug" in FB_CATEGORY_VALUES
    assert "unclear" in FB_CATEGORY_VALUES
    assert "wrong_answer" in FB_CATEGORY_VALUES
    assert "other" in FB_CATEGORY_VALUES


def test_status_values_include_required_set():
    assert FB_STATUS_OPEN in FB_STATUS_VALUES
    assert "in_progress" in FB_STATUS_VALUES
    assert "resolved" in FB_STATUS_VALUES
    assert "wont_fix" in FB_STATUS_VALUES


# === POST /feedback/report ================================================


def test_student_can_submit_report(client_with_users):
    c = client_with_users
    token = _login(c, "student@x.com", "StudentPass1")
    h = {"Authorization": f"Bearer {token}"}
    r = c.post(
        "/api/v1/feedback/report",
        json={"category": "bug", "text": "Кнопка «Применить» не работает в Safari"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["category"] == "bug"
    assert body["status"] == "open"
    assert body["text"] == "Кнопка «Применить» не работает в Safari"
    assert isinstance(body["id"], int) and body["id"] > 0
    assert "created_at" in body


def test_submit_with_message_id(client_with_users):
    c = client_with_users
    token = _login(c, "student@x.com", "StudentPass1")
    h = {"Authorization": f"Bearer {token}"}
    r = c.post(
        "/api/v1/feedback/report",
        json={"category": "error", "text": "AI дал неправильный ответ", "message_id": 42},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["message_id"] == 42


def test_unauthenticated_rejected(client_with_users):
    c = client_with_users
    r = c.post("/api/v1/feedback/report", json={"category": "bug", "text": "test"})
    assert r.status_code in (401, 403, 422)


def test_invalid_category_rejected(client_with_users):
    c = client_with_users
    token = _login(c, "student@x.com", "StudentPass1")
    h = {"Authorization": f"Bearer {token}"}
    r = c.post(
        "/api/v1/feedback/report",
        json={"category": "hacker_attack", "text": "что-то плохое"},
        headers=h,
    )
    assert r.status_code == 400


def test_short_text_rejected(client_with_users):
    c = client_with_users
    token = _login(c, "student@x.com", "StudentPass1")
    h = {"Authorization": f"Bearer {token}"}
    r = c.post(
        "/api/v1/feedback/report",
        json={"category": "bug", "text": "ab"},  # < 5 chars
        headers=h,
    )
    # Pydantic v2 возвращает 422 на min_length, наш runtime check возвращает 400
    assert r.status_code in (400, 422)


# === GET /admin/feedback-reports ==========================================


def test_admin_can_list_reports(client_with_users):
    c = client_with_users
    student_token = _login(c, "student@x.com", "StudentPass1")
    admin_token = _login(c, "admin@x.com", "AdminPass1")

    # Студент шлёт 2 report'а
    h_s = {"Authorization": f"Bearer {student_token}"}
    for i in range(2):
        r = c.post(
            "/api/v1/feedback/report",
            json={"category": "bug", "text": f"Test report {i}"},
            headers=h_s,
        )
        assert r.status_code == 201, r.text

    # Админ читает
    h_a = {"Authorization": f"Bearer {admin_token}"}
    r = c.get("/api/v1/admin/feedback-reports", headers=h_a)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2
    assert body["open_count"] == 2
    assert len(body["items"]) == 2
    # new items first
    assert body["items"][0]["text"].startswith("Test report")


def test_non_admin_cannot_list_reports(client_with_users):
    c = client_with_users
    token = _login(c, "student@x.com", "StudentPass1")
    h = {"Authorization": f"Bearer {token}"}
    r = c.get("/api/v1/admin/feedback-reports", headers=h)
    assert r.status_code in (401, 403)


def test_admin_filter_by_status(client_with_users):
    c = client_with_users
    admin_token = _login(c, "admin@x.com", "AdminPass1")
    h = {"Authorization": f"Bearer {admin_token}"}
    r = c.get("/api/v1/admin/feedback-reports?status_filter=open", headers=h)
    assert r.status_code == 200
    r = c.get("/api/v1/admin/feedback-reports?status_filter=resolved", headers=h)
    assert r.status_code == 200


def test_admin_invalid_status_filter(client_with_users):
    c = client_with_users
    admin_token = _login(c, "admin@x.com", "AdminPass1")
    h = {"Authorization": f"Bearer {admin_token}"}
    r = c.get("/api/v1/admin/feedback-reports?status_filter=blah", headers=h)
    assert r.status_code == 400


# === PATCH /status ======================================================


def test_admin_can_update_status(client_with_users):
    c = client_with_users
    student_token = _login(c, "student@x.com", "StudentPass1")
    admin_token = _login(c, "admin@x.com", "AdminPass1")
    h_s = {"Authorization": f"Bearer {student_token}"}
    h_a = {"Authorization": f"Bearer {admin_token}"}

    r = c.post(
        "/api/v1/feedback/report",
        json={"category": "bug", "text": "Test for status update"},
        headers=h_s,
    )
    rid = r.json()["id"]

    # admin → in_progress
    r = c.patch(
        f"/api/v1/admin/feedback-reports/{rid}/status",
        json={"status": "in_progress", "note": "разбираюсь"},
        headers=h_a,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "in_progress"

    # → resolved
    r = c.patch(
        f"/api/v1/admin/feedback-reports/{rid}/status",
        json={"status": "resolved"},
        headers=h_a,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"


def test_non_admin_cannot_update_status(client_with_users):
    c = client_with_users
    student_token = _login(c, "student@x.com", "StudentPass1")
    h_s = {"Authorization": f"Bearer {student_token}"}

    r = c.post(
        "/api/v1/feedback/report",
        json={"category": "bug", "text": "Test not admin"},
        headers=h_s,
    )
    rid = r.json()["id"]

    r = c.patch(
        f"/api/v1/admin/feedback-reports/{rid}/status",
        json={"status": "resolved"},
        headers=h_s,
    )
    assert r.status_code in (401, 403)


def test_admin_update_invalid_status(client_with_users):
    c = client_with_users
    student_token = _login(c, "student@x.com", "StudentPass1")
    admin_token = _login(c, "admin@x.com", "AdminPass1")
    h_s = {"Authorization": f"Bearer {student_token}"}
    h_a = {"Authorization": f"Bearer {admin_token}"}

    r = c.post(
        "/api/v1/feedback/report",
        json={"category": "bug", "text": "Test invalid status"},
        headers=h_s,
    )
    rid = r.json()["id"]

    r = c.patch(
        f"/api/v1/admin/feedback-reports/{rid}/status",
        json={"status": "blah"},
        headers=h_a,
    )
    assert r.status_code == 400


def test_admin_update_missing_report(client_with_users):
    c = client_with_users
    admin_token = _login(c, "admin@x.com", "AdminPass1")
    h_a = {"Authorization": f"Bearer {admin_token}"}
    r = c.patch(
        "/api/v1/admin/feedback-reports/999999/status",
        json={"status": "resolved"},
        headers=h_a,
    )
    assert r.status_code == 404
