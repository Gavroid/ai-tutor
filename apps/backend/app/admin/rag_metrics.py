"""Sprint 4 RAG production: Prometheus метрики для ingestion pipeline.

Метрики:
- rag_uploads_total{status} — Counter, инкремент при каждом upload.
- rag_chunks_total — Counter, инкремент при persist каждого chunk.
- rag_ingest_duration_seconds — Histogram, время одного ingest job.
- rag_queue_depth — Gauge, размер RQ очереди (обновляется при /admin/rag/stats).

Доступны на /metrics через prometheus_client (уже instrumented в main.py).
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# Sprint 4 RAG: метрики названы с префиксом `rag_` для namespace isolation.
RAG_UPLOADS_TOTAL = Counter(
    "rag_uploads_total",
    "Total RAG PDF uploads by status (success/failed/queued).",
    labelnames=("status",),  # success | failed | queued | rejected
)

RAG_CHUNKS_TOTAL = Counter(
    "rag_chunks_total",
    "Total RAG chunks persisted to rag_chunks table.",
)

RAG_INGEST_DURATION = Histogram(
    "rag_ingest_duration_seconds",
    "Wall-clock time of a single RAG ingest job (extract + chunk + embed + persist).",
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

RAG_QUEUE_DEPTH = Gauge(
    "rag_queue_depth",
    "Current depth of RQ ingestion queue (rag_ingest_queue).",
)

RAG_EMBEDDING_MODE = Gauge(
    "rag_embedding_mode_active",
    "1 if real sentence-transformers, 0 if hash fallback.",
)


def record_upload(status: str) -> None:
    """Инкремент RAG_UPLOADS_TOTAL{status}."""
    RAG_UPLOADS_TOTAL.labels(status=status).inc()


def record_chunks(count: int) -> None:
    """Инкремент RAG_CHUNKS_TOTAL на count."""
    if count > 0:
        RAG_CHUNKS_TOTAL.inc(count)


def observe_ingest_duration(seconds: float) -> None:
    """Sprint 4 RAG: observe ingest job duration в Histogram."""
    RAG_INGEST_DURATION.observe(seconds)


def set_queue_depth(depth: int) -> None:
    """Sprint 4 RAG: обновить queue depth gauge."""
    RAG_QUEUE_DEPTH.set(depth)


def set_embedding_mode(real: bool) -> None:
    """Sprint 4 RAG: 1 если real embeddings, 0 если fallback."""
    RAG_EMBEDDING_MODE.set(1 if real else 0)
