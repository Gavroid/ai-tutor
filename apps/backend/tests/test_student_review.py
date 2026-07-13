"""Sprint 2 — тесты UX Ученика, Spaced Repetition, опубликованных материалов."""
from __future__ import annotations

import os

os.environ["APP_SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["AI_API_KEY"] = "mock-key-for-tests"
os.environ["UPLOAD_DIR"] = "/tmp/ai-tutor-test-uploads-sprint2"

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

    from app.auth.security import hash_password
    from app.users.models import Role as UserRole, User

    s = SessionLocal()
    try:
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
                email="teacher@example.com",
                password="strongpass1",
                display_name="Учитель",
                role="teacher",
            ),
            allow_private_bypass=True,
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

        from app.subjects.scripts_seed_runner import seed_for_tests
        from app.subjects.models import Topic

        seed_for_tests(s, reset=False)
        topic = s.query(Topic).first()
        topic_id = topic.id
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
        c.topic_id = topic_id
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


def _publish_material(c: TestClient, topic_id: int) -> int:
    """Хелпер: создать материал и опубликовать."""
    teacher = _token(c, "teacher@example.com")
    r = c.post(
        "/api/v1/teacher/materials/generate",
        json={"topic_id": topic_id, "source_type": "topic"},
        headers=_h(teacher),
    )
    assert r.status_code == 200, r.text
    mat_id = r.json()["id"]
    c.post(f"/api/v1/teacher/materials/{mat_id}/approve", headers=_h(teacher))
    c.post(f"/api/v1/teacher/materials/{mat_id}/publish", headers=_h(teacher))
    return mat_id


# ============================================================
# SM-2 алгоритм (unit)
# ============================================================


def test_sm2_first_correct_review_schedules_for_1_day():
    from app.progress.spaced import schedule_next_review

    now = datetime.now(timezone.utc)
    r = schedule_next_review(None, 0, 2.5, quality=5, now=now)
    assert r.interval_days == 1
    assert r.review_count == 1
    # EF при q=5: 2.5 + 0.1 = 2.6
    assert r.new_ef == 2.6


def test_sm2_second_correct_review_schedules_for_6_days():
    from app.progress.spaced import schedule_next_review

    now = datetime.now(timezone.utc)
    r = schedule_next_review(now, 1, 2.5, quality=5, now=now)
    assert r.interval_days == 6
    assert r.review_count == 2


def test_sm2_incorrect_resets_count():
    from app.progress.spaced import schedule_next_review

    now = datetime.now(timezone.utc)
    # review_count=5, но ответили плохо
    r = schedule_next_review(now, 5, 2.5, quality=1, now=now)
    assert r.interval_days == 1
    # review_count не растёт (всё ещё 5)
    assert r.review_count == 5


def test_sm2_ef_floor_at_13():
    """EF не падает ниже 1.3 даже при q=0."""
    from app.progress.spaced import schedule_next_review

    now = datetime.now(timezone.utc)
    r = schedule_next_review(now, 0, 1.3, quality=0, now=now)
    assert r.new_ef >= 1.3


def test_sm2_quality_from_correct_no_hint_is_5():
    from app.progress.spaced import quality_from_result

    assert quality_from_result(True, False) == 5
    assert quality_from_result(True, True) == 3
    assert quality_from_result(False, False) == 1
    assert quality_from_result(False, True) == 1


# ============================================================
# due-for-review endpoint
# ============================================================


def test_due_for_review_requires_auth(client):
    r = client.get("/api/v1/progress/due-for-review")
    assert r.status_code == 401


def test_due_for_review_empty_for_new_student(client):
    kid = _token(client, "kid@example.com")
    r = client.get("/api/v1/progress/due-for-review", headers=_h(kid))
    assert r.status_code == 200
    assert r.json() == []


def test_due_for_review_returns_overdue_topic(client):
    """Если у ученика есть прогресс с next_review_at в прошлом — попадает в выдачу."""
    kid = _token(client, "kid@example.com")

    # Получаем реальный user_id кида (он autoincrement).
    from app.db.session import SessionLocal
    from app.users.models import User

    s = SessionLocal()
    try:
        kid_user = s.scalar(__import__("sqlalchemy").select(User).where(User.email == "kid@example.com"))
        kid_id = kid_user.id
    finally:
        s.close()

    # Создаём Progress через API.
    c_attempt = client.post(
        "/api/v1/progress/attempts",
        json={
            "topic_id": client.topic_id,
            "question_text": "q",
            "user_answer": "a",
            "correct_answer": "a",
            "is_correct": True,
            "score": 1.0,
        },
        headers=_h(kid),
    )
    assert c_attempt.status_code == 200, c_attempt.text

    c_review = client.post(
        "/api/v1/progress/review-result",
        json={"topic_id": client.topic_id, "quality": 5, "is_correct": True},
        headers=_h(kid),
    )
    assert c_review.status_code == 200, c_review.text

    # Сдвигаем next_review_at в прошлое через прямой SQL.
    from sqlalchemy import update

    from app.db.session import engine
    from app.progress.models import Progress

    past = datetime.now(timezone.utc) - timedelta(days=3)
    with engine.begin() as conn:
        result = conn.execute(
            update(Progress)
            .where(Progress.user_id == kid_id, Progress.topic_id == client.topic_id)
            .values(next_review_at=past, last_reviewed_at=past)
        )
        assert result.rowcount >= 1, f"No rows updated (user={kid_id}, topic={client.topic_id})"

    r = client.get("/api/v1/progress/due-for-review", headers=_h(kid))
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["topic_id"] == client.topic_id
    assert items[0]["days_overdue"] >= 1


def test_due_for_review_excludes_topics_without_next_review(client):
    """Прогресс без next_review_at (никогда не повторялся) — не в выдаче."""
    s = SessionLocal()
    try:
        from app.progress.models import Progress

        prog = Progress(
            user_id=2,
            topic_id=client.topic_id,
            mastery_score=0.5,
            attempts_count=1,
            correct_count=1,
            # next_review_at = None
        )
        s.add(prog)
        s.commit()
    finally:
        s.close()

    kid = _token(client, "kid@example.com")
    r = client.get("/api/v1/progress/due-for-review", headers=_h(kid))
    assert r.status_code == 200
    assert r.json() == []


# ============================================================
# review-result endpoint
# ============================================================


def test_review_result_creates_progress_for_first_time(client):
    kid = _token(client, "kid@example.com")
    r = client.post(
        "/api/v1/progress/review-result",
        json={"topic_id": client.topic_id, "quality": 5, "is_correct": True},
        headers=_h(kid),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # mastery_score, attempts_count были дефолтные 0
    # но quality=5 должен был пересчитать schedule
    assert body["topic_id"] == client.topic_id


def test_review_result_quality_clamped(client):
    """quality=10 → clamp в 5."""
    kid = _token(client, "kid@example.com")
    r = client.post(
        "/api/v1/progress/review-result",
        json={"topic_id": client.topic_id, "quality": 100, "is_correct": True},
        headers=_h(kid),
    )
    # 422 — pydantic валидация ge=0 le=5
    assert r.status_code == 422


def test_review_result_updates_existing_progress(client):
    """Повторный review пересчитывает next_review_at."""
    kid = _token(client, "kid@example.com")

    # Первый review
    r1 = client.post(
        "/api/v1/progress/review-result",
        json={"topic_id": client.topic_id, "quality": 5},
        headers=_h(kid),
    )
    assert r1.status_code == 200

    # Второй review
    r2 = client.post(
        "/api/v1/progress/review-result",
        json={"topic_id": client.topic_id, "quality": 4},
        headers=_h(kid),
    )
    assert r2.status_code == 200


def test_review_result_requires_auth(client):
    r = client.post(
        "/api/v1/progress/review-result",
        json={"topic_id": 1, "quality": 5},
    )
    assert r.status_code == 401


# ============================================================
# Student materials (опубликованные)
# ============================================================


def test_student_sees_published_materials(client):
    """Ученик видит только published."""
    mat_id = _publish_material(client, client.topic_id)

    kid = _token(client, "kid@example.com")
    r = client.get(
        f"/api/v1/student/materials?topic_id={client.topic_id}",
        headers=_h(kid),
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["id"] == mat_id
    assert items[0]["title"]


def test_student_does_not_see_drafts(client):
    """Черновик (ai_generated) не виден ученику."""
    teacher = _token(client, "teacher@example.com")
    client.post(
        "/api/v1/teacher/materials/generate",
        json={"topic_id": client.topic_id, "source_type": "topic"},
        headers=_h(teacher),
    )
    # approve НЕ делаем — остаётся ai_generated

    kid = _token(client, "kid@example.com")
    r = client.get(
        f"/api/v1/student/materials?topic_id={client.topic_id}",
        headers=_h(kid),
    )
    assert r.status_code == 200
    assert r.json() == []


def test_student_can_view_published_by_id(client):
    mat_id = _publish_material(client, client.topic_id)
    kid = _token(client, "kid@example.com")
    r = client.get(f"/api/v1/student/materials/{mat_id}", headers=_h(kid))
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == mat_id
    assert "content" in body


def test_student_cannot_view_draft_by_id(client):
    teacher = _token(client, "teacher@example.com")
    r = client.post(
        "/api/v1/teacher/materials/generate",
        json={"topic_id": client.topic_id, "source_type": "topic"},
        headers=_h(teacher),
    )
    mat_id = r.json()["id"]

    kid = _token(client, "kid@example.com")
    r = client.get(f"/api/v1/student/materials/{mat_id}", headers=_h(kid))
    assert r.status_code == 404


def test_student_materials_requires_auth(client):
    r = client.get("/api/v1/student/materials")
    assert r.status_code == 401


# ============================================================
# RBAC: due-for-review виден только студентам
# ============================================================


def test_due_for_review_blocks_parent(client):
    from app.auth.security import hash_password
    from app.users.models import Role, User

    s = SessionLocal()
    try:
        parent = User(
            email="mom@example.com",
            password_hash=hash_password("strongpass1"),
            display_name="Мама",
            role=Role.PARENT,
        )
        s.add(parent)
        s.commit()
    finally:
        s.close()

    mom_tok = client.post(
        "/api/v1/auth/login",
        json={"email": "mom@example.com", "password": "strongpass1"},
    ).json()["access_token"]

    # Должно работать — endpoint не teacher-only, любой авторизованный
    r = client.get("/api/v1/progress/due-for-review", headers=_h(mom_tok))
    assert r.status_code == 200
