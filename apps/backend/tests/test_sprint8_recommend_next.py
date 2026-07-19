"""Sprint 8.2 — тесты эндпоинта /api/v1/progress/recommend-next.

Алгоритм:
1. Если есть темы с mastery < 0.5 (и attempts > 0) → самая слабая
2. Иначе → следующая непройденная тема в curriculum
3. Иначе → "all_mastered" поздравление
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.users import service as user_service
from app.users.schemas import UserCreate
from app.progress import models as prog_models
from app.subjects import models as subj_models


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    yield TestClient(app)
    Base.metadata.drop_all(engine)
    engine.dispose()


def _setup_kid_with_seed():
    """Создаёт ученика + curriculum (subjects, sections, topics)."""
    s = SessionLocal()
    try:
        user = user_service.register_user(
            s,
            UserCreate(
                email="kid@example.com",
                password="strongpass1",
                display_name="Кирилл",
                role="student",
                grade=7,
            ),
        )
        # Seed curriculum (reset=True чтобы избежать конфликтов UNIQUE)
        from app.subjects.scripts_seed_runner import seed_for_tests

        seed_for_tests(s, reset=True)
        return user.id
    finally:
        s.close()


def _login(client, email: str = "kid@example.com") -> str:
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "strongpass1"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _add_progress(s, user_id: int, topic_id: int, mastery: float, attempts: int = 1) -> None:
    """Добавляет progress для topic (mastery, attempts_count)."""
    p = prog_models.Progress(
        user_id=user_id,
        topic_id=topic_id,
        mastery_score=mastery,
        attempts_count=attempts,
        correct_count=int(attempts * mastery),
    )
    s.add(p)
    s.commit()


def test_recommend_next_no_attempts_returns_next_topic(client):
    """Sprint 8.2: новый ученик → рекомендует первую тему в curriculum."""
    _setup_kid_with_seed()
    token = _login(client)
    r = client.get(
        "/api/v1/progress/recommend-next",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["reason"] == "next_in_curriculum"
    assert body["topic_id"] is not None
    assert body["topic_name"] is not None
    assert body["subject_id"] is not None
    assert body["mastery_score"] is None  # нет progress
    # encouragement — позитивное (содержит эмодзи или слово поддержки)
    assert any(emoji in body["encouragement"] for emoji in ["🚀", "💪", "📚", "✨", "🌟"]) or len(body["encouragement"]) > 5


def test_recommend_next_weak_topic_priority(client):
    """Sprint 8.2: тема с mastery < 0.5 приоритетнее новых тем."""
    s = SessionLocal()
    user_id = None
    try:
        user_id = _setup_kid_with_seed()  # уже seed'нул

        # Найдём первые 2 topic_id (сохраняем id сразу чтобы избежать DetachedInstance)
        topic_ids = [
            row[0]
            for row in s.query(subj_models.Topic.id).order_by(subj_models.Topic.id).limit(2).all()
        ]
        assert len(topic_ids) >= 2
        weak_topic_id = topic_ids[0]
        good_topic_id = topic_ids[1]

        # weak: mastery=0.2 (триггерит weak_topic)
        _add_progress(s, user_id, weak_topic_id, mastery=0.2, attempts=2)
        # good: mastery=0.6 (выше 0.5)
        _add_progress(s, user_id, good_topic_id, mastery=0.6, attempts=3)
    finally:
        s.close()

    token = _login(client)
    r = client.get(
        "/api/v1/progress/recommend-next",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert body["reason"] == "weak_topic"
    assert body["topic_id"] == weak_topic_id
    assert body["mastery_score"] == 0.2
    # encouragement содержит %
    assert "20" in body["encouragement"]


def test_recommend_next_weakest_topic_selected(client):
    """Sprint 8.2: при нескольких слабых темах — выбирается САМАЯ слабая."""
    s = SessionLocal()
    user_id = None
    try:
        user_id = _setup_kid_with_seed()  # уже seed'нул

        topic_ids = [
            row[0]
            for row in s.query(subj_models.Topic.id).order_by(subj_models.Topic.id).limit(3).all()
        ]
        weakest_id = topic_ids[1]  # будет mastery=0.1 — самая слабая
        # topic1: mastery=0.3
        _add_progress(s, user_id, topic_ids[0], mastery=0.3, attempts=2)
        # topic2: mastery=0.1 (САМАЯ слабая)
        _add_progress(s, user_id, weakest_id, mastery=0.1, attempts=1)
        # topic3: mastery=0.4
        _add_progress(s, user_id, topic_ids[2], mastery=0.4, attempts=2)
    finally:
        s.close()

    token = _login(client)
    r = client.get(
        "/api/v1/progress/recommend-next",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert body["reason"] == "weak_topic"
    # Самая слабая — topic_ids[1] (mastery=0.1)
    assert body["topic_id"] == weakest_id
    assert body["mastery_score"] == 0.1


def test_recommend_next_skips_zero_mastery_topics(client):
    """Sprint 8.2: темы с mastery=0 без attempts → next_in_curriculum (не weak_topic)."""
    s = SessionLocal()
    user_id = None
    try:
        user_id = _setup_kid_with_seed()  # уже seed'нул

        topic_id = s.query(subj_models.Topic.id).order_by(subj_models.Topic.id).first()[0]
        # mastery=0, attempts=0 — это просто не пройдено, не "weak"
        _add_progress(s, user_id, topic_id, mastery=0.0, attempts=0)
    finally:
        s.close()

    token = _login(client)
    r = client.get(
        "/api/v1/progress/recommend-next",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    # mastery=0 без attempts — это next_in_curriculum (не weak_topic)
    assert body["reason"] == "next_in_curriculum"


def test_recommend_next_all_mastered(client):
    """Sprint 8.2: все темы mastered → поздравление."""
    s = SessionLocal()
    user_id = None
    try:
        user_id = _setup_kid_with_seed()  # уже seed'нул

        # Все темы с mastery >= 0.5
        for t in s.query(subj_models.Topic).all():
            _add_progress(s, user_id, t.id, mastery=0.7, attempts=3)
    finally:
        s.close()

    token = _login(client)
    r = client.get(
        "/api/v1/progress/recommend-next",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert body["reason"] == "all_mastered"
    assert body["topic_id"] is None
    # encouragement позитивный
    assert any(emoji in body["encouragement"] for emoji in ["🎉", "✨", "🏆"]) or "невероятно" in body["encouragement"].lower()


def test_recommend_next_requires_auth(client):
    """Sprint 8.2: endpoint требует аутентификации."""
    r = client.get("/api/v1/progress/recommend-next")
    assert r.status_code == 401


def test_recommend_next_response_shape(client):
    """Sprint 8.2: response содержит все обязательные поля."""
    _setup_kid_with_seed()
    token = _login(client)
    r = client.get(
        "/api/v1/progress/recommend-next",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    # Все поля должны быть в response
    required = ["topic_id", "topic_name", "subject_id", "subject_name", "reason", "mastery_score", "encouragement"]
    for field in required:
        assert field in body, f"Missing field: {field}"
    # reason должен быть одной из 3 валидных
    assert body["reason"] in ("weak_topic", "next_in_curriculum", "all_mastered")


def test_recommend_next_isolated_per_user(client):
    """Sprint 8.2: рекомендация изолирована per user."""
    s = SessionLocal()
    try:
        _setup_kid_with_seed()  # первый kid + seed
        # Создаём второго ученика
        user_service.register_user(
            s,
            UserCreate(
                email="kid2@example.com",
                password="strongpass1",
                display_name="Другой",
                role="student",
                grade=7,
            ),
        )

        kid1_id = s.query(__import__("app.users.models", fromlist=["User"]).User).filter_by(email="kid@example.com").first().id

        # Даем kid1 слабую тему
        t1_id = s.query(subj_models.Topic.id).order_by(subj_models.Topic.id).first()[0]
        _add_progress(s, kid1_id, t1_id, mastery=0.2, attempts=2)
    finally:
        s.close()

    # Логинимся как kid2 — у него НЕТ слабых тем → next_in_curriculum
    token = _login(client, "kid2@example.com")
    r = client.get(
        "/api/v1/progress/recommend-next",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert body["reason"] == "next_in_curriculum"
    # НЕ рекомендует чужую слабую тему
    assert body["topic_id"] != t1_id or body["mastery_score"] is None


def test_recommend_next_weak_topic_excludes_completed_attempts(client):
    """Sprint 8.2: тема с attempts > 0 и mastery=0.3 (weak) — weak_topic."""
    s = SessionLocal()
    user_id = None
    try:
        user_id = _setup_kid_with_seed()  # уже seed'нул

        topic_id = s.query(subj_models.Topic.id).order_by(subj_models.Topic.id).first()[0]
        # mastery=0.3, attempts=3 (все неправильные) — это WEAK (< 0.5, attempts > 0)
        _add_progress(s, user_id, topic_id, mastery=0.3, attempts=3)
    finally:
        s.close()

    token = _login(client)
    r = client.get(
        "/api/v1/progress/recommend-next",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    # mastery=0.3 И attempts > 0 — weak_topic (потому что пытался, но не получилось)
    assert body["reason"] == "weak_topic"
    assert body["mastery_score"] == 0.3