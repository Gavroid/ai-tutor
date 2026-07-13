"""Sprint 8.3 — модель для кэша embedding'ов в БД.

Отдельная таблица `embedding_cache`:
  text_hash: SHA-256 hex полного текста (unique)
  text: усечённый текст (для отладки, <= 500 символов)
  embedding_json: JSON list[float] (например, 384-dim vector)
  dim: длина вектора (sanity check)
  created_at: когда вычислили
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"

    text_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[str] = mapped_column(Text, nullable=False)
    dim: Mapped[int] = mapped_column(Integer, nullable=False, default=384)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
