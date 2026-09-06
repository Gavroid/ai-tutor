"""Sprint 4.2: тесты для mastery thresholds и get_review_topics.

Решение владельца (audit 2026-09-05, зафиксировано в
audit-2026-09/13-session-2026-09-04-blocked-decisions.md):
- weak_topics:    mastery < 0.60 (60%)
- review_topics:  top-5 тем с наиболее старым last_reviewed_at
- NULL last_reviewed_at IS NULL трактуется как "никогда не повторяли"
- Сортировка детерминированная: NULLs first, затем ASC, tie-breaker по topic_id
- Пересечение weak ∩ review РАЗРЕШЕНО

Подход к изоляции БД (Sprint 3.43 P1 lesson learned):
- Отдельный StaticPool in-memory engine для теста
- monkeypatch SessionLocal чтобы get_review_topics использовал нашу БД
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.parents.schemas import ReviewTopic
from app.parents.service import (
    REVIEW_TOPICS_LIMIT,
    WEAK_MASTERY_THRESHOLD,
    get_review_topics,
)
from app.progress import models as prog_models
from app.subjects import models as subj_models
from app.users import models as user_models
from datetime import UTC, datetime, timedelta

# Sprint 4.2: отдельный engine для изоляции от xdist races (Sprint 3.43 P1 lesson).
# get_review_topics принимает db: Session параметром, НЕ использует SessionLocal,
# поэтому monkeypatch не нужен — каждый тест создаёт свой session через _TestSessionLocal.
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(_test_engine)
_TestSessionLocal = sessionmaker(bind=_test_engine)


def _create_topic_with_progress(
    slug: str,
    mastery: float = 0.5,
    last_reviewed_at: datetime | None = None,
    attempts: int = 1,
) -> int:
    """Создаёт user/subject/section/topic + Progress. Возвращает user_id."""
    session = _TestSessionLocal()
    try:
        user = user_models.User(
            email=f"{slug}@example.com",
            password_hash="x",
            role=user_models.Role.STUDENT,
            display_name="Test",
        )
        session.add(user)
        session.flush()

        subject = subj_models.Subject(
            name=f"Subj {slug}", code=slug, is_active=True
        )
        session.add(subject)
        session.flush()

        section = subj_models.Section(
            subject_id=subject.id, name="S", order_index=1
        )
        session.add(section)
        session.flush()

        topic = subj_models.Topic(section_id=section.id, name=f"Topic {slug}", order_index=1)
        session.add(topic)
        session.flush()

        progress = prog_models.Progress(
            user_id=user.id,
            topic_id=topic.id,
            mastery_score=mastery,
            attempts_count=attempts,
            last_reviewed_at=last_reviewed_at,
        )
        session.add(progress)
        session.commit()
        return user.id
    finally:
        session.close()


@pytest.fixture
def test_db():
    """Sprint 4.2: возвращает Session для test (привязан к нашему _test_engine)."""
    return _TestSessionLocal()


class TestSprint42MasteryThresholdConstants:
    """Sprint 4.2: константы thresholds зафиксированы."""

    def test_weak_threshold_is_60_percent(self, test_db) -> None:
        assert WEAK_MASTERY_THRESHOLD == 0.60

    def test_review_topics_limit_is_5(self, test_db) -> None:
        assert REVIEW_TOPICS_LIMIT == 5


class TestSprint42GetReviewTopics:
    """Sprint 4.2: get_review_topics behavior contract."""

    def test_returns_empty_for_no_progress(self, test_db) -> None:
        """Пустая БД → пустой результат."""
        result = get_review_topics(test_db, student_id=99999)
        assert result == []

    def test_returns_max_5_topics(self, test_db) -> None:
        """Если 10 тем с Progress — возвращаем top-5."""
        user_id = _create_topic_with_progress(
            f"max5-{i}", mastery=0.5, last_reviewed_at=datetime(2024, 1, i + 1, tzinfo=UTC)
        ) if False else None  # placeholder, replaced below
        # Создаём 10 разных topics для одного user.
        session = _TestSessionLocal()
        try:
            user = user_models.User(
                email="max5@example.com",
                password_hash="x",
                role=user_models.Role.STUDENT,
                display_name="Test",
            )
            session.add(user)
            session.flush()

            subject = subj_models.Subject(
                name="Subj", code="max5", is_active=True
            )
            session.add(subject)
            session.flush()

            section = subj_models.Section(
                subject_id=subject.id, name="S", order_index=1
            )
            session.add(section)
            session.flush()

            # 10 тем с разными last_reviewed_at (от 2024-01-01 до 2024-01-10).
            for i in range(10):
                topic = subj_models.Topic(
                    section_id=section.id,
                    name=f"Topic {i}",
                    order_index=i + 1,
                )
                session.add(topic)
                session.flush()
                progress = prog_models.Progress(
                    user_id=user.id,
                    topic_id=topic.id,
                    mastery_score=0.5,
                    attempts_count=1,
                    last_reviewed_at=datetime(2024, 1, i + 1, tzinfo=UTC),
                )
                session.add(progress)
            session.commit()
            user_id = user.id
        finally:
            session.close()

        result = get_review_topics(test_db, student_id=user_id)

        assert len(result) == REVIEW_TOPICS_LIMIT, (
            f"Expected {REVIEW_TOPICS_LIMIT} topics, got {len(result)}"
        )

    def test_nulls_last_reviewed_at_first(self, test_db) -> None:
        """Sprint 4.2=A: NULL last_reviewed_at трактуется как "никогда не повторяли"
        → попадают первыми в review_topics."""
        session = _TestSessionLocal()
        try:
            user = user_models.User(
                email="nullsfirst@example.com",
                password_hash="x",
                role=user_models.Role.STUDENT,
                display_name="Test",
            )
            session.add(user)
            session.flush()

            subject = subj_models.Subject(
                name="S", code="nullsfirst", is_active=True
            )
            session.add(subject)
            session.flush()

            section = subj_models.Section(
                subject_id=subject.id, name="S", order_index=1
            )
            session.add(section)
            session.flush()

            # Topic 1: last_reviewed_at = None (никогда не повторяли)
            topic1 = subj_models.Topic(section_id=section.id, name="NULL", order_index=1)
            session.add(topic1)
            session.flush()
            p1 = prog_models.Progress(
                user_id=user.id,
                topic_id=topic1.id,
                mastery_score=0.5,
                attempts_count=1,
                last_reviewed_at=None,
            )
            session.add(p1)

            # Topic 2: last_reviewed_at = 2024-01-01 (старая)
            topic2 = subj_models.Topic(section_id=section.id, name="OLD", order_index=2)
            session.add(topic2)
            session.flush()
            p2 = prog_models.Progress(
                user_id=user.id,
                topic_id=topic2.id,
                mastery_score=0.5,
                attempts_count=1,
                last_reviewed_at=datetime(2024, 1, 1, tzinfo=UTC),
            )
            session.add(p2)

            # Topic 3: last_reviewed_at = 2024-12-01 (новая)
            topic3 = subj_models.Topic(section_id=section.id, name="NEW", order_index=3)
            session.add(topic3)
            session.flush()
            p3 = prog_models.Progress(
                user_id=user.id,
                topic_id=topic3.id,
                mastery_score=0.5,
                attempts_count=1,
                last_reviewed_at=datetime(2024, 12, 1, tzinfo=UTC),
            )
            session.add(p3)
            session.commit()
            user_id = user.id
        finally:
            session.close()

        result = get_review_topics(test_db, student_id=user_id)

        # Ожидаем порядок: NULL, OLD (2024-01-01), NEW (2024-12-01).
        assert result[0].topic_name == "NULL", (
            f"First should be NULL (never reviewed), got {result[0].topic_name}"
        )
        assert result[0].last_reviewed_at is None
        assert result[1].topic_name == "OLD"
        assert result[1].last_reviewed_at is not None, (
            "OLD topic должен иметь last_reviewed_at (не NULL)"
        )
        # Sprint 4.2: SQLite strips tzinfo при round-trip, сравниваем по date().
        assert result[1].last_reviewed_at.date() == datetime(2024, 1, 1, tzinfo=UTC).date()
        assert result[2].topic_name == "NEW"
        assert result[2].last_reviewed_at is not None
        assert result[2].last_reviewed_at.date() == datetime(2024, 12, 1, tzinfo=UTC).date()

    def test_returns_review_topic_schema(self, test_db) -> None:
        """Каждый элемент — ReviewTopic schema с правильными полями."""
        user_id = _create_topic_with_progress(
            "schema-test", mastery=0.5, last_reviewed_at=datetime(2024, 6, 1, tzinfo=UTC)
        )

        result = get_review_topics(test_db, student_id=user_id)

        assert len(result) >= 1
        for topic in result:
            assert isinstance(topic, ReviewTopic)
            assert 0.0 <= topic.mastery <= 1.0

    def test_includes_topics_with_high_mastery(self, test_db) -> None:
        """Sprint 4.2=A: review_topics включают темы с mastery >= 60%
        (если они давно не повторялись). Пересечение с weak РАЗРЕШЕНО."""
        session = _TestSessionLocal()
        try:
            user = user_models.User(
                email="high-mastery@example.com",
                password_hash="x",
                role=user_models.Role.STUDENT,
                display_name="Test",
            )
            session.add(user)
            session.flush()

            subject = subj_models.Subject(name="S", code="highm", is_active=True)
            session.add(subject)
            session.flush()

            section = subj_models.Section(
                subject_id=subject.id, name="S", order_index=1
            )
            session.add(section)
            session.flush()

            # Topic с mastery=0.9 (high) и last_reviewed_at = NULL (никогда).
            topic = subj_models.Topic(
                section_id=section.id, name="HIGH_MASTERY", order_index=1
            )
            session.add(topic)
            session.flush()
            p = prog_models.Progress(
                user_id=user.id,
                topic_id=topic.id,
                mastery_score=0.9,  # high — НЕ weak
                attempts_count=10,
                last_reviewed_at=None,  # never reviewed
            )
            session.add(p)
            session.commit()
            user_id = user.id
        finally:
            session.close()

        result = get_review_topics(test_db, student_id=user_id)

        assert len(result) == 1
        assert result[0].topic_name == "HIGH_MASTERY"
        assert result[0].mastery == 0.9, (
            "Sprint 4.2=A: review_topics должны включать темы с high mastery "
            "если они давно не повторялись (NULL)."
        )
        assert result[0].last_reviewed_at is None
