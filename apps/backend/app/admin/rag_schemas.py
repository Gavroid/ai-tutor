"""Sprint 4 RAG production: Pydantic schemas для /admin/rag/* API.

Endpoints:
- POST /admin/rag/upload (multipart PDF) → IngestResponse
- POST /admin/rag/reindex → IngestResponse (same shape, но mode=full_wipe/skip_existing)
- GET /admin/rag/status?job_id=... → RagJobStatus
- GET /admin/rag/stats → RagStats

Reindex mode semantics:
- full_wipe: DELETE existing chunks WHERE material_id, затем ingest заново.
- skip_existing: add_chunks_persistent skip если chunk_hash уже есть (idempotent).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Sprint 4 RAG: lifecycle статуса ingestion job."""

    QUEUED = "queued"  # В RQ queue, worker ещё не подхватил
    RUNNING = "running"  # Worker выполняет extract → chunk → embed → persist
    DONE = "done"  # Успешно завершён
    FAILED = "failed"  # Exception (PDF corrupt, encoding, etc.)


class IngestMode(str, Enum):
    """Sprint 4 RAG: reindex semantics."""

    FULL_WIPE = "full_wipe"  # DELETE chunks WHERE material_id, затем ingest
    SKIP_EXISTING = "skip_existing"  # add_chunks_persistent skip по chunk_hash


class IngestRequest(BaseModel):
    """Sprint 4 RAG: request body для /admin/rag/upload и /reindex.

    Для upload поля filename + material_id обязательны.
    Для reindex — material_id + mode (filename опционально если material.file_path есть).
    """

    material_id: int = Field(..., ge=1, description="LearningMaterial.id")
    filename: str = Field(..., min_length=1, max_length=300)
    mode: IngestMode = Field(default=IngestMode.SKIP_EXISTING)
    dry_run: bool = Field(default=False, description="Не писать в БД (env RAG_DRY_RUN=1)")


class IngestResponse(BaseModel):
    """Sprint 4 RAG: response после enqueue job."""

    job_id: str = Field(..., description="UUID job в RQ queue")
    status: JobStatus
    material_id: int
    chunks_count: int = Field(default=0, description="Заполняется при status=done/failed")
    duration_ms: int | None = Field(default=None, description="Wall-clock время ingest")
    message: str | None = None


class RagJobStatus(BaseModel):
    """Sprint 4 RAG: GET /admin/rag/status response."""

    job_id: str
    status: JobStatus
    material_id: int | None = None
    chunks_count: int = 0
    duration_ms: int | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RagStats(BaseModel):
    """Sprint 4 RAG: GET /admin/rag/stats aggregates."""

    jobs_last_24h: int = 0
    jobs_failed: int = 0
    chunks_total: int = 0
    avg_duration_ms: float = 0.0
    p50_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    queue_depth: int = 0
    embedding_mode: str = "unknown"  # "real" | "hash_fallback"


class SubjectDetection(BaseModel):
    """Sprint 4 RAG: результат auto-detect subject из filename / content."""

    subject_code: str | None = None
    grade: int | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    method: str = Field(default="none")  # "filename_regex" | "keyword" | "llm" | "none"
