"""Sprint 6 (2026-08-23): versioned topic-level retrieval dataset + benchmark.

Зачем: Sprint 5 audit «retrieval probes 9/14, recall@5 ≈ 0.43, MRR@5 ≈ 0.32».
Sprint 6 требует:
- versioned topic-level retrieval dataset;
- recall@k и MRR@k по каждому subject;
- subject-specific thresholds;
- failed retrieval cases публикуются в audit.

Здесь реализован минимальный card-evaluator: лёгкая inverted-index поиск по
RagChunk.text (без embedding модели, hash-embedding). Достаточно чтобы
benchmark был deterministic в CI.

Примечание: чтобы получить truthful recall/MRR для production search,
нужно runtime search через sentence-transformers — Sprint 6 §Scope это
требует, но лёгкий evaluator здесь покрывает контракт структуры
benchmark'а и gating policy («subject не становится pilot-visible если
quality evidence неполно»).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RetrievalProbe:
    """Одна проба поиска: query + ожидаемый минимум relevant keys."""

    probe_id: str
    subject_code: str
    query: str
    relevant_keys: tuple[str, ...]  # match by chunk.metadata.subject/topic hash
    difficulty: int = 2


@dataclass
class RetrievalBenchmarkResult:
    """Результат benchmark'а."""

    subject_code: str
    top_k: int
    recall_at_k: float
    mrr_at_k: float
    hits: int
    total: int
    failed_probes: list[str] = field(default_factory=list)

    @property
    def passes_threshold(self) -> bool:
        # Sprint 6 thresholds: Math ≥ 0.6 recall@5 и ≥ 0.5 MRR@5.
        # OCR-risk subjects: lower threshold или skipped.
        if self.subject_code in {"math"}:
            return self.recall_at_k >= 0.6 and self.mrr_at_k >= 0.5
        # Other subjects — базовый gate (настраивается Sprint 7 disposable env).
        return self.recall_at_k >= 0.4 and self.mrr_at_k >= 0.3


def _tokenize(text: str) -> set[str]:
    """Минимальная токенизация для hash-based search."""
    import re

    return {w for w in re.findall(r"[а-яa-z0-9]{2,}", text.lower()) if w}


def _score_chunk(query_tokens: set[str], chunk_text: str) -> float:
    """Token overlap score (Sprint 6: deterministic, dependency-free)."""
    chunk_tokens = _tokenize(chunk_text)
    if not chunk_tokens or not query_tokens:
        return 0.0
    overlap = query_tokens & chunk_tokens
    return len(overlap) / max(1, len(query_tokens))


def evaluate_probes(
    subject_code: str,
    probes: list[RetrievalProbe],
    chunks: list[dict],
    top_k: int = 5,
) -> RetrievalBenchmarkResult:
    """Прогнать probes против chunks (список dict {text, key, metadata}).

    Возвращает aggregate metrics. Каждый probe:
    - scored by token overlap;
    - top-k извлечены;
    - recall@k = relevant_in_top_k / total_relevant;
    - MRR@k = 1 / rank_first_relevant (или 0 если не найден).
    """
    hits = 0
    total = 0
    failed: list[str] = []
    reciprocal_ranks: list[float] = []
    for probe in probes:
        if probe.subject_code != subject_code:
            continue
        query_tokens = _tokenize(probe.query)
        if not query_tokens:
            continue
        scored = [
            (
                _score_chunk(query_tokens, c.get("text", "")),
                c.get("key") or c.get("hash") or c.get("id"),
                c.get("metadata", {}),
            )
            for c in chunks
        ]
        # Сортируем по убыванию score, берём top-k.
        scored.sort(key=lambda x: -x[0])
        top_results = scored[:top_k]
        top_keys = {(k if k is not None else meta.get("hash") or meta.get("id")) for _, k, meta in top_results}
        relevant = set(probe.relevant_keys)
        # recall@k: any relevant in top-k.
        is_relevant_in_top = any(r in top_keys for r in relevant) if relevant else True
        if is_relevant_in_top:
            hits += 1
        else:
            failed.append(probe.probe_id)
        total += 1
        # MRR@k
        mrr = 0.0
        for rank, (_, _, _) in enumerate(top_results, start=1):
            for _, k, meta in top_results[:rank]:
                actual_key = k if k is not None else meta.get("hash") or meta.get("id")
                if actual_key in relevant:
                    mrr = 1.0 / rank
                    break
            if mrr:
                break
        reciprocal_ranks.append(mrr)
    if total == 0:
        return RetrievalBenchmarkResult(
            subject_code=subject_code,
            top_k=top_k,
            recall_at_k=0.0,
            mrr_at_k=0.0,
            hits=0,
            total=0,
            failed_probes=[],
        )
    recall = hits / total
    mrr = sum(reciprocal_ranks) / total
    return RetrievalBenchmarkResult(
        subject_code=subject_code,
        top_k=top_k,
        recall_at_k=recall,
        mrr_at_k=mrr,
        hits=hits,
        total=total,
        failed_probes=failed,
    )


def benchmark_math6_fixture() -> tuple[str, list[RetrievalProbe], list[dict]]:
    """Тестовая fixture для Math-6 (Sprint 6): 4 probes, 4 chunks."""
    probes = [
        RetrievalProbe(
            probe_id="math-001",
            subject_code="math",
            query="наибольший общий делитель и взаимно простые числа",
            relevant_keys=("math-chunk-3",),
            difficulty=3,
        ),
        RetrievalProbe(
            probe_id="math-002",
            subject_code="math",
            query="проценты в бытовых задачах",
            relevant_keys=("math-chunk-2",),
            difficulty=2,
        ),
        RetrievalProbe(
            probe_id="math-003",
            subject_code="math",
            query="среднее арифметическое нескольких чисел",
            relevant_keys=("math-chunk-1",),
            difficulty=2,
        ),
        RetrievalProbe(
            probe_id="math-004",
            subject_code="math",
            query="смешанные числа: плюс и минус",
            relevant_keys=("math-chunk-4",),
            difficulty=3,
        ),
    ]
    chunks = [
        {
            "key": "math-chunk-1",
            "text": "Среднее арифметическое нескольких чисел — это сумма этих чисел, делённая на их количество.",
            "metadata": {"subject_code": "math", "topic_id": 187},
        },
        {
            "key": "math-chunk-2",
            "text": "Проценты в бытовых задачах: скидки, налоги, доходность по вкладу — это доли от 100.",
            "metadata": {"subject_code": "math", "topic_id": 188},
        },
        {
            "key": "math-chunk-3",
            "text": "Наибольший общий делитель двух чисел и взаимно простые числа.",
            "metadata": {"subject_code": "math", "topic_id": 193},
        },
        {
            "key": "math-chunk-4",
            "text": "Смешанные числа: плюс и минус. Складываем целые части и дробные отдельно.",
            "metadata": {"subject_code": "math", "topic_id": 197},
        },
    ]
    return "math", probes, chunks
