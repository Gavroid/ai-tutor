"""Sprint 57: BM25 benchmark на production (real data).

Тестирует BM25 search на 30 ground truth вопросов из Sprint 43.
Сравнивает Recall@3, Recall@5, MRR с hash-based (Sprint 43: 0%).
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

# Env vars ДО app import.
os.environ.setdefault("APP_SECRET_KEY", "benchmark-secret-key-for-rag-benchmark-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("AI_API_KEY", "mock-for-rag-benchmark")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

sys.path.insert(0, "/app")
sys.path.insert(0, "/tmp")

# Real production DB.
os.environ["DATABASE_URL"] = "postgresql+psycopg2://tutor:PTCYGF8x4NoK_V2LkPHjVQy1y2F03zv7@db:5432/tutor"

from app.rag_persist import search_bm25_persistent  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

# 30 ground truth вопросов (из Sprint 43).
GROUND_TRUTH = [
    # Math
    {"q": "Что такое переменная?", "expected_subject": "Math"},
    {"q": "Как решать линейные уравнения?", "expected_subject": "Math"},
    {"q": "Что такое теорема Пифагора?", "expected_subject": "Math"},
    # Russian
    {"q": "Что такое существительное?", "expected_subject": "Russian"},
    {"q": "Как определить спряжение глагола?", "expected_subject": "Russian"},
    {"q": "Что такое причастный оборот?", "expected_subject": "Russian"},
    # English
    {"q": "What is Past Simple?", "expected_subject": "English"},
    {"q": "How to use articles a/an/the?", "expected_subject": "English"},
    {"q": "What is Present Perfect?", "expected_subject": "English"},
    # Biology
    {"q": "Что такое фотосинтез?", "expected_subject": "Biology"},
    {"q": "Как устроена клетка?", "expected_subject": "Biology"},
    {"q": "Что такое ДНК?", "expected_subject": "Biology"},
    # History
    {"q": "Когда была Куликовская битва?", "expected_subject": "History"},
    {"q": "Что такое Реформация?", "expected_subject": "History"},
    {"q": "Когда отменили крепостное право?", "expected_subject": "History"},
    # Geography
    {"q": "Что такое атмосферное давление?", "expected_subject": "Geography"},
    {"q": "Самые большие страны мира?", "expected_subject": "Geography"},
    {"q": "Что такое течение Гольфстрим?", "expected_subject": "Geography"},
    # Physics
    {"q": "Что такое сила тяжести?", "expected_subject": "Physics"},
    {"q": "Закон Ньютона?", "expected_subject": "Physics"},
    {"q": "Что такое электрический ток?", "expected_subject": "Physics"},
    # Chemistry
    {"q": "Что такое атом?", "expected_subject": "Chemistry"},
    {"q": "Что такое химическая реакция?", "expected_subject": "Chemistry"},
    {"q": "Периодический закон Менделеева?", "expected_subject": "Chemistry"},
    # Informatics
    {"q": "Что такое переменная в Python?", "expected_subject": "Informatics"},
    {"q": "Как работает цикл for?", "expected_subject": "Informatics"},
    {"q": "Что такое алгоритм?", "expected_subject": "Informatics"},
    # Cross-subject keywords
    {"q": "Переменная Python типы данных", "expected_subject": "Informatics"},
    {"q": "Москва Кремль история", "expected_subject": "History"},
    {"q": "Вода кислород химия", "expected_subject": "Chemistry"},
]


def _recall_at_k(retrieved: list, expected_subject: str, k: int) -> int:
    """Sprint 57: 1 если expected subject в top-K, иначе 0.

    BM25 возвращает PersistentChunk, metadata содержит material_title.
    Subject определяем по material_title (если содержит subject name).
    """
    top_k_titles = [
        r.metadata.get("material_title", "").lower()
        for r in retrieved[:k]
    ]
    # Subject matching: проверяем keywords в title
    subject_keywords = {
        "math": ["математика", "алгебра", "геометрия"],
        "russian": ["русский", "литература"],
        "english": ["english", "английский"],
        "biology": ["биология"],
        "history": ["история"],
        "geography": ["география"],
        "physics": ["физика"],
        "chemistry": ["химия"],
        "informatics": ["информатика", "python"],
    }
    keywords = subject_keywords.get(expected_subject.lower(), [])
    return 1 if any(any(kw in title for kw in keywords) for title in top_k_titles) else 0


def _reciprocal_rank(retrieved: list, expected_subject: str) -> float:
    """Sprint 57: 1/rank первого relevant result."""
    subject_keywords = {
        "math": ["математика", "алгебра", "геометрия"],
        "russian": ["русский", "литература"],
        "english": ["english", "английский"],
        "biology": ["биология"],
        "history": ["история"],
        "geography": ["география"],
        "physics": ["физика"],
        "chemistry": ["химия"],
        "informatics": ["информатика", "python"],
    }
    keywords = subject_keywords.get(expected_subject.lower(), [])
    for i, r in enumerate(retrieved):
        title = r.metadata.get("material_title", "").lower()
        if any(kw in title for kw in keywords):
            return 1.0 / (i + 1)
    return 0.0


def run_benchmark() -> dict[str, Any]:
    """Sprint 57: BM25 benchmark на production."""
    recall_at_3_sum = 0
    recall_at_5_sum = 0
    mrr_sum = 0.0
    per_question: list[dict[str, Any]] = []
    start = time.time()

    for item in GROUND_TRUTH:
        q = item["q"]
        with SessionLocal() as db:
            results = search_bm25_persistent(db, q, top_k=5)

        r3 = _recall_at_k(results, item["expected_subject"], 3)
        r5 = _recall_at_k(results, item["expected_subject"], 5)
        rr = _reciprocal_rank(results, item["expected_subject"])

        recall_at_3_sum += r3
        recall_at_5_sum += r5
        mrr_sum += rr

        per_question.append({
            "q": q,
            "expected_subject": item["expected_subject"],
            "results_count": len(results),
            "top_titles": [r.metadata.get("material_title", "?") for r in results[:3]],
            "recall@3": r3,
            "recall@5": r5,
            "reciprocal_rank": rr,
        })

    elapsed = time.time() - start
    n = len(GROUND_TRUTH)
    return {
        "n_questions": n,
        "recall_at_3": recall_at_3_sum / n,
        "recall_at_5": recall_at_5_sum / n,
        "mrr": mrr_sum / n,
        "elapsed_seconds": elapsed,
        "per_question": per_question,
    }


def make_report(results: dict[str, Any]) -> str:
    """Sprint 57: markdown report."""
    lines = [
        "# Sprint 57 — BM25 RAG Benchmark Report",
        "",
        f"**Дата:** 2026-07-26",
        f"**Production:** 192.168.1.86 (LXC, 4GB RAM)",
        f"**RAG mode:** BM25 keyword search (без embeddings)",
        f"**Total questions:** {results['n_questions']}",
        f"**Elapsed:** {results['elapsed_seconds']:.2f}s",
        "",
        "## Метрики (Sprint 57 BM25 vs Sprint 43 hash-based)",
        "",
        f"| Метрика | Sprint 43 (hash) | Sprint 57 (BM25) | Δ |",
        f"|---------|------------------|------------------|---|",
        f"| Recall@3 | 0.00% | {results['recall_at_3']:.2%} | +{results['recall_at_3']*100:.0f}pp |",
        f"| Recall@5 | 0.00% | {results['recall_at_5']:.2%} | +{results['recall_at_5']*100:.0f}pp |",
        f"| MRR | 0.000 | {results['mrr']:.3f} | +{results['mrr']:.3f} |",
        "",
    ]

    # Per-subject breakdown
    by_subject: dict[str, list[dict]] = {}
    for q in results["per_question"]:
        by_subject.setdefault(q["expected_subject"], []).append(q)

    lines.append("## По предметам\n")
    lines.append("| Subject | n | Recall@3 | Recall@5 | MRR |")
    lines.append("|---------|---|----------|----------|-----|")
    for subject, qs in sorted(by_subject.items()):
        n = len(qs)
        r3 = sum(q["recall@3"] for q in qs) / n
        r5 = sum(q["recall@5"] for q in qs) / n
        mrr = sum(q["reciprocal_rank"] for q in qs) / n
        lines.append(f"| {subject} | {n} | {r3:.2%} | {r5:.2%} | {mrr:.3f} |")

    # Successful queries
    successful = [q for q in results["per_question"] if q["recall@5"] > 0]
    lines.append(f"\n## Successful queries (Recall@5 > 0): {len(successful)}/{results['n_questions']}\n")
    for q in successful[:5]:
        lines.append(f"- **{q['q']}** → top: {q['top_titles'][0] if q['top_titles'] else '?'}")

    # Failed queries
    failed = [q for q in results["per_question"] if q["recall@5"] == 0]
    if failed:
        lines.append(f"\n## Failed queries: {len(failed)}/{results['n_questions']}\n")
        for q in failed[:5]:
            lines.append(f"- **{q['q']}** (expected: {q['expected_subject']})")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print("Sprint 57: BM25 RAG benchmark (production @ 192.168.1.86)")
    print(f"Вопросов: {len(GROUND_TRUTH)}")
    results = run_benchmark()
    report = make_report(results)

    with open("/tmp/rag_bench_bm25.md", "w") as f:
        f.write(report)
    print(f"\nReport сохранён в /tmp/rag_bench_bm25.md")
    print(f"Recall@3: {results['recall_at_3']:.2%}")
    print(f"Recall@5: {results['recall_at_5']:.2%}")
    print(f"MRR: {results['mrr']:.3f}")
    print(f"Elapsed: {results['elapsed_seconds']:.2f}s")