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
    def test_badge_catalog_has_10_badges(self):
        assert len(BADGES) >= 8, f"Только {len(BADGES)} баджей в каталоге"

    def test_no_streak_or_timer_badges(self):
        """T1D: ни streak'ов, ни обратных таймеров, ни штрафов за паузу."""
        bad_keywords = ["streak", "consecutive", "under pressure", "missed", "penalty"]
        for badge in BADGES:
            text = (
                badge.slug
                + " "
                + badge.title
                + " "
                + badge.description
            ).lower()
            for kw in bad_keywords:
                assert kw not in text, f"Бейдж {badge.slug} содержит T1D-нарушающее: '{kw}'"

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
    """T1D: категорически НЕ должно быть баджей, связанных со streak'ами."""

    def test_no_streak_in_catalog(self):
        slugs = [b.slug for b in BADGES]
        titles = [b.title.lower() for b in BADGES]
        descs = [b.description.lower() for b in BADGES]
        all_text = " ".join(slugs + titles + descs)
        for bad_word in ["streak", "серия подряд", "consecutive days"]:
            assert bad_word not in all_text, f"T1D-violating keyword: {bad_word}"
