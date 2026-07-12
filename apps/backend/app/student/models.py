"""Модели модуля student: черновики уроков, баджи."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TopicDraft(Base):
    """Серверный черновик урока (Sprint 7.3).

    Хранится в JSON — произвольное состояние: сообщения, текущий exercise,
    ответы, время прерывания. Используется для автосохранения урока с
    фронта каждые ~5 сек (debounce).
    """

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
