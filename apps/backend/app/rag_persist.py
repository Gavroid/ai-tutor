"""Sprint 8.3 — persistence слой для RAG.

In-memory хранилище (`app/rag.py`) переживает только время работы backend.
Sprint 8.3: добавляем БД-persistence через таблицу `rag_chunks`
(миграция 0012).

Особенности:
- Embeddings хранятся как JSON (list[float] через json.dumps).
- Hash-ключ sha256(material_id + text) даёт идемпотентность: повторный index
  одного и того же материала НЕ дублирует чанки.
- При недоступности БД — fallback на in-memory dict (`app.rag._store`).
- Embedding cache: `get_or_compute_embedding(text)` — если для текста уже
  есть embedding в кэше, возвращает его; иначе вычисляет через API.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "384"))
EMBEDDING_CACHE_ENABLED = os.environ.get("EMBEDDING_CACHE_ENABLED", "1") == "1"


def chunk_hash(material_id: int, text: str) -> str:
    """Стабильный ключ чанка (sha256 hex)."""
    raw = f"{material_id}:{text}".encode()
    return hashlib.sha256(raw).hexdigest()


def text_hash(text: str) -> str:
    """Hash для embedding-кэша (по самому тексту, без material_id)."""
    return hashlib.sha256(text.encode()).hexdigest()


def embedding_to_json(vec: list[float]) -> str:
    """Embedding → JSON-строка для БД."""
    return json.dumps(vec)


def json_to_embedding(s: str) -> list[float]:
    """JSON-строка → embedding (с fallback на hash если повреждено)."""
    if not s:
        return []
    try:
        result = json.loads(s)
        if isinstance(result, list):
            return [float(x) for x in result]
    except (ValueError, TypeError):
        pass
    return []


def get_or_compute_embedding(text: str, *, db_session: Session | None = None) -> list[float]:
    """Sprint 8.3: получить embedding из кэша или вычислить через API.

    1. Если БД-кэш включён — ищем существующий embedding по hash(text).
    2. Если найден — возвращаем.
    3. Иначе — вычисляем через OpenAI-compatible /embeddings ИЛИ hash-fallback.
    4. Сохраняем в БД-кэш.

    Returns:
        Список float (384-dim).
    """
    if EMBEDDING_CACHE_ENABLED:
        th = text_hash(text)
        try:
            db = db_session or SessionLocal()
            from app.rag_models import EmbeddingCache  # local import чтобы не циклиться

            row = db.execute(
                select(EmbeddingCache).where(EmbeddingCache.text_hash == th)
            ).scalar_one_or_none()
            if row and row.embedding_json:
                cached = json_to_embedding(row.embedding_json)
                if cached:
                    logger.debug("Embedding cache HIT for %s", th[:12])
                    return cached
        except (SQLAlchemyError, Exception) as e:
            logger.warning("Embedding cache lookup failed: %s", e)

    # Compute
    vec = _compute_embedding(text)

    # Save to cache
    if EMBEDDING_CACHE_ENABLED and vec:
        try:
            from app.rag_models import EmbeddingCache

            db = db_session or SessionLocal()
            existing = db.execute(
                select(EmbeddingCache).where(EmbeddingCache.text_hash == text_hash(text))
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    EmbeddingCache(
                        text_hash=text_hash(text),
                        text=text[:500],
                        embedding_json=embedding_to_json(vec),
                        dim=len(vec),
                    )
                )
                db.commit()
        except (SQLAlchemyError, Exception) as e:
            logger.warning("Embedding cache save failed: %s", e)

    return vec


def _compute_embedding(text: str) -> list[float]:
    """Вычислить embedding через OpenAI-compatible API или hash-fallback."""
    base_url = os.environ.get("AI_BASE_URL", "https://api.openrouter.ai/api/v1").rstrip("/")
    api_key = os.environ.get("AI_API_KEY", "").strip()
    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

    if not api_key:
        # Hash fallback (MiniMax без /embeddings)
        return _hash_embedding(text, dim=EMBEDDING_DIM)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "input": text[:8000]}

    try:
        import asyncio

        async def _fetch():
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(f"{base_url}/embeddings", headers=headers, json=payload)
                if r.status_code != 200:
                    return None
                return r.json()

        data = asyncio.run(_fetch())
        if data:
            if "data" in data and isinstance(data["data"], list) and data["data"]:
                return data["data"][0].get("embedding") or _hash_embedding(text, dim=EMBEDDING_DIM)
            if "embedding" in data:
                return data["embedding"]
    except Exception as e:
        logger.warning("Embedding API call failed: %s, fallback to hash", e)

    return _hash_embedding(text, dim=EMBEDDING_DIM)


def _hash_embedding(text: str, dim: int = 384) -> list[float]:
    """Детерминированный псевдо-embedding для тестов и fallback."""
    text_normalized = text.lower().strip()
    h = hashlib.sha256(text_normalized.encode()).digest()
    vec = []
    for i in range(dim):
        b = h[(i * 4) % len(h):(i * 4) % len(h) + 4].ljust(4, b"\x00")
        val = int.from_bytes(b, "big", signed=False)
        vec.append((val / 2**31) - 1.0)
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec
