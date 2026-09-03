"""Sprint 3.15: честные счётчики easy_solved / questions_to_ai.

Раньше (pre-3.15) `collect_stats()` использовал proxy `easy_solved = total`,
`questions_to_ai = total` — бейджи `all_basics` и `asked_question` выдавались
нечестно. Этот модуль фиксирует:

- (1) после v2 answer с difficulty≤2 и is_correct=True → easy_solved == 1
- (2) difficulty=5 (выше базового) → easy_solved == 0
- (3) POST /api/v1/ai/chat → questions_to_ai == 1
- (4) неверный ответ (is_correct=False) не инкрементит easy_solved

Реализация: новая таблица `user_counters` (миграция 0025), инкременты в
v2/exercises.py (после создания Attempt при easy difficulty) и
ai/router.py (после успешного chat).
"""
from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.student.badges import collect_stats
from app.student.models import UserCounter
from app.subjects import models as subj_models
from app.subjects.curriculum_7_class import CURRICULUM_7_CLASS
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def client():
    """TestClient + student + seeded curriculum + admin."""
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    s = SessionLocal()
    try:
        user_service.register_user(
            s,
            UserCreate(
                email="counters-student@example.com",
                password="strongpass1",
                display_name="Counter Student",
                role="student",
                grade=7,
            ),
        )
        # Raise hourly limit for repeated v2 calls в этом тесте.
        from app.ai import budget as _budget_mod

        _budget_mod.reload_limits(
            daily_requests=10_000,
            daily_tokens=_budget_mod.DAILY_TOKENS_LIMIT,
            hourly_requests=1_000,
        )
        _budget_mod.reset_budget_state()
        seed_for_tests(s, reset=False)
    finally:
        s.close()

    def _gen():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _gen
    try:
        with TestClient(app) as c:
            yield c
    finally:
        from app.ai import budget as _budget_teardown

        _budget_teardown.reload_limits(
            daily_requests=200,
            daily_tokens=200_000,
            hourly_requests=20,
        )
        _budget_teardown.reset_budget_state()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)


def _login(c: TestClient) -> str:
    r = c.post(
        "/api/v1/auth/login",
        json={"email": "counters-student@example.com", "password": "strongpass1"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _algebra_topic_id(s=None) -> int:
    s = s or SessionLocal()
    try:
        subj = s.scalar(
            select(subj_models.Subject).where(subj_models.Subject.code == "algebra")
        )
        assert subj is not None
        sec = s.scalar(
            select(subj_models.Section).where(subj_models.Section.subject_id == subj.id)
        )
        assert sec is not None
        topic = s.scalar(
            select(subj_models.Topic).where(subj_models.Topic.section_id == sec.id)
        )
        assert topic is not None
        return topic.id
    finally:
        if s is not None:
            s.close()


def _gen_correct_pair(client: TestClient, h: dict, topic_id: int, difficulty: int) -> tuple[int, str]:
    """Generate упражнение + возврат (exercise_id, correct_answer) для ТОГО ЖЕ."""
    from app.ai.models import GeneratedExerciseInstance

    gen = client.post(
        "/api/v2/exercises/generate",
        headers=h,
        json={"topic_id": topic_id, "difficulty": difficulty},
    ).json()
    with SessionLocal() as s:
        inst = s.get(GeneratedExerciseInstance, gen["exercise_id"])
        return gen["exercise_id"], inst.correct_answer


def test_easy_solved_increments_on_correct_easy_answer(client):
    """(1) difficulty=2 + correct → easy_solved == 1."""
    token = _login(client)
    h = {"Authorization": f"Bearer {token}"}
    tid = _algebra_topic_id()

    ex_id, correct = _gen_correct_pair(client, h, tid, difficulty=2)
    r = client.post(
        f"/api/v2/exercises/{ex_id}/answer",
        headers=h,
        json={"user_answer": correct},
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_correct"] is True

    with SessionLocal() as s:
        stats = collect_stats(s, _student_id_from_token(token))
        assert stats["easy_solved"] == 1, stats


def test_easy_solved_does_not_increment_on_hard_difficulty(client):
    """(2) difficulty=5 (выше базового 2) → easy_solved остаётся 0."""
    token = _login(client)
    h = {"Authorization": f"Bearer {token}"}
    tid = _algebra_topic_id()

    ex_id, correct = _gen_correct_pair(client, h, tid, difficulty=5)
    r = client.post(
        f"/api/v2/exercises/{ex_id}/answer",
        headers=h,
        json={"user_answer": correct},
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_correct"] is True

    with SessionLocal() as s:
        stats = collect_stats(s, _student_id_from_token(token))
        assert stats["easy_solved"] == 0, stats


def test_questions_to_ai_increments_on_chat(client):
    """(3) POST /api/v1/ai/chat → questions_to_ai == 1."""
    from app.ai import service as _service
    from app.ai.mock import MockProvider

    _service._provider_instance = MockProvider(model_name="mock-1")
    token = _login(client)
    h = {"Authorization": f"Bearer {token}"}
    tid = _algebra_topic_id()

    r = client.post(
        "/api/v1/ai/chat",
        headers=h,
        json={
            "history": [{"role": "user", "content": "Привет!"}],
            "topic_id": tid,
        },
    )
    assert r.status_code == 200, r.text

    with SessionLocal() as s:
        stats = collect_stats(s, _student_id_from_token(token))
        assert stats["questions_to_ai"] == 1, stats


def test_easy_solved_does_not_increment_on_wrong_answer(client):
    """(4) Неверный ответ → easy_solved не инкрементится (идемпотентность)."""
    token = _login(client)
    h = {"Authorization": f"Bearer {token}"}
    tid = _algebra_topic_id()

    ex_id, _correct = _gen_correct_pair(client, h, tid, difficulty=2)
    r = client.post(
        f"/api/v2/exercises/{ex_id}/answer",
        headers=h,
        json={"user_answer": "intentionally wrong"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_correct"] is False

    with SessionLocal() as s:
        stats = collect_stats(s, _student_id_from_token(token))
        assert stats["easy_solved"] == 0, stats


# === helpers ===

from sqlalchemy import select  # noqa: E402


def _student_id_from_token(token: str) -> int:
    """Декодируем JWT чтобы найти student.id (тестовая утилита)."""
    import base64
    import json as json_mod

    payload_b64 = token.split(".")[1]
    # JWT использует url-safe base64 без padding.
    payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
    payload = json_mod.loads(base64.urlsafe_b64decode(payload_b64))
    # `sub` это user.id (строкой). Возвращаем как int напрямую.
    user_id = int(payload["sub"])
    with SessionLocal() as s:
        from app.users.models import User

        u = s.get(User, user_id)
        assert u is not None, f"User not found: id={user_id}"
        return u.id
