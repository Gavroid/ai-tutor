"""Модели модуля student: черновики уроков, баджи (Sprint 7.5)."""

from __future__ import annotations

from datetime import UTC, datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TopicDraft(Base):
    """Серверный черновик урока (Sprint 7.3)."""

    __tablename__ = "topic_drafts"
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_topic_drafts_user_topic"),
        Index("ix_topic_drafts_user", "user_id"),
        Index("ix_topic_drafts_topic", "topic_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(Integer, ForeignKey("topics.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class BadgeDefinition(Base):
    """Каталог баджей (Sprint 7.5). Seed-таблица, обновляется при выпуске новых баджей."""

    __tablename__ = "badge_definitions"

    slug: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str] = mapped_column(String(20), nullable=False, default="🏆")
    criteria_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class UserCounter(Base):
    """Sprint 3.15: честные счётчики для бейджей all_basics / asked_question.

    Раньше `collect_stats()` использовал proxy `easy_solved = total`, `questions_to_ai = total`
    — бейджи выдавались нечестно. Теперь счётчики инкрементятся:
      - easy_solved: каждый correct v2 answer при inst.difficulty <= 2
      - questions_to_ai: каждый успешный POST /api/v1/ai/chat

    Счётчики стартуют с 0 (ретро-бэкфилл НЕ делается). Уже выданные бейджи НЕ отзываются.
    """

    __tablename__ = "user_counters"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    easy_solved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    questions_to_ai: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class UserBadge(Base):
    """Факт получения баджа (Sprint 7.5). UNIQUE(user_id, badge_slug) — без дублей."""

    __tablename__ = "user_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_slug", name="uq_user_badges"),
        Index("ix_user_badges_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    badge_slug: Mapped[str] = mapped_column(String(50), ForeignKey("badge_definitions.slug"), nullable=False)
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
