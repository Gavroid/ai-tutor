from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta, timezone

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")

import pytest
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.progress import models as progress_models
from app.subjects import models as subject_models
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users import service as user_service
from app.users.models import Role, User
from app.users.schemas import UserCreate
from fastapi.testclient import TestClient
from sqlalchemy import select


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    s = SessionLocal()
    try:
        user_service.register_user(
            s,
            UserCreate(email="teacher@example.com", password="strongpass1", display_name="Учитель", role="teacher"),
            allow_private_bypass=True,
        )
        user_service.register_user(
            s,
            UserCreate(email="admin@example.com", password="strongpass1", display_name="Админ", role="admin"),
            allow_private_bypass=True,
        )
        user_service.register_user(
            s,
            UserCreate(email="kid@example.com", password="strongpass1", display_name="Кирилл", role="student"),
            allow_private_bypass=True,
        )
        seed_for_tests(s, reset=False)
        student = s.scalar(select(User).where(User.email == "kid@example.com"))
        algebra = s.scalar(select(subject_models.Subject).where(subject_models.Subject.code == "algebra"))
        math = s.scalar(select(subject_models.Subject).where(subject_models.Subject.code == "math"))
        algebra_topics = [topic for section in algebra.sections for topic in section.topics]
        math_topics = [topic for section in math.sections for topic in section.topics]
        now = datetime.now(UTC)
        rows = [
            (algebra_topics[0].id, 0.25, 4, 1, now - timedelta(days=1)),
            (algebra_topics[1].id, 0.75, 4, 3, now - timedelta(days=2)),
            (math_topics[0].id, 0.50, 2, 1, now - timedelta(days=3)),
        ]
        for topic_id, mastery, attempts, correct, updated_at in rows:
            s.add(
                progress_models.Progress(
                    user_id=student.id,
                    topic_id=topic_id,
                    mastery_score=mastery,
                    attempts_count=attempts,
                    correct_count=correct,
                    updated_at=updated_at,
                )
            )
        s.commit()
    finally:
        s.close()

    def _gen():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _gen
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _token(c: TestClient, email: str) -> str:
    r = c.post("/api/v1/auth/login", json={"email": email, "password": "strongpass1"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_learning_analytics_requires_teacher_or_admin(client):
    student_token = _token(client, "kid@example.com")
    r = client.get("/api/v1/analytics/learning", headers={"Authorization": f"Bearer {student_token}"})
    assert r.status_code == 403


def test_learning_analytics_aggregates_subjects_topics_and_recent_activity(client):
    teacher_token = _token(client, "teacher@example.com")
    r = client.get("/api/v1/analytics/learning", headers={"Authorization": f"Bearer {teacher_token}"})

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["totals"]["attempts"] == 10
    assert body["totals"]["correct"] == 5
    assert body["totals"]["accuracy"] == 0.5
    assert body["totals"]["active_topics"] == 3
    assert body["totals"]["weak_topics"] == 1
    algebra = next(row for row in body["subjects"] if row["subject_code"] == "algebra")
    assert algebra["attempts"] == 8
    assert algebra["correct"] == 4
    assert algebra["accuracy"] == 0.5
    assert algebra["average_mastery"] == 0.5
    assert algebra["weak_topics"] == 1
    assert body["weak_topics"][0]["subject_code"] == "algebra"
    assert body["weak_topics"][0]["mastery_score"] == 0.25
    assert len(body["recent_activity"]) == 3
