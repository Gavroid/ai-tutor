"""Sprint 70: RAG benchmark с REAL embeddings (sentence-transformers).

Подключается к PostgreSQL на 192.168.1.86 (LAN).
Использует embeddings из metadata_json["embedding_v2"] (backfilled в Sprint 70).

Sprint 70 vs Sprint 57 BM25:
- Expected Recall@3: 10% → 60-80%
- Использует real cosine similarity на 384-dim vectors
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("APP_SECRET_KEY", "benchmark-no-secret-needed")
os.environ.setdefault("APP_ENV", "production")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://tutor:PTCYGF8x4NoK_V2LkPHjVQy1y2F03zv7@192.168.1.86:5432/tutor",
)
os.environ.setdefault("AI_API_KEY", "benchmark-mock")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import numpy as np

from app.db.session import SessionLocal
from app.rag_models import RagChunk
from app.rag_embeddings import encode_single
from scripts.rag_benchmark import GROUND_TRUTH


def real_retriever(query: str, k: int = 5) -> list[dict]:
    """Sprint 70: real embeddings-based RAG."""
    try:
        query_vec = encode_single(query)
        if query_vec is None:
            return []
        query_np = np.array(query_vec)

        with SessionLocal() as db:
            chunks = (
                db.query(RagChunk)
                .filter(RagChunk.metadata_json.like("%embedding_v2%"))
                .all()
            )

            scored = []
            for chunk in chunks:
                try:
                    metadata = json.loads(chunk.metadata_json) if chunk.metadata_json else {}
                    chunk_vec = metadata.get("embedding_v2")
                    if not chunk_vec:
                        continue
                    chunk_np = np.array(chunk_vec)
                    score = float(np.dot(query_np, chunk_np))
                    scored.append((score, chunk))
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue

            scored.sort(key=lambda x: x[0], reverse=True)
            top_k = scored[:k]
            return [
                {
                    "topic_id": json.loads(c.metadata_json).get("topic_id")
                    if c.metadata_json
                    else None,
                    "topic_name": json.loads(c.metadata_json).get("material_title", "?")
                    if c.metadata_json
                    else "?",
                    "score": float(score),
                }
                for score, c in top_k
            ]
    except Exception as e:
        print(f"Error: {e}")
        return []


def run_inline_benchmark(questions: list[dict]) -> dict[str, Any]:
    """Inline benchmark runner (не зависит от run_benchmark signature)."""
    recall_at_3_sum = 0
    recall_at_5_sum = 0
    mrr_sum = 0.0

    for item in questions:
        q = item["q"]
        try:
            results = real_retriever(q, k=5)
        except Exception as e:
            print(f"  Error for '{q}': {e}")
            continue

        # Recall@3: expected в top-3?
        top_3_titles = [r.get("topic_name", "").lower() for r in results[:3]]
        top_5_titles = [r.get("topic_name", "").lower() for r in results[:5]]

        expected_subject = item["expected_subject"].lower()
        # Sprint 70: match by subject keywords
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
        keywords = subject_keywords.get(expected_subject, [])

        recall_3 = 1 if any(any(kw in t for kw in keywords) for t in top_3_titles) else 0
        recall_5 = 1 if any(any(kw in t for kw in keywords) for t in top_5_titles) else 0

        # MRR: rank of first relevant
        mrr = 0.0
        for i, t in enumerate(top_5_titles):
            if any(kw in t for kw in keywords):
                mrr = 1.0 / (i + 1)
                break

        recall_at_3_sum += recall_3
        recall_at_5_sum += recall_5
        mrr_sum += mrr

    n = len(questions)
    return {
        "recall_at_3": recall_at_3_sum / n if n else 0,
        "recall_at_5": recall_at_5_sum / n if n else 0,
        "mrr": mrr_sum / n if n else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Sprint 70 RAG benchmark")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    print("Sprint 70: RAG benchmark с REAL embeddings")
    print("=" * 60)
    print(f"Total questions: {len(GROUND_TRUTH)}")

    questions = GROUND_TRUTH[: args.limit] if args.limit else GROUND_TRUTH
    start = time.time()
    results = run_inline_benchmark(questions)
    elapsed = time.time() - start

    print(f"\nBenchmark completed in {elapsed:.1f}s")
    print(f"Recall@3: {results['recall_at_3']:.2%}")
    print(f"Recall@5: {results['recall_at_5']:.2%}")
    print(f"MRR: {results['mrr']:.3f}")

    # Save report
    report = f"""# Sprint 70 — RAG Benchmark с REAL Embeddings

**Дата:** 2026-07-26
**Production:** 192.168.1.86
**Model:** paraphrase-multilingual-MiniLM-L12-v2 (384-dim)
**Chunks:** 2770 (Sprint 70 backfill)

## Метрики

| Метрика | Sprint 43 (hash) | Sprint 57 (BM25) | Sprint 70 (real) |
|---------|------------------|-------------------|------------------|
| Recall@3 | 0.00% | 10.00% | **{results['recall_at_3']:.2%}** |
| Recall@5 | 0.00% | 10.00% | **{results['recall_at_5']:.2%}** |
| MRR | 0.000 | 0.100 | **{results['mrr']:.3f}** |

## Sprint 70 vs Sprint 43 (hash-based)

- Recall@3: 0.00% → **{results['recall_at_3']:.2%}** (+{results['recall_at_3']*100:.0f}pp)
- Recall@5: 0.00% → **{results['recall_at_5']:.2%}** (+{results['recall_at_5']*100:.0f}pp)
- MRR: 0.000 → **{results['mrr']:.3f}** (+{results['mrr']:.3f})
"""
    output_path = "/root/workspace/ai-tutor/docs/RAG-BENCHMARK-REAL-EMBEDDINGS.md"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Write to a tmp first, then copy
    with open("/tmp/bench_report.md", "w") as f:
        f.write(report)
    print(f"\nReport saved: /tmp/bench_report.md")
    print("\n" + "=" * 60)
    print("Sprint 43 (hash) vs Sprint 70 (real embeddings):")
    print(f"  Recall@3: 0.00% → {results['recall_at_3']:.2%} (+{results['recall_at_3']*100:.0f}pp)")
    print(f"  Recall@5: 0.00% → {results['recall_at_5']:.2%} (+{results['recall_at_5']*100:.0f}pp)")
    print(f"  MRR:      0.000 → {results['mrr']:.3f} (+{results['mrr']:.3f})")


if __name__ == "__main__":
    main()
