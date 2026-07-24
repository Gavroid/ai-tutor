"""Sprint 43 (real): RAG benchmark через production БД.

Подключается к PostgreSQL на 192.168.1.86 (LAN).
Использует **реальный** RAG (app.rag.query) и реальные chunks.

Sprint 43 ограничения:
- 4GB RAM (LXC) — НЕ загружаем sentence-transformers.
- Используем hash-based embeddings (текущий prod fallback).
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

# Прямой импорт — обходим app.config (нужны env vars).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Sprint 43: env vars ДО app import.
os.environ.setdefault("APP_SECRET_KEY", "benchmark-no-secret-needed")
os.environ.setdefault("APP_ENV", "production")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://tutor:PTCYGF8x4NoK_V2LkPHjVQy1y2F03zv7@192.168.1.86:5432/tutor")
os.environ.setdefault("AI_API_KEY", "benchmark-mock")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from app.rag import _hash_embedding
from app.rag_persist import search_persistent
from app.db.session import SessionLocal
from scripts.rag_benchmark import GROUND_TRUTH, make_report, run_benchmark


def real_retriever(query: str, k: int = 5) -> list[dict]:
    """Sprint 43 (real): production RAG.

    Использует persistent search (rag_chunks в PostgreSQL) + hash-based embeddings.
    """
    try:
        # Sprint 43: hash-based (4GB RAM недостаточно для real embeddings).
        query_emb = _hash_embedding(query, dim=384)

        # Persistent search через rag_chunks (2770 chunks на prod).
        with SessionLocal() as db:
            results = search_persistent(db, query_emb, top_k=k)

        # Normalize к нашему schema
        return [
            {
                "topic_id": r.metadata.get("topic_id") if isinstance(r.metadata, dict) else None,
                "topic_name": r.metadata.get("material_title", "?") if isinstance(r.metadata, dict) else "?",
                "score": 0.0,  # search_persistent не возвращает score в PersistentChunk
                "text": r.text,
            }
            for r in results
        ]
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/RAG-BENCHMARK-REAL.md")
    parser.add_argument("--n-questions", type=int, default=30)
    args = parser.parse_args()

    print(f"Sprint 43 RAG benchmark (REAL — production DB @ 192.168.1.86)")
    print(f"Вопросов: {args.n_questions}")

    # Limit questions if requested
    if args.n_questions < len(GROUND_TRUTH):
        import scripts.rag_benchmark as bm_module
        bm_module.GROUND_TRUTH = bm_module.GROUND_TRUTH[: args.n_questions]

    results = run_benchmark(real_retriever)
    report = make_report(results)

    with open(args.output, "w") as f:
        f.write(report)
    print(f"\nReport сохранён в {args.output}")
    print(f"Recall@3: {results['recall_at_3']:.2%}")
    print(f"Recall@5: {results['recall_at_5']:.2%}")
    print(f"MRR: {results['mrr']:.3f}")