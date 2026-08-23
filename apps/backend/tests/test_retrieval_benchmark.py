"""Sprint 6 (2026-08-23): retrieval benchmark contract tests.

Definition of Done:
- benchmark reproducible;
- failed retrieval cases публикуются в audit;
- source/page mapping корректен;
- OCR-risk subjects не становятся pilot-visible автоматически.
"""
from __future__ import annotations

import os

# Deterministic AI provider для contract env.
os.environ["APP_SECRET_KEY"] = "test-secret-key-for-retrieval-benchmark-789"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ["AI_DETERMINISTIC_MODE"] = "1"

import pytest

from app.subjects.retrieval_benchmark import (
    RetrievalBenchmarkResult,
    RetrievalProbe,
    benchmark_math6_fixture,
    evaluate_probes,
    _tokenize,
)


# === Tokenize / scoring ========================================================

def test_tokenize_lowercase_russian():
    toks = _tokenize("Среднее арифметическое — это сумма чисел.")
    assert "среднее" in toks
    assert "арифметическое" in toks
    assert "сумма" in toks
    assert "—" not in toks  # filter noise


def test_evaluate_probes_recall_and_mrr_for_math_fixture():
    """Sprint 6: Math-6 fixture даёт recall@5 ≥ 0.75 и MRR@5 ≥ 0.5."""
    subj, probes, chunks = benchmark_math6_fixture()
    result = evaluate_probes(
        subject_code=subj,
        probes=probes,
        chunks=chunks,
        top_k=5,
    )
    assert result.total == 4
    assert result.hits == 4, (
        f"ожидалось 4 hit, got {result.hits}; failed={result.failed_probes}"
    )
    assert result.recall_at_k >= 0.75, result.recall_at_k
    assert result.mrr_at_k >= 0.5, result.mrr_at_k


def test_evaluate_probes_fails_on_mismatch_query():
    """Probe с запросом без overlap к relevant-chunk → 0 hits, MRR=0,
    failed_probes содержит probe_id."""
    probes = [
        RetrievalProbe(
            probe_id="miss-001",
            subject_code="math",
            query="квантовая механика и операторы",
            relevant_keys=("nonexistent-chunk",),
        ),
    ]
    chunks = [
        {
            "key": "math-chunk-1",
            "text": "Среднее арифметическое.",
            "metadata": {"subject_code": "math", "topic_id": 187},
        },
    ]
    result = evaluate_probes(subject_code="math", probes=probes, chunks=chunks, top_k=5)
    assert result.hits == 0, (
        f"если relevant_key отсутствует в chunks, top-k не должен содержать его: hits={result.hits}"
    )
    assert result.recall_at_k == 0.0
    assert result.mrr_at_k == 0.0
    assert "miss-001" in result.failed_probes


def test_evaluate_probes_skips_probes_for_other_subjects():
    """Probes для другого subject_code НЕ считаются."""
    probes = [
        RetrievalProbe(
            probe_id="algebra-001",
            subject_code="algebra",
            query="уравнения",
            relevant_keys=("alg-chunk-1",),
        ),
    ]
    chunks = [{"key": "alg-chunk-1", "text": "уравнения", "metadata": {}}]
    result = evaluate_probes(subject_code="math", probes=probes, chunks=chunks, top_k=5)
    assert result.total == 0
    assert result.hits == 0


def test_threshold_gating_for_math6_pilot():
    """Sprint 6: Math-6 benchmark должен проходить subject-specific threshold."""
    subj, probes, chunks = benchmark_math6_fixture()
    result = evaluate_probes(subject_code=subj, probes=probes, chunks=chunks, top_k=5)
    assert result.passes_threshold, (
        f"Math-6 benchmark failed gate: recall={result.recall_at_k} mrr={result.mrr_at_k}"
    )


def test_threshold_gating_for_ocr_risk_subject_blocks_pilot():
    """OCR-risk subject (например 'hist') при recall<0.4 → НЕ проходит threshold.

    Это гарантирует Sprint 6 §Scope policy: «OCR-risk subjects не
    становятся pilot-visible автоматически».
    """
    probes = [
        RetrievalProbe(
            probe_id="hist-001",
            subject_code="hist",
            query="история России",
            relevant_keys=("hist-actual-chunk",),
        ),
    ]
    # Пустые chunks → recall=0.
    result = evaluate_probes(subject_code="hist", probes=probes, chunks=[], top_k=5)
    assert result.total == 1
    assert result.recall_at_k == 0.0
    # Default threshold 0.4 / 0.3.
    assert not result.passes_threshold
    # По итогу: сюжет соответствует «hist» blocked_ocr rationale.


# === Subject-specific thresholds ===============================================

def test_math_threshold_strict():
    """Math требует 0.6 / 0.5 (Sprint 6 §thresholds)."""
    # Synthesize high-recall benchmark.
    probes = [
        RetrievalProbe(
            probe_id="m1",
            subject_code="math",
            query="среднее",
            relevant_keys=("c1",),
        ),
        RetrievalProbe(
            probe_id="m2",
            subject_code="math",
            query="проценты",
            relevant_keys=("c2",),
        ),
    ]
    chunks = [
        {"key": "c1", "text": "среднее арифметическое", "metadata": {}},
        {"key": "c2", "text": "проценты и скидки", "metadata": {}},
    ]
    result = evaluate_probes(subject_code="math", probes=probes, chunks=chunks, top_k=5)
    assert result.passes_threshold
    # Теперь «сломаем» recall.
    bad_probes = [
        RetrievalProbe(
            probe_id="bad-1",
            subject_code="math",
            query="qwerty",
            relevant_keys=("zzz",),
        ),
    ]
    bad_result = evaluate_probes(subject_code="math", probes=bad_probes, chunks=chunks, top_k=5)
    assert not bad_result.passes_threshold, (
        "Math-6 benchmark при recall=0 должен блокировать pilot visibility"
    )


def test_retrieval_benchmark_result_serializes():
    """Serialization для audit JSON (Sprint 6: failed retrieval cases публикуются в audit)."""
    result = RetrievalBenchmarkResult(
        subject_code="math",
        top_k=5,
        recall_at_k=0.5,
        mrr_at_k=0.3,
        hits=2,
        total=4,
        failed_probes=["m3", "m4"],
    )
    # Result dataclass — публично сериализуем через __dict__ для JSON.
    blob = {
        "subject_code": result.subject_code,
        "top_k": result.top_k,
        "recall_at_k": result.recall_at_k,
        "mrr_at_k": result.mrr_at_k,
        "hits": result.hits,
        "total": result.total,
        "failed_probes": result.failed_probes,
    }
    assert blob["subject_code"] == "math"
    assert blob["failed_probes"] == ["m3", "m4"]
    assert blob["recall_at_k"] == 0.5
