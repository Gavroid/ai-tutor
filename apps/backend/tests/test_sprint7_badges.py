"""Sprint 7.5: баджи за усилие (НЕ за streak)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth.security import create_access_token
from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.progress import models as prog_models
from app.student.badges import (
    BADGES,
    award_badge,
    evaluate_and_award_badges,
    seed_badge_definitions,
)
from app.student.models import BadgeDefinition, UserBadge
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def new_student():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        student = user_service.register_user(
            db,
            UserCreate(
                email="badges-kid@example.com",
                password="strongpass1",
                display_name="BadgeKid",
                role="student",
                grade=7,
            ),
        )
        db.commit()
        token, _ = create_access_token(student)
        return {"student_id": student.id, "token": token}
    finally:
        db.close()


class TestBadgeCatalog:
    def test_badge_catalog_has_60_badges(self):
        # Sprint 3.12: 20 (7.5+3.8) → 44 (3.11) → 60 (3.12): 15 на категорию.
        assert len(BADGES) == 60, f"Ожидаем 60 (15×4 категории), получили {len(BADGES)}"

    def test_no_t1d_hostile_keywords(self):
        """T1D: ни штрафов, ни 'under pressure', ни 'missed' формулировок.

        Sprint 3.8 ДОБАВИЛ streak/consecutive бейджи, но они позитивные.
        Поэтому здесь проверяем ТОЛЬКО явно враждебные к T1D keywords,
        а не 'streak'/'consecutive' вообще.
        """
        bad_keywords = ["under pressure", "missed", "penalty", "lost"]
        for badge in BADGES:
            text = (
                badge.slug + " " + badge.title + " " + badge.description
            ).lower()
            for kw in bad_keywords:
                assert kw not in text, (
                    f"Бейдж {badge.slug} содержит T1D-нарушающее: '{kw}'"
                )

    def test_all_badges_have_unique_slugs(self):
        slugs = [b.slug for b in BADGES]
        assert len(slugs) == len(set(slugs)), "duplicate slugs"

    def test_all_badges_have_icon_and_desc(self):
        for b in BADGES:
            assert b.icon
            assert len(b.description) > 5
            assert len(b.title) > 2


class TestSeedBadgeDefinitions:
    def test_seed_is_idempotent(self, new_student):
        db = SessionLocal()
        try:
            n1 = seed_badge_definitions(db)
            n2 = seed_badge_definitions(db)
            assert n1 == len(BADGES)
            assert n2 == len(BADGES)
            count = db.query(BadgeDefinition).count()
            assert count == len(BADGES)
        finally:
            db.close()


class TestAwardBadge:
    def test_award_unique(self, new_student):
        db = SessionLocal()
        try:
            seed_badge_definitions(db)
            first = award_badge(db, new_student["student_id"], "first_step", {"x": 1})
            second = award_badge(db, new_student["student_id"], "first_step", {"x": 2})
            assert first is True
            assert second is False, "Дубликат не должен присуждаться"
        finally:
            db.close()

    def test_award_unknown_slug(self, new_student):
        db = SessionLocal()
        try:
            seed_badge_definitions(db)
            ok = award_badge(db, new_student["student_id"], "nonexistent-badge")
            assert ok is False
        finally:
            db.close()


class TestEvaluation:
    def test_no_attempts_no_badges(self, new_student):
        db = SessionLocal()
        try:
            seed_badge_definitions(db)
            awarded = evaluate_and_award_badges(db, new_student["student_id"], {
                "total_attempts": 0,
                "quality_5_no_hint": 0,
                "returned_to_incorrect": 0,
                "max_mastery": 0.0,
                "easy_solved": 0,
                "questions_to_ai": 0,
            })
            assert awarded == []
        finally:
            db.close()

    def test_one_attempt_first_step(self, new_student):
        db = SessionLocal()
        try:
            seed_badge_definitions(db)
            awarded = evaluate_and_award_badges(db, new_student["student_id"], {
                "total_attempts": 1,
                "quality_5_no_hint": 1,
                "returned_to_incorrect": 0,
                "max_mastery": 0.5,
                "easy_solved": 1,
                "questions_to_ai": 1,
            })
            assert "first_step" in awarded
            # Explaied_in_own_words требует quality_5
            assert "explained_in_own_words" in awarded
            # Нет streak'ов
            assert not any("streak" in a for a in awarded)
        finally:
            db.close()


class TestBadgesEndpoint:
    def test_get_badges_unauthenticated_401(self):
        c = TestClient(app)
        r = c.get("/api/v1/student/badges")
        assert r.status_code in (401, 403)

    def test_get_badges_returns_all(self, new_student):
        c = TestClient(app)
        token = new_student["token"]
        r = c.get(
            "/api/v1/student/badges",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        items = r.json()
        assert len(items) == len(BADGES)
        # Все НЕ получены initially (нет активности)
        assert all(item["awarded_at"] is None for item in items)

    def test_evaluate_endpoint_triggers(self, new_student):
        c = TestClient(app)
        token = new_student["token"]
        # Без активности
        r = c.post(
            "/api/v1/student/badges/evaluate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json() == []

        # Симулируем активность — добавим Attempt
        db = SessionLocal()
        try:
            attempt = prog_models.Attempt(
                user_id=new_student["student_id"],
                topic_id=1,
                question_text="q",
                user_answer="a",
                correct_answer="a",
                is_correct=True,
                score=1.0,
            )
            db.add(attempt)
            db.commit()
        finally:
            db.close()

        r = c.post(
            "/api/v1/student/badges/evaluate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        awarded = r.json()
        assert "first_step" in awarded
        assert "explained_in_own_words" in awarded
        assert "asked_question" in awarded


class TestBadgesNotStreak:
    """T1D: бейджи за streak существуют (Sprint 3.8), но ТОЛЬКО положительные.

    Здесь проверяем:
    - нет ключевых слов, означающих НАКАЗАНИЕ за пропуск
    - есть явные позитивные формулировки
    """

    def test_no_t1d_punitive_keywords(self):
        all_text = " ".join(
            [b.slug + " " + b.title.lower() + " " + b.description.lower() for b in BADGES]
        )
        for bad_word in ["штраф", "penalty", "lost your", "сгорела"]:
            assert bad_word not in all_text, f"T1D-punitive keyword: {bad_word}"

    def test_streak_badges_are_positive(self):
        """Sprint 3.8 streak_* бейджи должны поощрять, а не давить."""
        streak_slugs = {"streak_3", "streak_7", "streak_30", "returned_after_pause"}
        for badge in BADGES:
            if badge.slug in streak_slugs:
                # Каждый streak-бейдж должен иметь позитивную формулировку
                # (без "сгорела", "потерял" и т.п.)
                assert "сгорел" not in badge.description.lower()
                assert "потерял" not in badge.description.lower()
                assert "lost" not in badge.description.lower()
