"""Sprint 34 — Session pause SQLAlchemy model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.users.models import BigIntPK


class SessionPause(Base):
    """Sprint 34 — запись pause events от ребёнка.

    T1D-friendly: НЕ интерпретирует glucose data.
    Используется для parent dashboard и analytics.
    """

    __tablename__ = "session_pauses"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[int | None] = mapped_column(
        BigIntPK, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # break | hypo | hyper | other (matches PauseButton reasons)
    reason: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )