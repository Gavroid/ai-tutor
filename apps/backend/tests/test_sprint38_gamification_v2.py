"""Sprint 3.8 — gamification v2: 10 новых бейджей.

Покрывает:
- streak_3 / streak_7 / streak_30 (только положительные)
- returned_after_pause (НЕ штраф за паузу — позитив)
- polymath_week (3+ предмета за 7 дней)
- early_bird / night_owl (time-of-day по локальному TZ)
- weekend_warrior
- perfect_five / ten_in_a_row (consecutive correct)

T1D-friendly гарантии:
- streak=0 → streak_* НЕ вручаются, но и никаких негативных бейджей
- пропуск 2+ дней → returned_after_pause вручается (поощрение)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.db.session import Base, SessionLocal, engine
from app.progress import models as prog_models
from app.student.badges import (
    BADGES,
    collect_stats,
    evaluate_and_award_badges,
    seed_badge_definitions,
)
from app.student.models import BadgeDefinition
from app.subjects import models as subj_models
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def db_with_student_and_subjects():
    """Создаёт чистую БД со студентом, 3 предметами и topics."""
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        student = user_service.register_user(
            db,
            UserCreate(
                email="gami-kid@example.com",
                password="strongpass1",
                display_name="GamiKid",
                role="student",
                grade=7,
            ),
        )
        db.commit()
        # 3 предмета × 2 топика для diversity теста
        for s_idx in range(3):
            subj = subj_models.Subject(
                code=f"subj-{s_idx}",
                name=f"Предмет {s_idx}",
                recommended_grade=7,
            )
            db.add(subj)
            db.flush()
            sec = subj_models.Section(
                subject_id=subj.id,
                name="Sec",
                order_index=1,
            )
            db.add(sec)
            db.flush()
            for t_idx in range(2):
                db.add(
                    subj_models.Topic(
                        section_id=sec.id,
                        name=f"Topic {s_idx}-{t_idx}",
                        order_index=t_idx,
                    )
                )
        db.commit()
        yield {"db": db, "student_id": student.id}
    finally:
        db.close()


def _add_attempt(db, student_id, topic_id, is_correct, when_utc: datetime):
    """Создаёт Attempt с заданным created_at (UTC).

    Question_text / user_answer / correct_answer — NOT NULL по схеме.
    Заполняем фейковыми значениями (для теста важно только is_correct + timestamp).
    """
    a = prog_models.Attempt(
        user_id=student_id,
        topic_id=topic_id,
        question_text="(test) what is X?",
        user_answer="42" if is_correct else "wrong",
        correct_answer="42",
        is_correct=is_correct,
        score=1.0 if is_correct else 0.0,
        created_at=when_utc,
    )
    db.add(a)
    db.commit()


def _all_topics(db) -> list:
    return db.query(subj_models.Topic).all()


# ============== Catalog tests ==============

class TestCatalogV2:
    def test_catalog_has_60_badges_total(self, db_with_student_and_subjects):
        # Sprint 3.12: 20 (7.5+3.8) → 44 (3.11) → 60 (3.12): 15 на категорию.
        assert len(BADGES) == 60

    def test_catalog_new_badges_seeded(self, db_with_student_and_subjects):
        db = db_with_student_and_subjects["db"]
        n = seed_badge_definitions(db)
        slugs = {b.slug for b in db.query(BadgeDefinition).all()}
        new_slugs = {
            "streak_3", "streak_7", "streak_30",
            "returned_after_pause", "polymath_week",
            "early_bird", "night_owl", "weekend_warrior",
            "perfect_five", "ten_in_a_row",
        }
        assert new_slugs.issubset(slugs), f"missing: {new_slugs - slugs}"

    def test_new_badges_have_t1d_friendly_criteria(self, db_with_student_and_subjects):
        """Критерий не должен включать negative language."""
        for b in BADGES:
            for k in b.criteria.keys():
                # Не должно быть 'penalty' / 'streak_lost' / etc.
                assert "lost" not in k, f"{b.slug} has '{k}'"
                assert "penalty" not in k, f"{b.slug} has '{k}'"


# ============== streak_* tests ==============

class TestStreakBadges:
    def test_streak_3_after_three_consecutive_days(
        self, db_with_student_and_subjects,
    ):
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        topics = _all_topics(db)
        # Сегодня вчера позавчера (UTC для простоты)
        # Europe/Moscow default TZ — текущая дата в UTC близка к MSK (разница ≤3ч).
        today_utc = datetime.now(timezone.utc)
        for d in [2, 1, 0]:  # 3 дня подряд, последний — сегодня
            ts = today_utc - timedelta(days=d)
            _add_attempt(db, sid, topics[0].id, True, ts)
        awarded = evaluate_and_award_badges(db, sid)
        assert "streak_3" in awarded

    def test_streak_7_requires_7_days(self, db_with_student_and_subjects):
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        topics = _all_topics(db)
        today_utc = datetime.now(timezone.utc)
        # Только 6 дней — streak_7 НЕ должен вручиться
        for d in range(6):
            _add_attempt(db, sid, topics[0].id, True, today_utc - timedelta(days=d))
        awarded = evaluate_and_award_badges(db, sid)
        assert "streak_3" in awarded
        assert "streak_7" not in awarded


# ============== returned_after_pause ==============

class TestReturnedAfterPause:
    def test_returned_after_2day_pause(self, db_with_student_and_subjects):
        """2+ дня пропуска → бадж 'Возвращение' (НЕ штраф)."""
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        topics = _all_topics(db)
        today_utc = datetime.now(timezone.utc)
        # Попытка 5 дней назад и сегодня
        _add_attempt(db, sid, topics[0].id, True, today_utc - timedelta(days=5))
        _add_attempt(db, sid, topics[0].id, True, today_utc)
        awarded = evaluate_and_award_badges(db, sid)
        assert "returned_after_pause" in awarded

    def test_no_badge_if_no_pause(self, db_with_student_and_subjects):
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        topics = _all_topics(db)
        today_utc = datetime.now(timezone.utc)
        # Все попытки сегодня и вчера — паузы не было
        _add_attempt(db, sid, topics[0].id, True, today_utc)
        _add_attempt(db, sid, topics[0].id, True, today_utc - timedelta(days=1))
        awarded = evaluate_and_award_badges(db, sid)
        assert "returned_after_pause" not in awarded


# ============== polymath_week ==============

class TestPolymath:
    def test_three_subjects_in_seven_days(self, db_with_student_and_subjects):
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        # Берём topics из разных subjects (по 1 из каждого)
        subj1_topic = db.query(subj_models.Topic).filter(
            subj_models.Topic.name == "Topic 0-0"
        ).first()
        subj2_topic = db.query(subj_models.Topic).filter(
            subj_models.Topic.name == "Topic 1-0"
        ).first()
        subj3_topic = db.query(subj_models.Topic).filter(
            subj_models.Topic.name == "Topic 2-0"
        ).first()
        today_utc = datetime.now(timezone.utc)
        # 3 разных предмета в разные дни за последнюю неделю
        _add_attempt(db, sid, subj1_topic.id, True, today_utc - timedelta(days=1))
        _add_attempt(db, sid, subj2_topic.id, True, today_utc - timedelta(days=3))
        _add_attempt(db, sid, subj3_topic.id, True, today_utc)
        awarded = evaluate_and_award_badges(db, sid)
        assert "polymath_week" in awarded

    def test_one_subject_no_polymath(self, db_with_student_and_subjects):
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        topics = _all_topics(db)
        # Берём только topics из одного subject (Topic 0-0 и Topic 0-1)
        same_subj_topics = db.query(subj_models.Topic).filter(
            subj_models.Topic.name.in_(["Topic 0-0", "Topic 0-1"])
        ).all()
        today_utc = datetime.now(timezone.utc)
        for t in same_subj_topics:
            _add_attempt(db, sid, t.id, True, today_utc)
        awarded = evaluate_and_award_badges(db, sid)
        assert "polymath_week" not in awarded


# ============== time-of-day ==============

class TestTimeOfDay:
    def test_morning_attempt_awards_early_bird(self, db_with_student_and_subjects):
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        topics = _all_topics(db)
        # 08:00 UTC → в MSK 11:00 — НЕ утро (07-10 MSK)
        # Используем 04:00 UTC = 07:00 MSK (граница)
        ts = datetime.now(timezone.utc).replace(hour=4, minute=0, second=0, microsecond=0)
        _add_attempt(db, sid, topics[0].id, True, ts)
        awarded = evaluate_and_award_badges(db, sid)
        assert "early_bird" in awarded
        assert "night_owl" not in awarded

    def test_evening_attempt_awards_night_owl(self, db_with_student_and_subjects):
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        topics = _all_topics(db)
        # 19:00 UTC = 22:00 MSK → evening
        ts = datetime.now(timezone.utc).replace(hour=19, minute=0, second=0, microsecond=0)
        _add_attempt(db, sid, topics[0].id, True, ts)
        awarded = evaluate_and_award_badges(db, sid)
        assert "night_owl" in awarded
        assert "early_bird" not in awarded


# ============== weekend_warrior ==============

class TestWeekend:
    def test_saturday_attempt_awards_weekend_warrior(
        self, db_with_student_and_subjects,
    ):
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        topics = _all_topics(db)
        # Найдём ближайшую субботу в UTC
        today = datetime.now(timezone.utc)
        days_to_sat = (5 - today.weekday()) % 7
        if days_to_sat == 0 and today.weekday() != 5:
            days_to_sat = 7
        sat = today - timedelta(days=today.weekday() - 5) if today.weekday() >= 5 else today + timedelta(days=days_to_sat)
        sat_noon = sat.replace(hour=12, minute=0, second=0, microsecond=0)
        _add_attempt(db, sid, topics[0].id, True, sat_noon)
        awarded = evaluate_and_award_badges(db, sid)
        assert "weekend_warrior" in awarded


# ============== consecutive_correct ==============

class TestConsecutiveCorrect:
    def test_five_correct_awards_perfect_five(self, db_with_student_and_subjects):
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        topics = _all_topics(db)
        today_utc = datetime.now(timezone.utc)
        for i in range(5):
            _add_attempt(db, sid, topics[0].id, True, today_utc - timedelta(minutes=i))
        awarded = evaluate_and_award_badges(db, sid)
        assert "perfect_five" in awarded

    def test_ten_correct_awards_both(self, db_with_student_and_subjects):
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        topics = _all_topics(db)
        today_utc = datetime.now(timezone.utc)
        for i in range(10):
            _add_attempt(db, sid, topics[0].id, True, today_utc - timedelta(minutes=i))
        awarded = evaluate_and_award_badges(db, sid)
        assert "perfect_five" in awarded
        assert "ten_in_a_row" in awarded

    def test_broken_streak_no_perfect_five(self, db_with_student_and_subjects):
        """3 правильных + 1 ошибка + 3 правильных = НЕ 5 подряд → perfect_five НЕ вручается."""
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        topics = _all_topics(db)
        today_utc = datetime.now(timezone.utc)
        # 3 correct
        for i in range(3):
            _add_attempt(db, sid, topics[0].id, True, today_utc - timedelta(minutes=10 + i))
        # 1 incorrect
        _add_attempt(db, sid, topics[0].id, False, today_utc - timedelta(minutes=8))
        # 3 correct
        for i in range(3):
            _add_attempt(db, sid, topics[0].id, True, today_utc - timedelta(minutes=5 + i))
        awarded = evaluate_and_award_badges(db, sid)
        assert "perfect_five" not in awarded


# ============== Idempotency / no regressions ==============

class TestIdempotency:
    def test_double_evaluate_does_not_double_award(
        self, db_with_student_and_subjects,
    ):
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        topics = _all_topics(db)
        today_utc = datetime.now(timezone.utc)
        for i in range(5):
            _add_attempt(db, sid, topics[0].id, True, today_utc - timedelta(minutes=i))
        first = evaluate_and_award_badges(db, sid)
        second = evaluate_and_award_badges(db, sid)
        # Второй вызов НЕ должен выдать повторно
        assert "perfect_five" in first
        assert "perfect_five" not in second

    def test_old_badges_still_work(self, db_with_student_and_subjects):
        """Регрессия: 10 старых бейджей Sprint 7.5 не сломаны."""
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        topics = _all_topics(db)
        today_utc = datetime.now(timezone.utc)
        _add_attempt(db, sid, topics[0].id, True, today_utc)
        awarded = evaluate_and_award_badges(db, sid)
        # Старые бейджи всё ещё работают
        assert "first_step" in awarded
        assert "asked_question" in awarded
        assert "explained_in_own_words" in awarded


# ============== Stats API ==============

class TestCollectStats:
    def test_collect_stats_returns_v2_fields(self, db_with_student_and_subjects):
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        stats = collect_stats(db, sid)
        assert "current_streak_days" in stats
        assert "returned_after_pause" in stats
        assert "subjects_in_last_7d" in stats
        assert "morning_attempt" in stats
        assert "evening_attempt" in stats
        assert "weekend_attempt" in stats
        assert "max_consecutive_correct" in stats
        # Backward compat: старые поля тоже есть
        assert "total_attempts" in stats
        assert "max_mastery" in stats

    def test_collect_stats_no_attempts_returns_zeros(
        self, db_with_student_and_subjects,
    ):
        db = db_with_student_and_subjects["db"]
        sid = db_with_student_and_subjects["student_id"]
        stats = collect_stats(db, sid)
        assert stats["current_streak_days"] == 0
        assert stats["returned_after_pause"] == 0
        assert stats["subjects_in_last_7d"] == 0
        assert stats["morning_attempt"] == 0
        assert stats["evening_attempt"] == 0
        assert stats["weekend_attempt"] == 0
        assert stats["max_consecutive_correct"] == 0
