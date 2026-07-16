"""Sprint 8.3 — модели для БД-persistence RAG.

Две таблицы:
  embedding_cache: кэш вычисленных embedding'ов (text_hash → embedding_json).
                   Экономит расходы на embedding API, переиспользует.
  rag_chunks (Sprint 3.5.2): сами чанки материалов (для persistent search).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EmbeddingCache(Base):
    """Sprint 8.3: кэш embedding'ов.

    text_hash: SHA-256 hex полного текста (unique).
    text: усечённый текст (для отладки, <= 500 символов).
    embedding_json: JSON list[float] (например, 384-dim vector).
    dim: длина вектора (sanity check).
    """
    __tablename__ = "embedding_cache"

    text_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[str] = mapped_column(Text, nullable=False)
    dim: Mapped[int] = mapped_column(Integer, nullable=False, default=384)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class RagChunk(Base):
    """Sprint 3.5.2: persistent chunk для RAG.

    hash: sha256(material_id + ':' + text)[:16] — уникальный ключ
          (idempotent re-index одного материала).
    embedding_json: JSON list[float] (384-dim для hash-based fallback).
    metadata_json: JSON dict с material_title/page_number/etc.
    """
    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[str] = mapped_column(Text, nullable=False, server_default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)