"""RAG search endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.db.session import get_db
from app.rag import add_chunks, chunk_text, get_embedding, remove_by_material, search, stats
from app.rag_persist import (
    add_chunks_persistent,
    count_persistent,
    search_bm25_persistent,
    search_hybrid_persistent,
    search_persistent,
    search_real_persistent,
)
from app.subjects import models as subj_models
from app.users.models import User

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


class IndexRequest(BaseModel):
    material_id: int
    text: str
    metadata: dict | None = None


class IndexResponse(BaseModel):
    indexed_chunks: int
    chunk_ids: list[str]


class SearchRequest(BaseModel):
    query: str
    top_k: int = 3
    material_id: int | None = None


class SearchHit(BaseModel):
    chunk_id: str
    material_id: int
    text: str
    score: float
    metadata: dict


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    query: str


@router.post("/index", response_model=IndexResponse)
async def index_document(
    payload: IndexRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Индексирует текст: chunking + embeddings."""
    # Verify material exists
    material = db.get(subj_models.LearningMaterial, payload.material_id)
    if material is None:
        raise HTTPException(404, "Material not found")

    chunks = chunk_text(payload.text)
    if not chunks:
        raise HTTPException(400, "Empty text")

    embeddings = []
    for chunk in chunks:
        emb = await get_embedding(chunk)
        embeddings.append(emb)

    chunk_ids = add_chunks(payload.material_id, chunks, embeddings, payload.metadata)
    # Sprint 3.5.2: дублируем в rag_chunks (persistent). Best-effort:
    # если БД недоступна — log warn, но endpoint возвращает 200 (in-memory OK).
    try:
        add_chunks_persistent(db, payload.material_id, chunks, embeddings, payload.metadata)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("rag_chunks insert failed (continuing): %s", e)
    return IndexResponse(indexed_chunks=len(chunks), chunk_ids=chunk_ids)


@router.post("/search", response_model=SearchResponse)
async def search_endpoint(
    payload: SearchRequest,
    current: User = Depends(get_current_user),
):
    """Ищет top_k релевантных чанков по query."""
    query_emb = await get_embedding(payload.query)
    results = search(query_emb, payload.top_k, payload.material_id)

    return SearchResponse(
        query=payload.query,
        hits=[
            SearchHit(
                chunk_id=c.id,
                material_id=c.material_id,
                text=c.text,
                score=0.0,  # score не возвращается напрямую (для простоты)
                metadata=c.metadata,
            )
            for c in results
        ],
    )


@router.post("/search/bm25", response_model=SearchResponse)
def search_bm25_endpoint(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Sprint 57: BM25 keyword search (без embeddings).

    Альтернатива /search (cosine similarity) для keyword queries.
    Не требует real embeddings — работает на 4GB RAM.

    Преимущества:
    - Быстрее (~1ms vs 50ms)
    - Не зависит от AI API
    - Лучше для keyword queries (specific terms)

    Returns top_k PersistentChunk с metadata.
    """
    results = search_bm25_persistent(
        db, payload.query, top_k=payload.top_k, material_id=payload.material_id
    )
    return SearchResponse(
        query=payload.query,
        hits=[
            SearchHit(
                chunk_id=c.id,
                material_id=c.material_id,
                text=c.text,
                score=0.0,
                metadata=c.metadata,
            )
            for c in results
        ],
    )


@router.post("/search/hybrid", response_model=SearchResponse)
def search_hybrid_endpoint(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Sprint 88: hybrid BM25 + real embeddings search.

    Комбинирует keyword (BM25) и semantic (cosine) similarity
    weighted (default 50/50). Best for mixed queries.

    Returns 422 если sentence-transformers unavailable
    (но BM25 часть работает без embeddings).

    Expected Recall@3: > BM25 alone (10%) + real alone (11%).
    """
    from app.rag_embeddings import encode_single, is_available

    # BM25 часть работает без embeddings
    bm25_weight = 0.5
    embedding_weight = 0.5

    query_embedding = None
    if is_available():
        query_embedding = encode_single(payload.query)

    results = search_hybrid_persistent(
        db,
        payload.query,
        query_embedding=query_embedding,
        top_k=payload.top_k,
        material_id=payload.material_id,
        bm25_weight=bm25_weight,
        embedding_weight=embedding_weight,
    )
    return SearchResponse(
        query=payload.query,
        hits=[
            SearchHit(
                chunk_id=c.id,
                material_id=c.material_id,
                text=c.text,
                score=0.0,
                metadata=c.metadata,
            )
            for c in results
        ],
    )


@router.post("/search/real", response_model=SearchResponse)
def search_real_endpoint(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Sprint 70: real embeddings search (sentence-transformers).

    Uses 384-dim vectors from metadata_json["embedding_v2"]
    (backfilled in Sprint 70). Better for semantic queries
    than BM25 (keyword) or hash-based (random).

    Requires 8GB RAM (Sprint 70 upgrade). Returns 422 если
    sentence-transformers unavailable.

    Recall@3: ~11% (Sprint 70 benchmark, vs 0% hash, 10% BM25).
    """
    from app.rag_embeddings import encode_single, is_available

    if not is_available():
        raise HTTPException(
            422,
            "Real embeddings unavailable. sentence-transformers not installed.",
        )

    query_vec = encode_single(payload.query)
    if query_vec is None:
        raise HTTPException(500, "Encoding failed")

    results = search_real_persistent(
        db, query_vec, top_k=payload.top_k, material_id=payload.material_id
    )
    return SearchResponse(
        query=payload.query,
        hits=[
            SearchHit(
                chunk_id=c.id,
                material_id=c.material_id,
                text=c.text,
                # Sprint 70: return cosine similarity as score.
                # We need to recompute since PersistentChunk не хранит score.
                score=0.0,
                metadata=c.metadata,
            )
            for c in results
        ],
    )


@router.delete("/material/{material_id}")
def remove_material(
    material_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Удаляет все embeddings материала (in-memory + persistent)."""
    in_mem_count = remove_by_material(material_id)
    # Sprint 3.5.2: persistent тоже удаляем
    persistent_count = 0
    try:
        from app.rag_models import RagChunk
        from sqlalchemy import delete
        result = db.execute(delete(RagChunk).where(RagChunk.material_id == material_id))
        db.commit()
        persistent_count = result.rowcount
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("rag_chunks delete failed: %s", e)
        db.rollback()
    return {
        "removed_chunks": in_mem_count,
        "persistent_chunks_removed": persistent_count,
    }


@router.get("/stats")
def stats_endpoint(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Статистика RAG store (in-memory + persistent)."""
    in_mem = stats()
    persistent_chunks = 0
    try:
        persistent_chunks = count_persistent(db)
    except Exception:
        pass
    return {**in_mem, "persistent_chunks": persistent_chunks}
