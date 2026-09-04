"""Stage 23: parent privacy boundary regression tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timezone

import pytest
from app.auth.security import hash_password
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.progress import models as progress_models
from app.subjects.models import Topic
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users.models import ParentStudentLink, Role, User
from fastapi.testclient import TestClient
from sqlalchemy import select


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        users = [
            User(
                email="parent@example.com",
                password_hash=hash_password("strongpass1"),
                display_name="Parent",
                role=Role.PARENT,
            ),
            User(
                email="student@example.com",
                password_hash=hash_password("strongpass1"),
                display_name="Linked Student",
                role=Role.STUDENT,
            ),
            User(
                email="other-student@example.com",
                password_hash=hash_password("strongpass1"),
                display_name="Other Student",
                role=Role.STUDENT,
            ),
            User(
                email="teacher@example.com",
                password_hash=hash_password("strongpass1"),
                display_name="Teacher",
                role=Role.TEACHER,
            ),
            User(
                email="admin@example.com",
                password_hash=hash_password("strongpass1"),
                display_name="Admin",
                role=Role.ADMIN,
            ),
        ]
        db.add_all(users)
        db.flush()
        parent, linked_student, other_student, *_ = users
        seed_for_tests(db, reset=False)
        topic = db.scalars(select(Topic).order_by(Topic.id)).first()
        assert topic is not None
        db.add(ParentStudentLink(parent_id=parent.id, student_id=linked_student.id, status="active"))
        db.add(
            progress_models.Attempt(
                user_id=linked_student.id,
                topic_id=topic.id,
                question_text="RAW_PRIVATE_QUESTION: сколько будет 2+2?",
                user_answer="RAW_PRIVATE_USER_ANSWER: five",
                correct_answer="RAW_PRIVATE_CORRECT_ANSWER: 4",
                is_correct=False,
                score=0.0,
                feedback="RAW_PRIVATE_AI_FEEDBACK: hidden chat-style feedback",
                created_at=datetime.now(UTC),
            )
        )
        db.add(
            progress_models.Progress(
                user_id=linked_student.id,
                topic_id=topic.id,
                mastery_score=0.4,
                attempts_count=1,
                correct_count=0,
            )
        )
        db.add(
            progress_models.Mistake(
                user_id=linked_student.id,
                topic_id=topic.id,
                mistake_type="conceptual",
                description="Aggregate mistake summary only",
                count=1,
                last_seen=datetime.now(UTC),
            )
        )
        db.add(
            progress_models.Attempt(
                user_id=other_student.id,
                topic_id=topic.id,
                question_text="OTHER_PRIVATE_QUESTION",
                user_answer="OTHER_PRIVATE_USER_ANSWER",
                correct_answer="OTHER_PRIVATE_CORRECT_ANSWER",
                is_correct=True,
                score=1.0,
                created_at=datetime.now(UTC),
            )
        )
        db.commit()
        linked_id = linked_student.id
        other_id = other_student.id

    def _gen():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _gen
    with TestClient(app) as test_client:
        test_client.linked_student_id = linked_id
        test_client.other_student_id = other_id
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _token(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "strongpass1"})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def test_parent_dashboard_is_aggregate_only_and_hides_raw_attempt_content(client):
    parent = _token(client, "parent@example.com")

    response = client.get(
        f"/api/v1/parents/students/{client.linked_student_id}/dashboard",
        headers=_auth(parent),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    text = _json_text(body)
    assert body["privacy_note"]
    assert "чат" in body["privacy_note"].lower()
    assert "total_attempts" in body
    assert "subject_mastery" in body
    assert "weak_topics" in body
    assert "top_mistakes" in body
    for forbidden in [
        "RAW_PRIVATE_QUESTION",
        "RAW_PRIVATE_USER_ANSWER",
        "RAW_PRIVATE_CORRECT_ANSWER",
        "RAW_PRIVATE_AI_FEEDBACK",
        "question_text",
        "user_answer",
        "correct_answer",
        "feedback",
        "history",
        "messages",
        "chat",
    ]:
        assert forbidden not in text


def test_parent_dashboard_pdf_is_aggregate_only(client):
    parent = _token(client, "parent@example.com")

    response = client.get(
        f"/api/v1/parents/students/{client.linked_student_id}/dashboard.pdf",
        headers=_auth(parent),
    )

    assert response.status_code == 200, response.text
    assert "Родитель видит агрегированные метрики" in response.text
    assert "RAW_PRIVATE_QUESTION" not in response.text
    assert "RAW_PRIVATE_CORRECT_ANSWER" not in response.text
    assert "question_text" not in response.text
    assert "correct_answer" not in response.text


def test_parent_cannot_access_unrelated_child_dashboard_or_overview(client):
    parent = _token(client, "parent@example.com")

    for path in [
        f"/api/v1/parents/children/{client.other_student_id}",
        f"/api/v1/parents/students/{client.other_student_id}/dashboard",
        f"/api/v1/parents/students/{client.other_student_id}/dashboard.pdf",
    ]:
        response = client.get(path, headers=_auth(parent))
        assert response.status_code == 404, response.text
        assert "OTHER_PRIVATE" not in response.text


def test_parent_cannot_access_teacher_or_admin_data(client):
    parent = _token(client, "parent@example.com")

    forbidden_paths = [
        "/api/v1/teacher/topics/readiness",
        "/api/v1/teacher/materials",
        "/api/v1/admin/audit-log",
        "/api/v1/admin/realtime/snapshot",
        "/api/v1/admin/users",
    ]
    for path in forbidden_paths:
        response = client.get(path, headers=_auth(parent))
        assert response.status_code == 403, f"{path}: {response.status_code} {response.text}"


def test_parent_children_endpoints_return_only_linked_student(client):
    parent = _token(client, "parent@example.com")

    response = client.get("/api/v1/parents/children", headers=_auth(parent))

    assert response.status_code == 200, response.text
    children = response.json()
    assert [child["student_id"] for child in children] == [client.linked_student_id]
    assert client.other_student_id not in [child["student_id"] for child in children]
