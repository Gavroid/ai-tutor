"""Pilot Core Stage 1 — Phase 2 (P1.2.2): server-owned exercise instances.

Pilot Core не доверяет браузеру: `correct_answer` хранится на сервере,
клиент получает opaque `exercise_id` и не видит ответ до submit.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.users.models import BigIntPK


# Default exercise lifetime (TTL). Pилот: 60 минут.
DEFAULT_EXERCISE_TTL_MINUTES = 60


class GeneratedExerciseInstance(Base):
    """Server-side exercise instance.

    Хранит правильный ответ и контекст. Браузер получает только
    `to_safe_dict()` (без correct_answer/explanation) и opaque id.
    """

    __tablename__ = "generated_exercise_instances"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    # JSON-строка с options (или null для numeric/text).
    options_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Server-side truth — НИКОГДА не отдаётся клиенту до submit.
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="mock")
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False, default="pilot-1")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Submission state — NULL пока submit не было.
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    submission_score: Mapped[float | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("ix_gei_owner_created", "owner_id", "created_at"),
    )

    def __init__(self, **kwargs: object) -> None:
        # Авто-проставление expires_at если не передано явно.
        if "expires_at" not in kwargs:
            kwargs["expires_at"] = datetime.now(timezone.utc) + timedelta(
                minutes=DEFAULT_EXERCISE_TTL_MINUTES
            )
        super().__init__(**kwargs)

    @property
    def is_expired(self) -> bool:
        expires = self.expires_at
        if expires is None:
            return False
        # SQLite возвращает naive datetime даже для DateTime(timezone=True).
        # Нормализуем к UTC для сравнения с datetime.now(timezone.utc).
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= expires

    @property
    def is_submitted(self) -> bool:
        return self.submitted_at is not None

    def to_safe_dict(self) -> dict[str, object]:
        """Opaque projection для браузера. НЕ содержит correct_answer/explanation.

        После submit (P1.2.3) endpoint сам формирует feedback + explanation;
        на этом уровне данные в safe dict остаются минимальными.
        """
        return {
            "exercise_id": self.id,
            "question_text": self.question_text,
            "type": self.type,
            "options": self._options_as_list(),
            "difficulty": self.difficulty,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    def _options_as_list(self) -> list[str] | None:
        if not self.options_json:
            return None
        import json

        try:
            parsed = json.loads(self.options_json)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except (ValueError, TypeError):
            return None
        return None
