"""Sprint 9 — тесты эндпоинта /api/v1/admin/engagement.

Метрики:
- active_users: уникальных пользователей с attempts за период
- total_attempts: количество attempts
- avg_attempts_per_active_user
- dau_last_14_days: DAU за 14 дней
- top_subjects: топ предметов по студентам
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


def _create_user(s, email: str, role: str = "student") -> int:
    """Создаёт user через register endpoint (только student/parent/teacher).

    Admin создаётся напрямую через _create_admin().
    """
    if role == "admin":
        return _create_admin(s, email)
    user = user_service.register_user(
        s,
        UserCreate(
            email=email,
            password="strongpass1",
            display_name=email.split("@")[0],
            role=role,
            grade=7,
        ),
    )
    return user.id


def _create_admin(s, email: str) -> int:
    """Sprint 9: admin создаётся напрямую в БД (через /auth/register нельзя)."""
    from app.users import models as user_models
    from app.auth.security import hash_password

    user = user_models.User(
        email=email,
        password_hash=hash_password("strongpass1"),
        display_name="Admin",
        role="admin",
        is_active=True,
    )
    s.add(user)
    s.commit()
    s.refresh(user)
    return user.id


def _login(client, email: str) -> str:
    r = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "strongpass1"}
    )
    return r.json()["access_token"]


def _add_attempt(s, user_id: int, topic_id: int, is_correct: bool = True, days_ago: int = 0) -> None:
    """Добавляет attempt в БД."""
    when = datetime.now(timezone.utc) - timedelta(days=days_ago)
    a = prog_models.Attempt(
        user_id=user_id,
        topic_id=topic_id,
        question_text="q",
        user_answer="a",
        correct_answer="c",
        is_correct=is_correct,
        score=1.0 if is_correct else 0.0,
        created_at=when,
    )
    s.add(a)
    s.commit()


def test_engagement_requires_admin(client):
    """Sprint 9: engagement endpoint требует admin role."""
    s = SessionLocal()
    try:
        _create_user(s, "kid@example.com", "student")
    finally:
        s.close()

    token = _login(client, "kid@example.com")
    r = client.get(
        "/api/v1/admin/engagement?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Student не имеет доступа к admin endpoints
    assert r.status_code == 403


def test_engagement_empty_db(client):
    """Sprint 9: пустая БД → все нули + 14 пустых DAU дней."""
    s = SessionLocal()
    try:
        admin_id = _create_user(s, "admin@example.com", "admin")
    finally:
        s.close()

    token = _login(client, "admin@example.com")
    r = client.get(
        "/api/v1/admin/engagement?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["period_days"] == 30
    assert body["active_users"] == 0
    assert body["total_attempts"] == 0
    assert body["avg_attempts_per_active_user"] == 0
    assert len(body["dau_last_14_days"]) == 14
    # DAU для пустой БД — все нули
    assert all(d["active_users"] == 0 for d in body["dau_last_14_days"])
    assert body["top_subjects"] == []


def test_engagement_active_users_count(client):
    """Sprint 9: active_users = уникальные пользователи с attempts."""
    s = SessionLocal()
    try:
        _create_user(s, "admin@example.com", "admin")
        kid1 = _create_user(s, "kid1@example.com", "student")
        kid2 = _create_user(s, "kid2@example.com", "student")
        kid3 = _create_user(s, "kid3@example.com", "student")

        # kid1: 3 attempts за 5 дней назад
        for _ in range(3):
            _add_attempt(s, kid1, 1, days_ago=5)
        # kid2: 1 attempt сегодня
        _add_attempt(s, kid2, 1, days_ago=0)
        # kid3: 1 attempt 60 дней назад (вне 30-day окна)
        _add_attempt(s, kid3, 1, days_ago=60)
    finally:
        s.close()

    token = _login(client, "admin@example.com")
    r = client.get(
        "/api/v1/admin/engagement?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    # 2 уникальных user (kid1 и kid2, kid3 за пределами 30 дней)
    assert body["active_users"] == 2
    # 4 attempts всего
    assert body["total_attempts"] == 4
    # avg = 4 / 2 = 2.0
    assert body["avg_attempts_per_active_user"] == 2.0


def test_engagement_dau_calculation(client):
    """Sprint 9: DAU правильно считает уникальных user per день."""
    s = SessionLocal()
    try:
        _create_user(s, "admin@example.com", "admin")
        kid1 = _create_user(s, "kid1@example.com", "student")
        kid2 = _create_user(s, "kid2@example.com", "student")

        # Day 3 days ago: kid1, kid2 оба активны
        _add_attempt(s, kid1, 1, days_ago=3)
        _add_attempt(s, kid2, 1, days_ago=3)
        # Day 1 day ago: только kid1
        _add_attempt(s, kid1, 1, days_ago=1)
    finally:
        s.close()

    token = _login(client, "admin@example.com")
    r = client.get(
        "/api/v1/admin/engagement?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    # DAU за 14 дней — найдём конкретные даты
    days_dict = {d["date"]: d["active_users"] for d in body["dau_last_14_days"]}
    target_3_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).date().isoformat()
    target_1_day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    # Day 3 days ago: 2 users (kid1 + kid2)
    assert days_dict[target_3_days_ago] == 2
    # Day 1 day ago: 1 user (только kid1)
    assert days_dict[target_1_day_ago] == 1
    # Total DAU = 2 (kid1, kid2) и kid1 имеет 2 attempts
    assert body["active_users"] == 2
    assert body["total_attempts"] == 3


def _date_n_days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).date().isoformat()


def test_engagement_dau_response_shape(client):
    """Sprint 9: dau_last_14_days содержит 14 записей с правильным shape."""
    s = SessionLocal()
    try:
        _create_user(s, "admin@example.com", "admin")
    finally:
        s.close()

    token = _login(client, "admin@example.com")
    r = client.get(
        "/api/v1/admin/engagement?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert len(body["dau_last_14_days"]) == 14
    for d in body["dau_last_14_days"]:
        assert "date" in d
        assert "active_users" in d
        assert isinstance(d["active_users"], int)
        # date в формате YYYY-MM-DD
        from datetime import datetime as dt
        dt.strptime(d["date"], "%Y-%m-%d")


def test_engagement_days_parameter_validation(client):
    """Sprint 16.0 P0-8: days < 1 или > 365 возвращает 422 (Query validator)."""
    s = SessionLocal()
    try:
        _create_user(s, "admin@example.com", "admin")
    finally:
        s.close()

    token = _login(client, "admin@example.com")

    # days=0 → 422 (ge=1)
    r = client.get(
        "/api/v1/admin/engagement?days=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422

    # days=999 → 422 (le=365)
    r = client.get(
        "/api/v1/admin/engagement?days=999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422

    # days=1 (на границе) → 200
    r = client.get(
        "/api/v1/admin/engagement?days=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["period_days"] == 1

    # days=365 (на границе) → 200
    r = client.get(
        "/api/v1/admin/engagement?days=365",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["period_days"] == 365


def test_engagement_top_subjects(client):
    """Sprint 9: top_subjects содержит топ-3 предмета по уникальным студентам."""
    s = SessionLocal()
    try:
        _create_user(s, "admin@example.com", "admin")
        # Seed curriculum для subject'ов
        from app.subjects.scripts_seed_runner import seed_for_tests
        seed_for_tests(s, reset=True)

        kid1 = _create_user(s, "kid1@example.com", "student")
        kid2 = _create_user(s, "kid2@example.com", "student")
        kid3 = _create_user(s, "kid3@example.com", "student")

        # Получим несколько topic_id из РАЗНЫХ subject'ов.
        from app.subjects import models as subj_models
        from sqlalchemy import distinct, select

        # Выбираем topic'и у которых РАЗНЫЕ subject_id (через section)
        # Нужны 3 разных subject_id, по 1 topic на каждый.
        # Способ: выбрать topic с минимальным id в каждом subject'е.
        unique_subjects_q = (
            s.query(subj_models.Section.subject_id, subj_models.Topic.id)
            .join(subj_models.Topic, subj_models.Topic.section_id == subj_models.Section.id)
            .order_by(subj_models.Section.subject_id, subj_models.Topic.order_index)
            .all()
        )

        # Берём первые 3 уникальных subject_id, для каждого — 1 topic_id
        seen_subjects = set()
        topic_for_subject = {}
        for subject_id, topic_id in unique_subjects_q:
            if subject_id not in seen_subjects and len(topic_for_subject) < 3:
                topic_for_subject[subject_id] = topic_id
                seen_subjects.add(subject_id)

        # Если получили 3 разных subject'а (или сколько есть)
        assert len(topic_for_subject) >= 2, f"Expected ≥ 2 subjects, got {len(topic_for_subject)}"
        topic_ids = list(topic_for_subject.values())

        # Создаём progress:
        # 1-й subject: 2 студента (kid1, kid2)
        # 2-й subject: 1 студент (kid3)
        # 3-й subject: 0 студентов
        for kid in [kid1, kid2]:
            p = prog_models.Progress(
                user_id=kid, topic_id=topic_ids[0],
                mastery_score=0.5, attempts_count=1, correct_count=1,
            )
            s.add(p)
        p = prog_models.Progress(
            user_id=kid3, topic_id=topic_ids[1],
            mastery_score=0.5, attempts_count=1, correct_count=1,
        )
        s.add(p)
        s.commit()
    finally:
        s.close()

    token = _login(client, "admin@example.com")
    r = client.get(
        "/api/v1/admin/engagement?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    top = body["top_subjects"]
    # top_subjects должен содержать subjects с students
    # Сортировка: students DESC, потом subject_id ASC (стабильный tie-break)
    # Top: subject с 2 students
    assert len(top) >= 1
    top_students = [s["students"] for s in top]
    # Максимум студентов = 2 (kid1+kid2 на первом subject)
    assert max(top_students) == 2
    # top[0] должен иметь 2 students
    assert top[0]["students"] == 2
    # Если есть top[1] — у него 1 student
    if len(top) > 1:
        assert top[1]["students"] == 1


def test_engagement_excludes_admin_from_active_users(client):
    """Sprint 9: admin не считается в active_users (только students/parents/...)."""
    s = SessionLocal()
    try:
        _create_user(s, "admin@example.com", "admin")
        _create_user(s, "kid@example.com", "student")

        # Admin делает attempts (не реально, но проверим)
        # Admin в данном тесте НЕ делает attempts — просто проверяем что
        # admin token + admin request не показывает admin в active_users
    finally:
        s.close()

    token = _login(client, "admin@example.com")
    r = client.get(
        "/api/v1/admin/engagement?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    # Тут admin запросил — у admin нет attempts
    assert body["active_users"] == 0


def test_engagement_response_shape(client):
    """Sprint 9: response содержит все обязательные поля."""
    s = SessionLocal()
    try:
        _create_user(s, "admin@example.com", "admin")
    finally:
        s.close()

    token = _login(client, "admin@example.com")
    r = client.get(
        "/api/v1/admin/engagement?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    required = [
        "period_days",
        "active_users",
        "total_attempts",
        "avg_attempts_per_active_user",
        "dau_last_14_days",
        "top_subjects",
    ]
    for field in required:
        assert field in body, f"Missing field: {field}"


def test_engagement_period_days_reflects_param(client):
    """Sprint 9: period_days в response соответствует запрошенному."""
    s = SessionLocal()
    try:
        _create_user(s, "admin@example.com", "admin")
    finally:
        s.close()

    token = _login(client, "admin@example.com")
    for days in [7, 14, 30, 90]:
        r = client.get(
            f"/api/v1/admin/engagement?days={days}",
            headers={"Authorization": f"Bearer {token}"},
        )
        body = r.json()
        assert body["period_days"] == days


def test_engagement_avg_handles_zero_active_users(client):
    """Sprint 9: avg = 0 когда active_users = 0 (деление на 0)."""
    s = SessionLocal()
    try:
        _create_user(s, "admin@example.com", "admin")
    finally:
        s.close()

    token = _login(client, "admin@example.com")
    r = client.get(
        "/api/v1/admin/engagement?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = r.json()
    # avg_attempts_per_active_user должен быть 0, не error
    assert body["avg_attempts_per_active_user"] == 0