"""Sprint 43 (real): RAG benchmark через SSH tunnel к production.

Sprint 43: PostgreSQL на prod слушает только на docker network.
С рабочей машины нет доступа к 192.168.1.86:5432.

Решение: SSH tunnel.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Env vars ДО app import.
os.environ.setdefault("APP_SECRET_KEY", "benchmark-secret-key-for-rag-benchmark-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("AI_API_KEY", "mock-for-rag-benchmark")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")


def start_ssh_tunnel(local_port: int = 5433) -> subprocess.Popen | None:
    """Sprint 43: SSH tunnel к prod PostgreSQL."""
    ssh_cmd = [
        "ssh",
        "-i", os.path.expanduser("~/.ssh/id_ed25519_kirill_ai"),
        "-o", "StrictHostKeyChecking=no",
        "-N",  # no command
        "-L", f"{local_port}:db:5432",  # local:remote:remote_port (db = docker name)
        "root@192.168.1.86",
    ]
    print(f"Starting SSH tunnel: {' '.join(ssh_cmd)}", file=sys.stderr)
    proc = subprocess.Popen(
        ssh_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)  # wait for tunnel
    return proc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/RAG-BENCHMARK.md")
    parser.add_argument("--n-questions", type=int, default=30)
    args = parser.parse_args()

    # Start tunnel
    proc = start_ssh_tunnel(local_port=5433)
    if proc is None:
        print("ERROR: SSH tunnel failed", file=sys.stderr)
        sys.exit(1)

    try:
        # Use local port
        os.environ["DATABASE_URL"] = "postgresql+psycopg2://tutor:PTCYGF8x4NoK_V2LkPHjVQy1y2F03zv7@127.0.0.1:5433/tutor"

        from app.rag import _hash_embedding
        from app.rag_persist import search_persistent
        from app.db.session import SessionLocal
        from scripts.rag_benchmark import GROUND_TRUTH, make_report, run_benchmark

        def real_retriever(query: str, k: int = 5) -> list[dict]:
            try:
                query_emb = _hash_embedding(query, dim=384)
                with SessionLocal() as db:
                    results = search_persistent(db, query_emb, top_k=k)
                return [
                    {
                        "topic_id": r.metadata.get("topic_id") if isinstance(r.metadata, dict) else None,
                        "topic_name": r.metadata.get("material_title", "?") if isinstance(r.metadata, dict) else "?",
                        "score": 0.0,
                        "text": r.text,
                    }
                    for r in results
                ]
            except Exception as e:
                print(f"  ERROR: {e}", file=sys.stderr)
                return []

        if args.n_questions < len(GROUND_TRUTH):
            import scripts.rag_benchmark as bm
            bm.GROUND_TRUTH = bm.GROUND_TRUTH[: args.n_questions]

        results = run_benchmark(real_retriever)
        report = make_report(results)

        with open(args.output, "w") as f:
            f.write(report)
        print(f"\nReport сохранён в {args.output}")
        print(f"Recall@3: {results['recall_at_3']:.2%}")
        print(f"Recall@5: {results['recall_at_5']:.2%}")
        print(f"MRR: {results['mrr']:.3f}")

    finally:
        # Cleanup tunnel
        if proc:
            proc.terminate()
            proc.wait(timeout=5)


if __name__ == "__main__":
    main()