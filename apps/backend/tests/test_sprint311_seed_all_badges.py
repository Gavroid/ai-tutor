"""Sprint 3.11 — pytest: проверяет seed_all_badges.py + полный acceptance S4.

Тест использует in-memory SQLite через ту же fixtures-структуру что и
test_admin.py (Base.metadata.create_all + SessionLocal). Это даёт чистые данные
для каждого теста.

Sprint 3.11 update: каталог расширен с 20 до 44 бейджей.
Sprint 3.12 update: каталог расширен до 60 бейджей (15 в каждой из 4 категорий):
- count: 15 (1, 5, 10, 50, 100, 200, ..., 1500)
- effort: 15 (quality_correct + mastered + review_count + correct_count thresholds)
- streak: 15 (3..365 milestones + streak_correct + returned_after_pause + returned_Nx)
- context: 15 (polymath_week + early_bird + night_owl + weekend_* + perfect_five +
              ten/twenty/fifty_in_a_row + morning_streak + lunch_* + late_night_hero)

Покрывает:
- Сценарий «с нуля» → seed_all → 60/60 бейджей
- Idempotency (повторный запуск → 0 awarded, 60 already_had)
- Все 4 категории (count, effort, streak, context) дают бейджи
- Evidence сохраняется в БД как JSON

Run: pytest tests/test_sprint311_seed_all_badges.py -v
"""
from __future__ import annotations

import json
import os
import sys

import pytest

# Sprint 3.11: для доступа к scripts/ из теста добавляем путь.
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TESTS_DIR)
sys.path.insert(0, BACKEND_DIR)

from app.db.session import Base, SessionLocal, engine  # noqa: E402

from scripts.seed_all_badges import (  # noqa: E402
    SEED_EVIDENCE,
    seed_all,
    seed_one,
)

EXPECTED_BADGES = set(SEED_EVIDENCE.keys())
TOTAL_BADGES = 60  # Sprint 3.12: 15 в каждой из 4 категорий


@pytest.fixture()
def db_session():
    """Чистая in-memory БД для каждого теста."""
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def _make_user(s, email: str) -> int:
    """Создать пользователя с уникальным email и вернуть user_id."""
    from app.auth.security import hash_password
    from app.users.models import Role, User

    user = User(
        email=email,
        password_hash=hash_password("TestBadges!2026"),
        display_name="Test Badges",
        role=Role.STUDENT,
    )
    s.add(user)
    s.commit()
    s.refresh(user)
    return user.id


def test_seed_all_awards_all_badges_for_new_user(db_session):
    """Новый пользователь без бейджей → seed_all → 53 awarded, 0 already."""
    user_id = _make_user(db_session, "fresh-test@example.com")

    result = seed_all(db_session, user_id)

    assert len(result["awarded"]) == TOTAL_BADGES, (
        f"expected {TOTAL_BADGES}, got {len(result['awarded'])}: {result['awarded']}"
    )
    assert len(result["already_had"]) == 0
    assert set(result["awarded"]) == EXPECTED_BADGES


def test_seed_all_is_idempotent(db_session):
    """Повторный вызов → 0 awarded, 53 already."""
    user_id = _make_user(db_session, "idempotent-test@example.com")

    result1 = seed_all(db_session, user_id)
    assert len(result1["awarded"]) == TOTAL_BADGES

    # Second call — все бейджи должны быть already_had.
    result2 = seed_all(db_session, user_id)
    assert len(result2["awarded"]) == 0
    assert len(result2["already_had"]) == TOTAL_BADGES
    assert set(result2["already_had"]) == EXPECTED_BADGES


def test_seed_all_persists_to_database(db_session):
    """Проверяет что бейджи реально записались в БД с правильным evidence."""
    from app.student.models import BadgeDefinition, UserBadge

    user_id = _make_user(db_session, "db-persist-test@example.com")
    seed_all(db_session, user_id)

    # Все бейджи должны быть в user_badges.
    rows = db_session.query(UserBadge).filter(UserBadge.user_id == user_id).all()
    assert len(rows) == TOTAL_BADGES

    # Все BadgeDefinition должны быть засеяны.
    defs = db_session.query(BadgeDefinition).all()
    assert len(defs) == TOTAL_BADGES
    slugs = {d.slug for d in defs}
    assert slugs == EXPECTED_BADGES


def test_seed_all_categories_covered(db_session):
    """Все 4 категории (count, effort, streak, context) покрыты seed_all.

    Sprint 3.12: каждая категория содержит ровно 15 бейджей.
    """
    COUNT_BADGES = {
        "first_step", "five_solved", "ten_solved", "fifty_solved", "hundred_solved",
        "two_hundred_solved", "three_hundred_solved", "four_hundred_solved",
        "five_hundred_solved", "six_hundred_solved", "seven_hundred_solved",
        "eight_hundred_solved", "nine_hundred_solved", "thousand_solved",
        "fifteen_hundred_solved",
    }
    EFFORT_BADGES = {
        "explained_in_own_words", "five_quality_correct", "twenty_quality_correct",
        "fifty_quality_correct", "returned_to_hard", "mastered_topic",
        "mastered_five_topics", "all_basics", "review_count_10",
        "review_count_50", "asked_question",
        "correct_count_25", "correct_count_75", "correct_count_150", "correct_count_500",
    }
    STREAK_BADGES = {
        "streak_3", "streak_7", "streak_14", "streak_30", "streak_45",
        "streak_60", "streak_100", "streak_180", "streak_365",
        "returned_after_pause",
        "streak_correct_5", "streak_correct_14", "streak_correct_30",
        "returned_twice", "returned_five",
    }
    CONTEXT_BADGES = {
        "polymath_week", "early_bird", "night_owl", "weekend_warrior",
        "perfect_five", "ten_in_a_row", "twenty_in_a_row", "fifty_in_a_row",
        "morning_streak_5",
        "lunch_learner", "lunch_master", "late_night_hero",
        "weekend_regular_2", "weekend_master_8", "morning_streak_14",
    }

    expected_categories = COUNT_BADGES | EFFORT_BADGES | STREAK_BADGES | CONTEXT_BADGES
    assert expected_categories == EXPECTED_BADGES, (
        f"category mismatch:\n"
        f"  missing: {expected_categories - EXPECTED_BADGES}\n"
        f"  extra:   {EXPECTED_BADGES - expected_categories}"
    )
    # Sprint 3.12: ровно 15 в каждой категории.
    assert len(COUNT_BADGES) == 15, f"count != 15: {len(COUNT_BADGES)}"
    assert len(EFFORT_BADGES) == 15, f"effort != 15: {len(EFFORT_BADGES)}"
    assert len(STREAK_BADGES) == 15, f"streak != 15: {len(STREAK_BADGES)}"
    assert len(CONTEXT_BADGES) == 15, f"context != 15: {len(CONTEXT_BADGES)}"


def test_seed_one_awards_single_badge(db_session):
    """seed_one выдаёт только один конкретный бейдж."""
    from app.student.models import UserBadge

    user_id = _make_user(db_session, "single-test@example.com")

    ok = seed_one(db_session, user_id, "streak_7")
    assert ok is True

    rows = db_session.query(UserBadge).filter(UserBadge.user_id == user_id).all()
    assert len(rows) == 1
    assert rows[0].badge_slug == "streak_7"
    # Evidence должен быть валидным JSON.
    evidence = json.loads(rows[0].evidence_json)
    assert "streak_days" in evidence


def test_seed_one_returns_false_for_already_awarded(db_session):
    """Повторный seed_one → False (бейдж уже есть)."""
    user_id = _make_user(db_session, "double-seed-test@example.com")

    assert seed_one(db_session, user_id, "perfect_five") is True
    assert seed_one(db_session, user_id, "perfect_five") is False


def test_seed_all_with_evdence_contains_required_keys(db_session):
    """Каждый бейдж получает осмысленный evidence (ключи из SEED_EVIDENCE)."""
    user_id = _make_user(db_session, "evidence-test@example.com")
    seed_all(db_session, user_id)

    from app.student.models import UserBadge

    rows = db_session.query(UserBadge).filter(UserBadge.user_id == user_id).all()
    for row in rows:
        evidence = json.loads(row.evidence_json)
        # Должен содержать хотя бы один ключ (slug → ключ evidence).
        assert len(evidence) >= 1, f"badge {row.badge_slug} has empty evidence: {evidence}"
        # Все значения evidence должны быть JSON-serializable.
        json.dumps(evidence)

