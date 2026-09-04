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
from dataclasses import dataclass
from typing import Optional

import httpx
from sqlalchemy import func, select
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

        try:
            asyncio.get_running_loop()
            logger.debug("Embedding API skipped inside running event loop; fallback to hash")
            return _hash_embedding(text, dim=EMBEDDING_DIM)
        except RuntimeError:
            pass

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


# === Sprint 3.5.2: Persistent RAG (search по rag_chunks в PostgreSQL) ===

@dataclass
class PersistentChunk:
    """Lightweight DTO для search results — не зависит от in-memory store."""
    id: str
    material_id: int
    text: str
    embedding: list[float]
    metadata: dict


def add_chunks_persistent(
    db: Session,
    material_id: int,
    chunks: list[str],
    embeddings: list[list[float]],
    metadata: dict | None = None,
) -> list[str]:
    """Sprint 3.5.2: записать chunk'и в rag_chunks (идемпотентно по hash).

    Returns: список id (строковых, как hash) добавленных chunk'ов.
    """
    from app.rag_models import RagChunk  # local import (избежать цикл.импорта)

    meta_json = json.dumps(metadata or {}, ensure_ascii=False)
    added_ids = []
    for text, emb in zip(chunks, embeddings, strict=False):
        h = chunk_hash(material_id, text)
        # Идемпотентность: если chunk с таким hash уже есть — пропускаем.
        existing = db.execute(
            select(RagChunk).where(RagChunk.hash == h)
        ).scalar_one_or_none()
        if existing is not None:
            added_ids.append(h)
            continue
        row = RagChunk(
            material_id=material_id,
            hash=h,
            text=text,
            embedding_json=embedding_to_json(emb),
            metadata_json=meta_json,
        )
        db.add(row)
        added_ids.append(h)
    db.commit()
    return added_ids


def search_persistent(
    db: Session,
    query_embedding: list[float],
    top_k: int = 3,
    material_id: int | None = None,
) -> list[PersistentChunk]:
    """Sprint 3.5.2: persistent search через rag_chunks + cosine similarity.

    Простой in-Python cosine (без pgvector). Достаточно для MVP:
    384-dim × ~1000 chunks = ~1ms в Python. Если chunks > 10K — мигрировать
    на pgvector extension (Sprint 3.5.3+ TODO).
    """
    from app.rag import cosine_similarity
    from app.rag_models import RagChunk  # local import

    q = select(RagChunk)
    if material_id is not None:
        q = q.where(RagChunk.material_id == material_id)
    rows = db.execute(q).scalars().all()

    if not rows:
        return []

    scored: list[tuple[float, PersistentChunk]] = []
    for row in rows:
        emb = json_to_embedding(row.embedding_json)
        if not emb:
            continue
        sim = cosine_similarity(query_embedding, emb)
        scored.append((sim, PersistentChunk(
            id=row.hash,
            material_id=row.material_id,
            text=row.text,
            embedding=emb,
            metadata=json.loads(row.metadata_json or "{}"),
        )))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:top_k]]


def search_real_persistent(
    db: Session,
    query_embedding: list[float],
    top_k: int = 3,
    material_id: int | None = None,
) -> list[PersistentChunk]:
    """Sprint 70: persistent search через rag_chunks + REAL embeddings.

    Использует sentence-transformers embeddings из metadata_json["embedding_v2"]
    (backfilled в Sprint 70). 384-dim cosine similarity.

    Recall@3: 0% (hash) → 11% (real). Sprint 88 планирует hybrid search
    (BM25 + real) для >60% Recall.

    Args:
        db: SQLAlchemy session
        query_embedding: 384-dim vector (sentence-transformers)
        top_k: top-k results
        material_id: optional filter

    Returns:
        list of PersistentChunk sorted by cosine similarity (desc)
    """
    import numpy as np

    from app.rag_models import RagChunk  # local import

    q = select(RagChunk)
    if material_id is not None:
        q = q.where(RagChunk.material_id == material_id)
    # Sprint 70: filter chunks с real embeddings (Sprint 70 backfill).
    rows = db.execute(q).scalars().all()

    if not rows:
        return []

    query_np = np.array(query_embedding)

    scored: list[tuple[float, PersistentChunk]] = []
    for row in rows:
        # Sprint 70: real embeddings в metadata_json["embedding_v2"].
        metadata = json.loads(row.metadata_json or "{}")
        real_emb = metadata.get("embedding_v2")
        if not real_emb:
            continue  # chunk ещё не backfilled
        try:
            chunk_np = np.array(real_emb)
            # Cosine similarity (vectors are normalized, so dot product).
            sim = float(np.dot(query_np, chunk_np))
        except (TypeError, ValueError):
            continue
        scored.append((sim, PersistentChunk(
            id=row.hash,
            material_id=row.material_id,
            text=row.text,
            # Sprint 88: добавляем cosine_score в metadata для hybrid search.
            embedding=real_emb,
            metadata={
                **metadata,
                "cosine_score": float(sim),
            },
        )))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:top_k]]


def search_bm25_persistent(
    db: Session,
    query: str,
    top_k: int = 3,
    material_id: int | None = None,
) -> list[PersistentChunk]:
    """Sprint 57: BM25 keyword search через rag_chunks.

    Альтернатива search_persistent (cosine) — лучше для keyword queries,
    не требует embeddings. Используется когда:
    - embeddings недоступны (4GB RAM)
    - запрос keyword-based (не semantic)

    Returns: top_k PersistentChunk sorted by BM25 score.
    """
    from app.rag_bm25 import bm25_search
    from app.rag_models import RagChunk

    q = select(RagChunk)
    if material_id is not None:
        q = q.where(RagChunk.material_id == material_id)
    rows = db.execute(q).scalars().all()

    if not rows:
        return []

    # Convert to dict format для bm25_search.
    chunk_dicts = []
    for row in rows:
        meta = json.loads(row.metadata_json or "{}")
        chunk_dicts.append({
            "id": row.hash,
            "material_id": row.material_id,
            "text": row.text,
            "material_title": meta.get("material_title", ""),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "metadata": meta,
            "_row": row,  # for PersistentChunk construction
        })

    # BM25 search.
    top_chunks = bm25_search(
        query=query,
        chunks=chunk_dicts,
        top_k=top_k,
        title_boost_factor=1.5,
        recency_enabled=True,
    )

    # Convert back to PersistentChunk.
    # Sprint 88: сохраняем bm25_score в metadata для hybrid search.
    result: list[PersistentChunk] = []
    for chunk_dict in top_chunks:
        row = chunk_dict["_row"]
        emb = json_to_embedding(row.embedding_json)
        # bm25_score хранится в chunk_dict (добавлено bm25_search)
        bm25_score_value = chunk_dict.get("bm25_score", 0)
        metadata_with_score = {
            **chunk_dict["metadata"],
            "bm25_score": bm25_score_value,
        }
        result.append(PersistentChunk(
            id=row.hash,
            material_id=row.material_id,
            text=row.text,
            embedding=emb,
            metadata=metadata_with_score,
        ))
    return result


def count_persistent(db: Session) -> int:
    """Sprint 3.5.2: сколько chunk'ов в rag_chunks."""
    from app.rag_models import RagChunk
    return db.execute(select(func.count(RagChunk.id))).scalar_one()

def search_hybrid_persistent(
    db: Session,
    query: str,
    query_embedding: list[float] | None = None,
    top_k: int = 3,
    material_id: int | None = None,
    bm25_weight: float = 0.5,
    embedding_weight: float = 0.5,
) -> list[PersistentChunk]:
    """Sprint 88: hybrid BM25 + real embeddings search.

    Комбинирует:
    - BM25 score (keyword match, fast, no embeddings needed)
    - Cosine similarity на real embeddings (semantic match)

    Использует weighted combination: final_score = bm25_weight * norm_bm25
    + embedding_weight * norm_cosine.

    Default: 50/50 weighted. Для keyword-heavy queries → increase
    bm25_weight. Для semantic queries → increase embedding_weight.

    Returns: top_k PersistentChunk sorted by combined score (desc).
    """
    from app.rag_models import RagChunk

    # Get BM25 results (top 5x candidates)
    bm25_results = search_bm25_persistent(
        db, query, top_k=top_k * 5, material_id=material_id
    )
    if not bm25_results:
        return []

    # Build BM25 score map (normalize to 0-1)
    bm25_scores: dict[str, float] = {}
    bm25_max = max(
        (c.metadata.get("bm25_score", 0) for c in bm25_results),
        default=1.0,
    )
    for chunk in bm25_results:
        bm25_scores[chunk.id] = (
            chunk.metadata.get("bm25_score", 0) / bm25_max
            if bm25_max > 0 else 0
        )

    # Get real embeddings results (если есть)
    embedding_scores: dict[str, float] = {}
    if query_embedding:
        real_results = search_real_persistent(
            db, query_embedding, top_k=top_k * 5, material_id=material_id
        )
        for chunk in real_results:
            # Cosine similarity уже в normalized embeddings
            embedding_scores[chunk.id] = chunk.metadata.get("cosine_score", 0)

    # Combine scores
    combined: list[tuple[float, PersistentChunk]] = []
    for chunk in bm25_results:
        bm25_norm = bm25_scores.get(chunk.id, 0)
        emb_norm = embedding_scores.get(chunk.id, 0)
        final_score = bm25_weight * bm25_norm + embedding_weight * emb_norm
        combined.append((final_score, chunk))

    # Sort by combined score desc
    combined.sort(key=lambda x: -x[0])
    return [c for _, c in combined[:top_k]]

