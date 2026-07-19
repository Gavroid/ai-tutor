"""Sprint 8.1 — тесты эндпоинта /api/v1/student/streak.

T1D-friendly дизайн:
- current_streak: сколько дней подряд до сегодня включительно
- longest_streak: max за всё время, растёт
- total_active_days: сколько уникальных дней была активность
- encouragement: позитивное сообщение
- Пропуск дня НЕ наказывается
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

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


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    yield TestClient(app)
    Base.metadata.drop_all(engine)
    engine.dispose()


def _create_student(s, email: str = "kid@example.com") -> int:
    user = user_service.register_user(
        s,
        UserCreate(
            email=email,
            password="strongpass1",
            display_name="Кирилл",
            role="student",
            grade=7,
        ),
    )
    return user.id


def _login(client, email: str = "kid@example.com") -> str:
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "strongpass1"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _add_attempt(s, user_id: int, topic_id: int, is_correct: bool, days_ago: int) -> None:
    """Добавляет attempt в БД с created_at = days_ago назад от сегодня."""
    when = datetime.now(timezone.utc) - timedelta(days=days_ago)
    a = prog_models.Attempt(
        user_id=user_id,
        topic_id=topic_id,
        # NOT NULL: text fields
        question_text="test question",
        user_answer="test answer",
        correct_answer="test correct",
        is_correct=is_correct,
        # Sprint 3.0: numeric grading 0..1
        score=1.0 if is_correct else 0.0,
        created_at=when,
    )
    s.add(a)
    s.commit()


def test_streak_no_attempts(client):
    """Sprint 8.1: новый ученик без attempts → все нули + positive message."""
    s = SessionLocal()
    try:
        _create_student(s)
    finally:
        s.close()

    token = _login(client)
    r = client.get("/api/v1/student/streak", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()

    assert body["current_streak_days"] == 0
    assert body["longest_streak_days"] == 0
    assert body["total_active_days"] == 0
    assert body["last_active_date"] is None
    # T1D-friendly: для нулевой серии — мягкое послание.
    assert "нов" in body["encouragement"].lower() or "🌱" in body["encouragement"]


def test_streak_today_only(client):
    """Sprint 8.1: attempt сегодня → current=1, longest=1, total=1."""
    s = SessionLocal()
    user_id = None
    try:
        user_id = _create_student(s)
        _add_attempt(s, user_id, topic_id=1, is_correct=True, days_ago=0)
    finally:
        s.close()

    token = _login(client)
    r = client.get("/api/v1/student/streak", headers={"Authorization": f"Bearer {token}"})
    body = r.json()
    assert body["current_streak_days"] == 1
    assert body["longest_streak_days"] == 1
    assert body["total_active_days"] == 1
    assert body["last_active_date"] is not None


def test_streak_consecutive_three_days(client):
    """Sprint 8.1: 3 дня подряд → current=3, longest=3, total=3."""
    s = SessionLocal()
    user_id = None
    try:
        user_id = _create_student(s)
        for d in (0, 1, 2):
            _add_attempt(s, user_id, topic_id=1, is_correct=True, days_ago=d)
    finally:
        s.close()

    token = _login(client)
    r = client.get("/api/v1/student/streak", headers={"Authorization": f"Bearer {token}"})
    body = r.json()
    assert body["current_streak_days"] == 3
    assert body["longest_streak_days"] == 3
    assert body["total_active_days"] == 3


def test_streak_skip_yesterday_breaks_current_not_longest(client):
    """Sprint 8.1 T1D-friendly: пропуск вчера → current=1, longest сохраняется.

    Если ученик был активен 3 дня (longest=3), потом пропустил день,
    и сегодня снова активен — current=1, но longest всё равно 3.
    Никакого штрафа.
    """
    s = SessionLocal()
    user_id = None
    try:
        user_id = _create_student(s)
        # Активность 4, 3, 2 дня назад (longest=3)
        for d in (2, 3, 4):
            _add_attempt(s, user_id, topic_id=1, is_correct=True, days_ago=d)
        # Пропуск вчера (1 день назад)
        # Сегодня снова активен
        _add_attempt(s, user_id, topic_id=1, is_correct=True, days_ago=0)
    finally:
        s.close()

    token = _login(client)
    r = client.get("/api/v1/student/streak", headers={"Authorization": f"Bearer {token}"})
    body = r.json()
    # Текущая серия сбрасывается (пропуск вчера)
    assert body["current_streak_days"] == 1, "current should be 1 (today only)"
    # Longest сохраняется (3 дня подряд ранее)
    assert body["longest_streak_days"] == 3, "longest should remain 3"
    # Total = 4 дня (не считаем вчера)
    assert body["total_active_days"] == 4


def test_streak_longest_grows_with_break(client):
    """Sprint 8.1: longest_streak растёт когда появляется новая длинная серия."""
    s = SessionLocal()
    user_id = None
    try:
        user_id = _create_student(s)
        # Первая серия: 2 дня (5, 6 дней назад)
        for d in (5, 6):
            _add_attempt(s, user_id, topic_id=1, is_correct=True, days_ago=d)
        # Пропуск (3, 4 дня)
        # Вторая серия: 3 дня (1, 2, 0 — но 0 это today)
        for d in (0, 1, 2):
            _add_attempt(s, user_id, topic_id=1, is_correct=True, days_ago=d)
    finally:
        s.close()

    token = _login(client)
    r = client.get("/api/v1/student/streak", headers={"Authorization": f"Bearer {token}"})
    body = r.json()
    # Current = 3 (сегодня + 1 + 2 дня назад)
    assert body["current_streak_days"] == 3
    # Longest = 3 (вторая серия длиннее первой)
    assert body["longest_streak_days"] == 3
    # Total = 5 уникальных дней
    assert body["total_active_days"] == 5


def test_streak_no_today_yet_current_zero(client):
    """Sprint 8.1: если сегодня ещё не было активности → current=0.

    Ученик был активен 2 дня назад (current=0), но longest и total
    сохраняются. T1D-friendly: это не штраф.
    """
    s = SessionLocal()
    user_id = None
    try:
        user_id = _create_student(s)
        _add_attempt(s, user_id, topic_id=1, is_correct=True, days_ago=1)
    finally:
        s.close()

    token = _login(client)
    r = client.get("/api/v1/student/streak", headers={"Authorization": f"Bearer {token}"})
    body = r.json()
    # current=0 потому что сегодня не было активности
    assert body["current_streak_days"] == 0
    # longest=1 (был один день активности)
    assert body["longest_streak_days"] == 1
    # total=1
    assert body["total_active_days"] == 1
    # T1D-friendly: encouragement не агрессивный
    assert "нов" in body["encouragement"].lower() or "🌱" in body["encouragement"]


def test_streak_another_user_isolation(client):
    """Sprint 8.1: streak изолирован per user."""
    s = SessionLocal()
    user1_id = user2_id = None
    try:
        user1_id = _create_student(s, "kid1@example.com")
        user2_id = _create_student(s, "kid2@example.com")
        # Только user1 имеет attempts
        _add_attempt(s, user1_id, topic_id=1, is_correct=True, days_ago=0)
    finally:
        s.close()

    # Логинимся как user2 — его streak пуст
    token = _login(client, "kid2@example.com")
    r = client.get("/api/v1/student/streak", headers={"Authorization": f"Bearer {token}"})
    body = r.json()
    assert body["current_streak_days"] == 0
    assert body["total_active_days"] == 0


def test_streak_requires_auth(client):
    """Sprint 8.1: streak endpoint требует аутентификации."""
    r = client.get("/api/v1/student/streak")
    assert r.status_code == 401


def test_streak_longest_format_yyyy_mm_dd(client):
    """Sprint 8.1: last_active_date в формате YYYY-MM-DD."""
    s = SessionLocal()
    user_id = None
    try:
        user_id = _create_student(s)
        _add_attempt(s, user_id, topic_id=1, is_correct=True, days_ago=0)
    finally:
        s.close()

    token = _login(client)
    r = client.get("/api/v1/student/streak", headers={"Authorization": f"Bearer {token}"})
    body = r.json()
    date_str = body["last_active_date"]
    # Должно быть валидной датой YYYY-MM-DD
    assert date_str is not None
    datetime.strptime(date_str, "%Y-%m-%d")  # raises если невалидна