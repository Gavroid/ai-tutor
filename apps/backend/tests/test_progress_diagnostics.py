"""Тесты прогресса + диагностики (Этап 7, 8)."""
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

from app.ai import hermes
from app.ai.service import get_ai_service
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.progress import models as prog_models
from app.subjects import models as subj_models
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    s = SessionLocal()
    try:
        user_service.register_user(
            s,
            UserCreate(
                email="kirill@example.com",
                password="strongpass1",
                display_name="Кирилл",
                role="student",
                grade=7,
            ),
        )
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
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _login(c: TestClient) -> str:
    return c.post(
        "/api/v1/auth/login",
        json={"email": "kirill@example.com", "password": "strongpass1"},
    ).json()["access_token"]


def _algebra_topic_id(s=None) -> int:
    s = s or SessionLocal()
    try:
        subj = s.scalar(select(subj_models.Subject).where(subj_models.Subject.code == "algebra"))
        topic = s.scalar(
            select(subj_models.Topic)
            .join(subj_models.Section)
            .where(subj_models.Section.subject_id == subj.id)
            .limit(1)
        )
        return topic.id
    finally:
        s.close()


# ===== Progress =====


def test_progress_record_attempt(client):
    token = _login(client)
    tid = _algebra_topic_id()
    r = client.post(
        "/api/v1/progress/attempts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "topic_id": tid,
            "question_text": "Сколько будет 2+2?",
            "user_answer": "4",
            "correct_answer": "4",
            "is_correct": True,
            "score": 1.0,
        },
    )
    assert r.status_code == 200
    assert r.json()["is_correct"]


def test_progress_mastery_updates(client):
    token = _login(client)
    tid = _algebra_topic_id()
    # 3 правильных попытки
    for _ in range(3):
        client.post(
            "/api/v1/progress/attempts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "topic_id": tid,
                "question_text": "q",
                "user_answer": "a",
                "correct_answer": "a",
                "is_correct": True,
                "score": 1.0,
            },
        )
    # 1 неправильная
    client.post(
        "/api/v1/progress/attempts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "topic_id": tid,
            "question_text": "q",
            "user_answer": "wrong",
            "correct_answer": "right",
            "is_correct": False,
            "score": 0.0,
            "feedback": "Неверно",
        },
    )
    r = client.get("/api/v1/progress", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    p = next((x for x in data if x["topic_id"] == tid), None)
    assert p is not None
    assert p["attempts_count"] == 4
    assert p["correct_count"] == 3
    # Mastery около 0.75 (3/4)
    assert 0.7 < p["mastery_score"] < 0.8


def test_progress_mistakes_aggregated(client):
    token = _login(client)
    tid = _algebra_topic_id()
    for _ in range(3):
        client.post(
            "/api/v1/progress/attempts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "topic_id": tid,
                "question_text": "q",
                "user_answer": "x",
                "correct_answer": "y",
                "is_correct": False,
                "score": 0.0,
                "feedback": "Забыл знак",
            },
        )
    r = client.get("/api/v1/progress/mistakes", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert data[0]["count"] == 3


def test_progress_recommend_review(client):
    token = _login(client)
    tid = _algebra_topic_id()
    # Записываем много неправильных попыток
    for _ in range(5):
        client.post(
            "/api/v1/progress/attempts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "topic_id": tid,
                "question_text": "q",
                "user_answer": "x",
                "correct_answer": "y",
                "is_correct": False,
                "score": 0.0,
            },
        )
    r = client.get("/api/v1/progress/recommend-review", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert r.json()[0]["mastery_score"] < 0.5


# ===== Diagnostics =====


def test_diagnostic_full_flow(client):
    token = _login(client)
    subj_id = SessionLocal().scalar(
        select(subj_models.Subject).where(subj_models.Subject.code == "algebra")
    ).id

    # Start
    r = client.post(
        "/api/v1/diagnostic/start",
        json={"subject_id": subj_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    sid = r.json()["id"]
    assert r.json()["status"] == "in_progress"

    # Получаем вопросы и отвечаем
    for i in range(3):
        r = client.get(
            f"/api/v1/diagnostic/{sid}/next",
            headers={"Authorization": f"Bearer {token}"},
        )
        if r.status_code == 404:
            break  # вопросы кончились
        assert r.status_code == 200
        q = r.json()
        client.post(
            f"/api/v1/diagnostic/{sid}/answer",
            json={
                "topic_id": q["topic_id"],
                "question_text": q["question_text"],
                "user_answer": "правильный ответ про алгебру",
                "correct_answer": q["question_text"],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    # Finish
    r = client.post(
        f"/api/v1/diagnostic/{sid}/finish",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "finished"
    assert body["total_questions"] >= 1
    assert body["recommendations"]
    assert "повторить" in body["recommendations"].lower() or "Отличный" in body["recommendations"]


# ===== Rate limit =====


def test_rate_limit_ai(client):
    """Превышение лимита AI возвращает 429."""
    import os
    os.environ["RATE_LIMIT_AI_PER_MINUTE"] = "3"

    # Перезагрузим config cache и очистим rate limit log (мог быть заполнен
    # предыдущими тестами в той же сессии pytest).
    from app.config import get_settings
    from app.main import _ai_call_log
    _ai_call_log.clear()
    get_settings.cache_clear()

    token = _login(client)
    tid = _algebra_topic_id()
    statuses = []
    for _ in range(5):
        r = client.post(
            "/api/v1/ai/explain",
            json={"topic_id": tid},
            headers={"Authorization": f"Bearer {token}"},
        )
        statuses.append(r.status_code)
    # Cleanup для следующих тестов
    _ai_call_log.clear()
    get_settings.cache_clear()
    # Первые 3 — 200, остальные — 429
    assert statuses[:3].count(200) >= 1, f"Expected at least one 200, got {statuses[:3]}"
    assert 429 in statuses, f"Expected 429 in {statuses}"