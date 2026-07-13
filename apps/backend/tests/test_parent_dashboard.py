"""Sprint 3 — тесты родительского дашборда."""
from __future__ import annotations

import os

os.environ["APP_SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["AI_API_KEY"] = "mock-key-for-tests"

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

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
        # mom + kid
        user_service.register_user(
            s,
            UserCreate(
                email="mom@example.com",
                password="strongpass1",
                display_name="Мама",
                role="parent",
            ),
        )
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
        # student2 — для теста RBAC (не привязан к mom)
        user_service.register_user(
            s,
            UserCreate(
                email="other_kid@example.com",
                password="strongpass1",
                display_name="Другой",
                role="student",
                grade=7,
            ),
        )

        from app.subjects.scripts_seed_runner import seed_for_tests

        seed_for_tests(s, reset=False)
    finally:
        s.close()

    # Линкуем mom + kid
    s = SessionLocal()
    try:
        from app.users.models import User
        from app.parents import service as parents_service

        mom = s.scalar(__import__("sqlalchemy").select(User).where(User.email == "mom@example.com"))
        kid = s.scalar(__import__("sqlalchemy").select(User).where(User.email == "kid@example.com"))
        code = parents_service.create_invite_for_parent(s, mom)
        parents_service.accept_invite(s, kid, code)
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


def _token(c: TestClient, email: str) -> str:
    r = c.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "strongpass1"},
    )
    assert r.status_code == 200
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _get_kid_id(c: TestClient) -> int:
    """Реальный ID кида (autoincrement)."""
    from app.db.session import SessionLocal
    from app.users.models import User

    s = SessionLocal()
    try:
        kid = s.scalar(
            __import__("sqlalchemy").select(User).where(User.email == "kid@example.com")
        )
        return kid.id
    finally:
        s.close()


# ============================================================
# Auth / RBAC
# ============================================================


def test_dashboard_requires_auth(client):
    r = client.get("/api/v1/parents/students/1/dashboard")
    assert r.status_code == 401


def test_dashboard_blocks_student(client):
    kid = _token(client, "kid@example.com")
    r = client.get("/api/v1/parents/students/1/dashboard", headers=_h(kid))
    assert r.status_code == 403


def test_dashboard_blocks_teacher(client):
    # Создаём teacher
    s = SessionLocal()
    try:
        user_service.register_user(
            s,
            UserCreate(
                email="teacher@example.com",
                password="strongpass1",
                display_name="Учитель",
                role="teacher",
            ),
            allow_private_bypass=True,
        )
    finally:
        s.close()

    teacher = _token(client, "teacher@example.com")
    r = client.get("/api/v1/parents/students/1/dashboard", headers=_h(teacher))
    assert r.status_code == 403


def test_dashboard_404_for_unlinked_student(client):
    """Mom не привязана к other_kid → 404."""
    mom = _token(client, "mom@example.com")

    from app.db.session import SessionLocal
    from app.users.models import User

    s = SessionLocal()
    try:
        other = s.scalar(
            __import__("sqlalchemy").select(User).where(
                User.email == "other_kid@example.com"
            )
        )
        other_id = other.id
    finally:
        s.close()

    r = client.get(
        f"/api/v1/parents/students/{other_id}/dashboard",
        headers=_h(mom),
    )
    assert r.status_code == 404


# ============================================================
# Empty dashboard
# ============================================================


def test_dashboard_empty_for_new_student(client):
    """У нового кида нет ни attempts, ни progress — дашборд пустой, но 200."""
    kid_id = _get_kid_id(client)
    mom = _token(client, "mom@example.com")
    r = client.get(
        f"/api/v1/parents/students/{kid_id}/dashboard",
        headers=_h(mom),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_attempts"] == 0
    assert body["correct_attempts"] == 0
    assert body["accuracy"] == 0
    assert body["average_mastery"] == 0
    assert body["due_for_review_count"] == 0
    assert body["weak_topics"] == []
    assert body["top_mistakes"] == []
    # Subject mastery содержит все активные предметы (даже если без попыток)
    assert isinstance(body["subject_mastery"], list)
    assert len(body["subject_mastery"]) > 0
    # Streak пустой
    assert body["streak"]["current_streak_days"] == 0
    assert body["streak"]["total_active_days"] == 0
    # Privacy note
    assert "приватность" in body["privacy_note"].lower() or "приват" in body["privacy_note"].lower()


def test_dashboard_daily_activity_30_entries(client):
    """daily_activity_30d всегда содержит ровно 30 записей."""
    kid_id = _get_kid_id(client)
    mom = _token(client, "mom@example.com")
    r = client.get(
        f"/api/v1/parents/students/{kid_id}/dashboard",
        headers=_h(mom),
    )
    body = r.json()
    assert len(body["daily_activity_30d"]) == 30


# ============================================================
# Dashboard with data
# ============================================================


def test_dashboard_with_attempts(client):
    """С attempts — все поля заполняются."""
    kid_id = _get_kid_id(client)
    kid = _token(client, "kid@example.com")

    # Записываем несколько attempts через API
    for i in range(5):
        client.post(
            "/api/v1/progress/attempts",
            json={
                "topic_id": 1,
                "question_text": f"q{i}",
                "user_answer": "a",
                "correct_answer": "a",
                "is_correct": i % 2 == 0,
                "score": 1.0 if i % 2 == 0 else 0.0,
                "feedback": "ok" if i % 2 == 0 else "wrong",
            },
            headers=_h(kid),
        )

    mom = _token(client, "mom@example.com")
    r = client.get(
        f"/api/v1/parents/students/{kid_id}/dashboard",
        headers=_h(mom),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_attempts"] == 5
    assert body["correct_attempts"] >= 3  # i=0,2,4 → correct
    assert body["accuracy"] > 0
    assert body["average_mastery"] > 0
    # Time stats — попытки попали в сегодня
    assert body["time_stats"]["last_7_days"] >= 5
    assert body["time_stats"]["total_attempts"] == 5


def test_dashboard_streak_calculation(client):
    """Сегодняшние attempts → current_streak = 1."""
    kid_id = _get_kid_id(client)
    kid = _token(client, "kid@example.com")

    client.post(
        "/api/v1/progress/attempts",
        json={
            "topic_id": 1,
            "question_text": "q",
            "user_answer": "a",
            "correct_answer": "a",
            "is_correct": True,
            "score": 1.0,
        },
        headers=_h(kid),
    )

    mom = _token(client, "mom@example.com")
    r = client.get(
        f"/api/v1/parents/students/{kid_id}/dashboard",
        headers=_h(mom),
    )
    body = r.json()
    assert body["streak"]["current_streak_days"] == 1
    assert body["streak"]["longest_streak_days"] == 1
    assert body["streak"]["total_active_days"] == 1
    assert body["streak"]["last_active_date"] is not None


def test_dashboard_subject_mastery(client):
    """subject_mastery содержит хотя бы один предмет с правильными полями."""
    kid_id = _get_kid_id(client)
    kid = _token(client, "kid@example.com")

    client.post(
        "/api/v1/progress/attempts",
        json={
            "topic_id": 1,
            "question_text": "q",
            "user_answer": "a",
            "correct_answer": "a",
            "is_correct": True,
            "score": 1.0,
        },
        headers=_h(kid),
    )

    mom = _token(client, "mom@example.com")
    r = client.get(
        f"/api/v1/parents/students/{kid_id}/dashboard",
        headers=_h(mom),
    )
    body = r.json()
    sm = body["subject_mastery"]
    assert len(sm) > 0
    s0 = sm[0]
    assert "subject_name" in s0
    assert "topics_total" in s0
    assert "topics_attempted" in s0
    assert "avg_mastery" in s0
    assert "accuracy" in s0


def test_dashboard_due_for_review_count(client):
    """due_for_review_count = кол-во тем с next_review_at <= now."""
    kid_id = _get_kid_id(client)
    kid = _token(client, "kid@example.com")

    # Создаём attempt + review (SM-2 ставит next_review_at = завтра)
    client.post(
        "/api/v1/progress/attempts",
        json={
            "topic_id": 1,
            "question_text": "q",
            "user_answer": "a",
            "correct_answer": "a",
            "is_correct": True,
            "score": 1.0,
        },
        headers=_h(kid),
    )
    client.post(
        "/api/v1/progress/review-result",
        json={"topic_id": 1, "quality": 5, "is_correct": True},
        headers=_h(kid),
    )

    # Сдвигаем в прошлое
    from sqlalchemy import update

    from app.db.session import engine
    from app.progress.models import Progress

    past = datetime.now(timezone.utc) - timedelta(days=1)
    with engine.begin() as conn:
        conn.execute(
            update(Progress)
            .where(Progress.user_id == kid_id)
            .values(next_review_at=past)
        )

    mom = _token(client, "mom@example.com")
    r = client.get(
        f"/api/v1/parents/students/{kid_id}/dashboard",
        headers=_h(mom),
    )
    body = r.json()
    assert body["due_for_review_count"] >= 1


# ============================================================
# HTML export
# ============================================================


def test_dashboard_pdf_export_returns_html(client):
    kid_id = _get_kid_id(client)
    mom = _token(client, "mom@example.com")
    r = client.get(
        f"/api/v1/parents/students/{kid_id}/dashboard.pdf",
        headers=_h(mom),
    )
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    body = r.text
    assert "Кирилл" in body
    assert "приватность" in body.lower()
    assert "<table" in body


def test_dashboard_pdf_export_requires_auth(client):
    r = client.get("/api/v1/parents/students/1/dashboard.pdf")
    assert r.status_code == 401


def test_dashboard_pdf_export_404_for_unlinked(client):
    """Mom не привязана к other_kid → 404."""
    from app.db.session import SessionLocal
    from app.users.models import User

    s = SessionLocal()
    try:
        other = s.scalar(
            __import__("sqlalchemy").select(User).where(
                User.email == "other_kid@example.com"
            )
        )
        other_id = other.id
    finally:
        s.close()

    mom = _token(client, "mom@example.com")
    r = client.get(
        f"/api/v1/parents/students/{other_id}/dashboard.pdf",
        headers=_h(mom),
    )
    assert r.status_code == 404
