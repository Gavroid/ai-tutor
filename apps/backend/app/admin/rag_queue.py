"""Sprint 4 RAG production: Redis-backed очередь для async ingestion.

Дизайн (минимальный, без зависимости `rq`):
- Queue name: "rag_ingest_queue"
- Job representation: JSON {job_id, material_id, pdf_path, mode, dry_run}
- Push: redis.lpush("rag_ingest_queue", json.dumps(job))
- Pop (blocking): redis.brpop("rag_ingest_queue", timeout=5)
- Status storage: redis.hset(f"rag_job:{job_id}", mapping={...})

Fallback: если RAG_SYNC=1 или Redis недоступен — выполняем ingest inline.
Это страховка от регрессии prod-deploy без Redis.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

from app.admin.rag_metrics import (
    record_chunks,
    record_upload,
    set_embedding_mode,
)
from app.admin.rag_schemas import IngestMode, JobStatus
from app.rag_embeddings import is_available
from app.rag_ingest import _hash_embedding, extract_text_from_pdf

logger = logging.getLogger(__name__)


# Sprint 4 RAG: ключи Redis (изолированы от других features).
QUEUE_KEY: str = "rag_ingest_queue"
JOB_KEY_PREFIX: str = "rag_job:"


def _should_run_sync() -> bool:
    """Sprint 4 RAG: если RAG_SYNC=1 — fallback на inline execution.

    Returns:
        True если нужно выполнять ingest в request thread (sync).
    """
    return os.environ.get("RAG_SYNC", "").strip() == "1"


def _get_sync_redis() -> Any:
    """Sprint 4 RAG: sync Redis client (для lpush/brpop/hset операций).

    Не зависит от main._get_redis (он async и нужен для rate limit/budget).
    Returns:
        Redis client или None если REDIS_URL не задан / недоступен.
    """
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if not redis_url:
        return None
    try:
        import redis as redis_sync

        return redis_sync.from_url(redis_url, decode_responses=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sprint 4 RAG: redis.from_url failed: %s", exc)
        return None


def enqueue_ingest_job(
    material_id: int,
    pdf_path: str | Path,
    filename: str,
    mode: IngestMode = IngestMode.SKIP_EXISTING,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Sprint 4 RAG: enqueue ingest job в Redis queue.

    Args:
        material_id: LearningMaterial.id.
        pdf_path: путь к сохранённому PDF файлу.
        filename: оригинальное имя файла (для логов).
        mode: reindex semantics.
        dry_run: не писать в БД.

    Returns:
        dict {job_id, status, chunks_count, duration_ms} — job_id всегда,
        остальное заполняется после исполнения (для sync mode).
    """
    job_id = uuid.uuid4().hex[:16]
    job_payload = {
        "job_id": job_id,
        "material_id": material_id,
        "pdf_path": str(pdf_path),
        "filename": filename,
        "mode": mode.value,
        "dry_run": dry_run,
        "created_at": time.time(),
    }

    # Sync fallback path.
    if _should_run_sync():
        logger.info("Sprint 4 RAG: RAG_SYNC=1, running inline (job_id=%s)", job_id)
        return _execute_job_sync(job_payload)

    sync_client = _get_sync_redis()
    if sync_client is None:
        logger.warning("Sprint 4 RAG: Redis unavailable, running inline")
        return _execute_job_sync(job_payload)

    # Async path: push в queue + initial status.
    try:
        sync_client.lpush(QUEUE_KEY, json.dumps(job_payload))
        sync_client.hset(
            f"{JOB_KEY_PREFIX}{job_id}",
            mapping={
                "status": JobStatus.QUEUED.value,
                "material_id": str(material_id),
                "filename": filename,
                "created_at": str(time.time()),
            },
        )
        # Expire job status через 7 дней (cleanup).
        sync_client.expire(f"{JOB_KEY_PREFIX}{job_id}", 7 * 24 * 3600)
        record_upload("queued")
        logger.info("Sprint 4 RAG: enqueued job_id=%s material_id=%d", job_id, material_id)
        return {"job_id": job_id, "status": JobStatus.QUEUED.value, "chunks_count": 0, "duration_ms": None}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sprint 4 RAG: enqueue failed, falling back to sync: %s", exc)
        return _execute_job_sync(job_payload)


def _execute_job_sync(job_payload: dict[str, Any]) -> dict[str, Any]:
    """Sprint 4 RAG: inline исполнение job (sync mode / Redis unavailable).

    Returns dict с финальным статусом (done/failed) и chunks_count.
    """
    start = time.monotonic()
    job_id = job_payload["job_id"]
    material_id = job_payload["material_id"]
    pdf_path = Path(job_payload["pdf_path"])
    dry_run = job_payload.get("dry_run", False)

    set_embedding_mode(is_available())

    try:
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF не найден: {pdf_path}")

        pages = extract_text_from_pdf(pdf_path)
        all_text = "\n\n".join(p.text for p in pages if p.text.strip())

        if not all_text.strip():
            duration_ms = int((time.monotonic() - start) * 1000)
            record_upload("success")
            return {
                "job_id": job_id,
                "status": JobStatus.DONE.value,
                "chunks_count": 0,
                "duration_ms": duration_ms,
            }

        # Inline chunking (используем существующий chunk_text_into_rag).
        from app.rag_ingest import chunk_text_into_rag

        chunks = chunk_text_into_rag(all_text)
        if not chunks:
            duration_ms = int((time.monotonic() - start) * 1000)
            record_upload("success")
            return {
                "job_id": job_id,
                "status": JobStatus.DONE.value,
                "chunks_count": 0,
                "duration_ms": duration_ms,
            }

        # Embeddings (real или hash fallback).
        from app.rag_embeddings import encode_single

        use_real = is_available()
        chunk_records: list[tuple[str, list[float]]] = []
        for chunk in chunks:
            embedding: list[float] | None = None
            if use_real:
                try:
                    embedding = encode_single(chunk)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Sprint 4 RAG: encode_single failed, using hash: %s", exc)
            if embedding is None:
                embedding = _hash_embedding(chunk)
            chunk_records.append((chunk, embedding))

        if not dry_run:
            from app.db.session import get_db
            from app.rag_persist import add_chunks_persistent

            db_gen = get_db()
            db = next(db_gen)
            try:
                texts = [c[0] for c in chunk_records]
                embeddings = [c[1] for c in chunk_records]
                saved = add_chunks_persistent(db, material_id, texts, embeddings)
                db.commit()
                chunks_count = len(saved)
            finally:
                try:
                    next(db_gen)
                except StopIteration:
                    pass
        else:
            chunks_count = len(chunk_records)

        duration_ms = int((time.monotonic() - start) * 1000)
        record_chunks(chunks_count)
        record_upload("success")
        return {
            "job_id": job_id,
            "status": JobStatus.DONE.value,
            "chunks_count": chunks_count,
            "duration_ms": duration_ms,
        }
    except Exception as exc:  # noqa: BLE001
        duration_ms = int((time.monotonic() - start) * 1000)
        record_upload("failed")
        logger.exception("Sprint 4 RAG: ingest failed for job_id=%s: %s", job_id, exc)
        return {
            "job_id": job_id,
            "status": JobStatus.FAILED.value,
            "chunks_count": 0,
            "duration_ms": duration_ms,
            "error_message": str(exc),
        }


def get_job_status(job_id: str) -> dict[str, Any] | None:
    """Sprint 4 RAG: получить status job из Redis.

    Returns None если job не найден.
    """
    sync_client = _get_sync_redis()
    if sync_client is None:
        return None

    try:
        data = sync_client.hgetall(f"{JOB_KEY_PREFIX}{job_id}")
        if not data:
            return None
        return {
            "job_id": job_id,
            "status": data.get("status", JobStatus.QUEUED.value),
            "material_id": int(data["material_id"]) if data.get("material_id") else None,
            "chunks_count": int(data.get("chunks_count", 0)),
            "duration_ms": int(data["duration_ms"]) if data.get("duration_ms") else None,
            "error_message": data.get("error_message"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sprint 4 RAG: get_job_status failed: %s", exc)
        return None


def update_job_status(job_id: str, **fields: Any) -> None:
    """Sprint 4 RAG: обновить status job (вызывается worker'ом)."""
    sync_client = _get_sync_redis()
    if sync_client is None:
        return
    try:
        payload = {k: str(v) for k, v in fields.items()}
        payload["updated_at"] = str(time.time())
        sync_client.hset(f"{JOB_KEY_PREFIX}{job_id}", mapping=payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sprint 4 RAG: update_job_status failed: %s", exc)


def queue_depth() -> int:
    """Sprint 4 RAG: текущая глубина queue (для /admin/rag/stats и Prometheus gauge)."""
    sync_client = _get_sync_redis()
    if sync_client is None:
        return 0
    try:
        return int(sync_client.llen(QUEUE_KEY))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sprint 4 RAG: queue_depth failed: %s", exc)
        return 0


# === Public API для ingest_pdf_async (используется в тестах) ===


def ingest_pdf_async(
    material_id: int,
    pdf_path: str | Path,
    filename: str,
    mode: IngestMode = IngestMode.SKIP_EXISTING,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Sprint 4 RAG: alias для enqueue_ingest_job — compat с тестами."""
    return enqueue_ingest_job(material_id, pdf_path, filename, mode, dry_run)
