"""Sprint P1 (2026-08-23): /api/v1/feedback endpoint.

Sprint goal: простая форма фидбека для Kirill-pilot. Сохраняет
в audit_log action='user.feedback'. Comment НЕ сохраняется (только длина)
для PII minimization — дети могут написать свободный текст.
"""
from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-feedback-endpoint-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")

import pytest
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.users import service as user_service
from app.users.models import Role
from app.users.schemas import UserCreate
from fastapi.testclient import TestClient


@pytest.fixture()
def client_with_student():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        user_service.register_user(
            db,
            UserCreate(
                email="kirill@example.com",
                password="Kirill2026!",
                display_name="Кирилл",
                role=Role.STUDENT,
                grade=7,
            ),
        )
        user_service.register_user(
            db,
            UserCreate(
                email="parent@example.com",
                password="AI-Tutor-Pilot-2026!Secure",
                display_name="Игорь",
                role=Role.PARENT,
            ),
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


def _login(c: TestClient, email: str, password: str) -> str:
    r = c.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_feedback_student_can_submit(client_with_student):
    """Student может отправить фидбек."""
    c = client_with_student
    token = _login(c, "kirill@example.com", "Kirill2026!")
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post(
        "/api/v1/feedback",
        json={"feeling": "ok", "comment": "Было понятно про дроби", "topic_id": 187},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert isinstance(body["id"], int) and body["id"] > 0


def test_feedback_parent_can_submit(client_with_student):
    """Parent тоже может отправить фидбек."""
    c = client_with_student
    token = _login(c, "parent@example.com", "AI-Tutor-Pilot-2026!Secure")
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post(
        "/api/v1/feedback",
        json={"feeling": "more", "comment": "Хочу больше упражнений", "topic_id": None},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


def test_feedback_unauthenticated_rejected(client_with_student):
    """Без auth → 401."""
    c = client_with_student
    r = c.post("/api/v1/feedback", json={"feeling": "ok", "comment": ""})
    assert r.status_code in (401, 403)


def test_feedback_validates_feeling_field(client_with_student):
    """feeling обязателен (min_length=2)."""
    c = client_with_student
    token = _login(c, "kirill@example.com", "Kirill2026!")
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post(
        "/api/v1/feedback",
        json={"feeling": "x", "comment": ""},
        headers=headers,
    )
    # 422 от Pydantic
    assert r.status_code == 422, r.text


def test_feedback_does_not_persist_comment_to_audit(client_with_student):
    """Comment НЕ должен попадать в audit details (PII)."""
    from app.admin import service as audit_service
    c = client_with_student
    token = _login(c, "kirill@example.com", "Kirill2026!")
    headers = {"Authorization": f"Bearer {token}"}
    secret_comment = "Я ненавижу математику навсегда"
    r = c.post(
        "/api/v1/feedback",
        json={"feeling": "boring", "comment": secret_comment, "topic_id": 188},
        headers=headers,
    )
    assert r.status_code == 200
    feedback_id = r.json()["id"]
    # Проверяем audit log напрямую: comment не должен быть в details
    # (только comment_len).
    with SessionLocal() as db:
        # Ищем запись в audit_log
        from app.admin.models import AuditLog
        from sqlalchemy import select
        rec = db.scalar(select(AuditLog).where(AuditLog.id == feedback_id))
        assert rec is not None, f"audit record {feedback_id} not found"
        import json
        details = rec.details if isinstance(rec.details, dict) else json.loads(rec.details or "{}")
        # comment НЕ должен присутствовать
        assert secret_comment not in str(details)
        # comment_len ДОЛЖЕН присутствовать
        assert details.get("comment_len") == len(secret_comment.strip())
        # feeling — должен быть
        assert details.get("feeling") == "boring"
