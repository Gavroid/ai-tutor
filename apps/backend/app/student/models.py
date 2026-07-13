"""Модели модуля student: черновики уроков, баджи (Sprint 7.5)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


class BadgeDefinition(Base):
    """Каталог баджей (Sprint 7.5). Seed-таблица, обновляется при выпуске новых баджей."""

    __tablename__ = "badge_definitions"

    slug: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str] = mapped_column(String(20), nullable=False, default="🏆")
    criteria_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class UserBadge(Base):
    """Факт получения баджа (Sprint 7.5). UNIQUE(user_id, badge_slug) — без дублей."""

    __tablename__ = "user_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_slug", name="uq_user_badges"),
        Index("ix_user_badges_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    badge_slug: Mapped[str] = mapped_column(
        String(50), ForeignKey("badge_definitions.slug"), nullable=False
    )
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
