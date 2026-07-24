"""Sprint 40: CGMConfig ORM model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CGMConfig(Base):
    """Sprint 40: CGM (Continuous Glucose Monitor) opt-in config per user.

    T1D safety: ВСЕ glucose readings проксируются напрямую из Nightscout.
    В БД НЕ сохраняются glucose values — только URL и opt-in flag.
    """

    __tablename__ = "cgm_configs"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    nightscout_url: Mapped[str] = mapped_column(String(500), nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )