"""Pilot Core Stage 1 — Phase 2 (P1.2.3, P1.2.4): v2 exercises endpoint tests.

Покрывают:
- generate → safe projection (без correct_answer/explanation);
- answer → server-owned truth, idempotency;
- чужой exercise_id → 404;
- expired exercise_id → 410.
"""
from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from datetime import datetime, timedelta, timezone
import json

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.subjects import models as subj_models  # noqa: E402
from app.subjects.scripts_seed_runner import seed_for_tests  # noqa: E402
from app.users.models import Role, User  # noqa: E402


@pytest.fixture()
def client():
    from app.db.session import engine as default_engine

    Base.metadata.drop_all(default_engine)
    default_engine.dispose()
    Base.metadata.create_all(default_engine)

    # Сидим curriculum → появляются subject/section/topic
    with SessionLocal() as s:
        seed_for_tests(s, reset=False)
        s.commit()

    def _override_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(default_engine)


def _register(c: TestClient, email: str, role: str = "student", name: str = "Кирилл") -> str:
    payload = {
        "email": email,
        "password": "strongpass1",
        "display_name": name,
        "role": role,
    }
    if role == "student":
        payload["grade"] = 7
    r = c.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201, r.text
    login = c.post("/api/v1/auth/login", json={"email": email, "password": "strongpass1"})
    return login.json()["access_token"]


def _first_topic_id(db=None) -> int:
    from app.db.session import SessionLocal

    with SessionLocal() as s:
        t = s.query(subj_models.Topic).order_by(subj_models.Topic.id).first()
        assert t is not None
        return t.id


def test_v2_generate_returns_safe_projection(client):
    """P1.2.3: generate не отдаёт correct_answer/explanation."""
    token = _register(client, "v2-student@example.com")
    h = {"Authorization": f"Bearer {token}"}
    topic_id = _first_topic_id()

    r = client.post(
        "/api/v2/exercises/generate",
        headers=h,
        json={"topic_id": topic_id, "difficulty": 2},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "exercise_id" in body and isinstance(body["exercise_id"], int)
    assert "question_text" in body
    # safe projection — НЕ должно быть correct_answer/explanation
    serialized = json.dumps(body)
    assert "correct_answer" not in serialized
    assert "explanation" not in serialized


def test_v2_answer_correct_creates_attempt_and_progress(client):
    """P1.2.3: answer с правильным ответом сохраняет Attempt + обновляет Progress."""
    token = _register(client, "v2-student-2@example.com")
    h = {"Authorization": f"Bearer {token}"}
    topic_id = _first_topic_id()

    gen = client.post(
        "/api/v2/exercises/generate",
        headers=h,
        json={"topic_id": topic_id},
    ).json()

    # Узнаём correct_answer через прямой БД-доступ (мы не можем через API)
    from app.db.session import SessionLocal
    from app.ai.models import GeneratedExerciseInstance

    with SessionLocal() as s:
        inst = s.get(GeneratedExerciseInstance, gen["exercise_id"])
        correct = inst.correct_answer

    r = client.post(
        f"/api/v2/exercises/{gen['exercise_id']}/answer",
        headers=h,
        json={"user_answer": correct},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_correct"] is True
    assert body["score"] == 1.0
    assert "explanation" in body  # теперь можно показать


def test_v2_answer_wrong_does_not_set_correct(client):
    """P1.2.3: неправильный user_answer → is_correct=False, score=0."""
    token = _register(client, "v2-student-3@example.com")
    h = {"Authorization": f"Bearer {token}"}
    topic_id = _first_topic_id()

    gen = client.post(
        "/api/v2/exercises/generate", headers=h, json={"topic_id": topic_id}
    ).json()
    r = client.post(
        f"/api/v2/exercises/{gen['exercise_id']}/answer",
        headers=h,
        json={"user_answer": "явно неправильный ответ который никогда не совпадёт с эталоном"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_correct"] is False
    assert body["score"] == 0.0


def test_v2_answer_idempotent_does_not_create_second_attempt(client):
    """P1.2.4: повтор submit возвращает тот же результат, без новой attempt-записи."""
    token = _register(client, "v2-student-4@example.com")
    h = {"Authorization": f"Bearer {token}"}
    topic_id = _first_topic_id()

    gen = client.post(
        "/api/v2/exercises/generate", headers=h, json={"topic_id": topic_id}
    ).json()

    from app.db.session import SessionLocal
    from app.ai.models import GeneratedExerciseInstance
    from app.progress import models as progress_models

    with SessionLocal() as s:
        inst = s.get(GeneratedExerciseInstance, gen["exercise_id"])
        correct = inst.correct_answer

    # Первый submit
    r1 = client.post(
        f"/api/v2/exercises/{gen['exercise_id']}/answer",
        headers=h,
        json={"user_answer": correct},
    )
    assert r1.status_code == 200

    # Сколько attempt'ов сейчас
    with SessionLocal() as s:
        count_after_first = (
            s.query(progress_models.Attempt)
            .filter_by(user_id=s.query(User).filter_by(email="v2-student-4@example.com").one().id)
            .count()
        )
    assert count_after_first == 1

    # Второй submit (идемпотентный)
    r2 = client.post(
        f"/api/v2/exercises/{gen['exercise_id']}/answer",
        headers=h,
        json={"user_answer": correct},
    )
    assert r2.status_code == 200
    assert r2.json()["is_correct"] is True

    # Не должно появиться нового Attempt
    with SessionLocal() as s:
        count_after_second = (
            s.query(progress_models.Attempt)
            .filter_by(user_id=s.query(User).filter_by(email="v2-student-4@example.com").one().id)
            .count()
        )
    assert count_after_second == 1, "idempotency violated: second attempt was created"


def test_v2_answer_other_user_exercise_id_returns_404(client):
    """P1.2.3: чужой exercise_id → 404."""
    token_a = _register(client, "v2-owner@example.com")
    token_b = _register(client, "v2-other@example.com")
    h_a = {"Authorization": f"Bearer {token_a}"}
    h_b = {"Authorization": f"Bearer {token_b}"}

    topic_id = _first_topic_id()
    gen = client.post(
        "/api/v2/exercises/generate", headers=h_a, json={"topic_id": topic_id}
    ).json()

    r = client.post(
        f"/api/v2/exercises/{gen['exercise_id']}/answer",
        headers=h_b,
        json={"user_answer": "anything"},
    )
    assert r.status_code == 404, r.text


def test_v2_answer_expired_returns_410(client):
    """P1.2.3: expired exercise_id → 410 Gone."""
    token = _register(client, "v2-exp@example.com")
    h = {"Authorization": f"Bearer {token}"}
    topic_id = _first_topic_id()

    gen = client.post(
        "/api/v2/exercises/generate", headers=h, json={"topic_id": topic_id}
    ).json()

    # Вручную делаем exercise expired через прямой БД-доступ
    from app.db.session import SessionLocal
    from app.ai.models import GeneratedExerciseInstance

    with SessionLocal() as s:
        inst = s.get(GeneratedExerciseInstance, gen["exercise_id"])
        inst.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        s.commit()

    r = client.post(
        f"/api/v2/exercises/{gen['exercise_id']}/answer",
        headers=h,
        json={"user_answer": "x"},
    )
    assert r.status_code == 410, r.text
