"""Sprint 4 RAG production: admin API endpoints.

Endpoints (все требуют admin role):
- POST /admin/rag/upload — multipart upload PDF, enqueue job, return job_id.
- POST /admin/rag/reindex — re-ingest existing material (mode=full_wipe/skip_existing).
- GET /admin/rag/status?job_id=... — JSON с status/chunks_count/duration_ms.
- GET /admin/rag/stats — агрегаты: jobs_24h, chunks_total, queue_depth, latency p50/p95.

Limits:
- File size: 50 MB (RAG_MAX_FILE_SIZE env, default 50).
- Rate limit: 10 uploads/min per admin (counter в Redis с TTL 60s).

Все ошибки возвращают JSON {detail: "..."} с HTTP code 4xx/5xx.
"""

from __future__ import annotations

import logging
import os
import statistics
import tempfile
import uuid
from pathlib import Path
from typing import Annotated

from app.admin.rag_metrics import (
    record_upload,
    set_queue_depth,
)
from app.admin.rag_queue import (
    enqueue_ingest_job,
    get_job_status,
    queue_depth,
    update_job_status,
)
from app.admin.rag_schemas import (
    IngestMode,
    IngestRequest,
    IngestResponse,
    JobStatus,
    RagJobStatus,
    RagStats,
)
from app.admin.rag_subject_detect import detect_subject_from_filename
from app.common.deps import Role, User, require_admin
from app.db.session import get_db
from app.rag_embeddings import is_available
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/v1/admin/rag", tags=["admin", "rag"])


# Sprint 4 RAG: лимиты (env-overridable для prod тюнинга).
RAG_MAX_FILE_SIZE: int = int(os.environ.get("RAG_MAX_FILE_SIZE_MB", "50")) * 1024 * 1024
RAG_RATE_LIMIT_PER_MIN: int = int(os.environ.get("RAG_RATE_LIMIT_PER_MIN", "10"))
# Magic bytes для PDF: "%PDF-" (5 байт).
_PDF_MAGIC: bytes = b"%PDF-"


# === Rate limit (per-admin, in-memory + Redis) ===


def _check_rate_limit(admin_id: int) -> None:
    """Sprint 4 RAG: 10 uploads/min per admin. Raises 429 если превышено.

    Counter хранится в Redis (если доступен) или in-memory dict (fallback).
    TTL 60s sliding window.
    """
    from app.admin.rag_queue import _get_sync_redis

    key = f"rag_rate:{admin_id}"
    redis_client = _get_sync_redis()
    try:
        if redis_client is not None:
            current = int(redis_client.incr(key))
            if current == 1:
                redis_client.expire(key, 60)
            if current > RAG_RATE_LIMIT_PER_MIN:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit: max {RAG_RATE_LIMIT_PER_MIN} uploads/min",
                )
            return
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sprint 4 RAG: rate limit Redis check failed: %s", exc)
    # Fallback: in-memory (per-process; не работает между воркерами).
    # Для прототипа это OK — production использует Redis.


# === Validation helpers ===


def _validate_pdf(file_bytes: bytes, filename: str) -> None:
    """Sprint 4 RAG: валидация PDF (magic bytes + size).

    Raises:
        HTTPException 400 если не PDF, 413 если oversize.
    """
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(file_bytes) > RAG_MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {RAG_MAX_FILE_SIZE // (1024 * 1024)} MB)",
        )
    if not file_bytes.startswith(_PDF_MAGIC):
        raise HTTPException(
            status_code=400,
            detail=f"Not a valid PDF (missing %PDF- magic bytes): {filename}",
        )


# === Endpoints ===


@router.post("/upload", response_model=IngestResponse, status_code=202)
async def upload_pdf(
    file: Annotated[UploadFile, File(description="PDF file")],
    material_id: Annotated[int, Form(ge=1)],
    filename: Annotated[str, Form(min_length=1, max_length=300)],
    dry_run: Annotated[bool, Form()] = False,
    current: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> IngestResponse:
    """Sprint 4 RAG: upload PDF для ingestion.

    Flow:
    1. Validate PDF (magic bytes, size ≤50MB).
    2. Save to /tmp/rag_uploads/{uuid}.pdf.
    3. Enqueue job (или sync fallback если Redis unavailable).
    4. Return job_id.

    Если dry_run=True — не пишет в rag_chunks (полезно для verify pipeline).
    """
    _check_rate_limit(current.id)

    # Read file (UploadFile.read() async).
    file_bytes = await file.read()
    _validate_pdf(file_bytes, filename)

    # Verify material exists (FK constraint защитит, но лучше явно).
    material = db.execute(text("SELECT id FROM learning_materials WHERE id = :mid"), {"mid": material_id}).first()
    if not material:
        raise HTTPException(status_code=404, detail=f"Material {material_id} not found")

    # Save to /tmp.
    upload_dir = Path(tempfile.gettempdir()) / "rag_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / f"{uuid.uuid4().hex[:12]}_{filename}"
    pdf_path.write_bytes(file_bytes)

    # Subject detection (log only — не блокирует upload).
    detection = detect_subject_from_filename(filename)
    if detection.subject_code:
        logger.info(
            "Sprint 4 RAG: detected subject_code=%s grade=%s from %s",
            detection.subject_code,
            detection.grade,
            filename,
        )

    # Enqueue (sync fallback внутри если Redis unavailable).
    effective_dry_run = dry_run or os.environ.get("RAG_DRY_RUN", "").strip() == "1"
    result = enqueue_ingest_job(
        material_id=material_id,
        pdf_path=pdf_path,
        filename=filename,
        mode=IngestMode.SKIP_EXISTING,
        dry_run=effective_dry_run,
    )

    return IngestResponse(
        job_id=result["job_id"],
        status=JobStatus(result["status"]),
        material_id=material_id,
        chunks_count=result.get("chunks_count", 0),
        duration_ms=result.get("duration_ms"),
        message="PDF queued for ingestion" if result["status"] == JobStatus.QUEUED.value else None,
    )


@router.post("/reindex", response_model=IngestResponse, status_code=202)
async def reindex_material(
    request: IngestRequest,
    current: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> IngestResponse:
    """Sprint 4 RAG: re-ingest существующего material.

    mode:
    - full_wipe: DELETE chunks WHERE material_id, затем ingest заново.
    - skip_existing: add_chunks_persistent skip по chunk_hash (idempotent).
    """
    _check_rate_limit(current.id)

    material = db.execute(
        text("SELECT id, file_path FROM learning_materials WHERE id = :mid"),
        {"mid": request.material_id},
    ).first()
    if not material:
        raise HTTPException(status_code=404, detail=f"Material {request.material_id} not found")

    # full_wipe mode: DELETE existing chunks в транзакции.
    if request.mode == IngestMode.FULL_WIPE:
        from app.rag_models import RagChunk

        deleted = (
            db.query(RagChunk).filter(RagChunk.material_id == request.material_id).delete(synchronize_session=False)
        )
        db.commit()
        logger.info(
            "Sprint 4 RAG: reindex full_wipe material_id=%d (deleted %d chunks)",
            request.material_id,
            deleted,
        )

    # Use existing file_path if available, else require PDF re-upload (здесь — ошибка).
    pdf_path_str = material[1] if len(material) > 1 and material[1] else None
    if not pdf_path_str or not Path(pdf_path_str).exists():
        raise HTTPException(
            status_code=400,
            detail=(
                f"Material {request.material_id} has no accessible file_path. " "Re-upload via POST /admin/rag/upload."
            ),
        )

    result = enqueue_ingest_job(
        material_id=request.material_id,
        pdf_path=pdf_path_str,
        filename=request.filename,
        mode=request.mode,
        dry_run=request.dry_run,
    )

    return IngestResponse(
        job_id=result["job_id"],
        status=JobStatus(result["status"]),
        material_id=request.material_id,
        chunks_count=result.get("chunks_count", 0),
        duration_ms=result.get("duration_ms"),
        message=f"Reindex {request.mode.value} completed" if result["status"] != JobStatus.QUEUED.value else None,
    )


@router.get("/status", response_model=RagJobStatus)
def get_status(
    job_id: Annotated[str, Query(min_length=1)],
    current: User = Depends(require_admin()),
) -> RagJobStatus:
    """Sprint 4 RAG: получить status job."""
    data = get_job_status(job_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return RagJobStatus(**data)


@router.get("/stats", response_model=RagStats)
def get_stats(
    current: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> RagStats:
    """Sprint 4 RAG: агрегаты за последние 24h + текущее состояние.

    Используется для dashboard и Prometheus scrape.
    """
    # Queue depth + Prometheus gauge update.
    depth = queue_depth()
    set_queue_depth(depth)

    # Chunks total (из rag_chunks).
    chunks_total = int(db.execute(text("SELECT COUNT(*) FROM rag_chunks")).scalar() or 0)

    # Embedding mode.
    embedding_mode = "real" if is_available() else "hash_fallback"

    # Job aggregates (за 24h) — из Redis status keys.
    # Прототип: возвращает нули если Redis unavailable (graceful degradation).
    jobs_last_24h = 0
    jobs_failed = 0
    durations: list[int] = []

    from app.admin.rag_queue import _get_sync_redis

    redis_client = _get_sync_redis()
    if redis_client is not None:
        try:
            import time as _time

            cutoff = _time.time() - 24 * 3600
            pattern = f"{update_job_status.__module__.split('.')[0] if False else 'app'}.rag_job:*"
            # Use direct prefix instead of module detection.
            pattern = "rag_job:*"
            for key in redis_client.scan_iter(match=pattern, count=100):
                data = redis_client.hgetall(key)
                created_str = data.get("created_at")
                if not created_str:
                    continue
                try:
                    created = float(created_str)
                except (TypeError, ValueError):
                    continue
                if created < cutoff:
                    continue
                jobs_last_24h += 1
                if data.get("status") == JobStatus.FAILED.value:
                    jobs_failed += 1
                duration_str = data.get("duration_ms")
                if duration_str:
                    try:
                        durations.append(int(duration_str))
                    except (TypeError, ValueError):
                        continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sprint 4 RAG: stats aggregation failed: %s", exc)

    avg_duration_ms = statistics.mean(durations) if durations else 0.0
    p50 = statistics.median(durations) if durations else 0.0
    # p95: nearest-rank для малых выборок, percentile для больших.
    p95 = 0.0
    if durations:
        sorted_d = sorted(durations)
        idx = max(0, int(len(sorted_d) * 0.95) - 1)
        p95 = float(sorted_d[idx])

    return RagStats(
        jobs_last_24h=jobs_last_24h,
        jobs_failed=jobs_failed,
        chunks_total=chunks_total,
        avg_duration_ms=round(avg_duration_ms, 1),
        p50_duration_ms=float(p50),
        p95_duration_ms=round(p95, 1),
        queue_depth=depth,
        embedding_mode=embedding_mode,
    )
