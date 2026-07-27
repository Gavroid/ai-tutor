"""Sprint 70: backfill embeddings for existing 2770 chunks.

Использует sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2, 384 dim)
для backfill embeddings в PersistentChunk.

Note: chunks пока хранят hash embeddings (для backward compat).
Sprint 71+ заменит hash-based search на real embeddings.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

# Добавляем backend в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

os.environ.setdefault("APP_ENV", "production")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

# Production DATABASE_URL
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://tutor:PTCYGF8x4NoK_V2LkPHjVQy1y2F03zv7@db:5432/tutor",
)
os.environ.setdefault("APP_SECRET_KEY", "backfill-secret-do-not-use-in-prod")

import json
import logging

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sprint70_backfill")


def main():
    parser = argparse.ArgumentParser(description="Backfill RAG embeddings")
    parser.add_argument("--batch-size", type=int, default=32, help="Encoding batch size")
    parser.add_argument("--limit", type=int, default=None, help="Limit chunks (для теста)")
    args = parser.parse_args()

    logger.info("Sprint 70: Backfill embeddings для RAG chunks")

    from app.rag_embeddings import encode_texts, EMBEDDING_DIM
    from app.db.session import SessionLocal
    from app.rag_models import RagChunk

    if encode_texts(["test"]) is None:
        logger.error("sentence-transformers unavailable! Aborting.")
        sys.exit(1)

    logger.info(f"EMBEDDING_DIM = {EMBEDDING_DIM}")

    # Get all chunks
    with SessionLocal() as db:
        query = db.query(RagChunk).order_by(RagChunk.id)
        if args.limit:
            query = query.limit(args.limit)
        chunks = query.all()
        total = len(chunks)
        logger.info(f"Found {total} chunks для backfill")

        # Process in batches
        start = time.time()
        processed = 0
        for batch_start in range(0, total, args.batch_size):
            batch = chunks[batch_start : batch_start + args.batch_size]
            texts = [c.text for c in batch]

            # Encode
            vectors = encode_texts(texts)
            if vectors is None:
                logger.error(f"Encoding failed for batch {batch_start}")
                continue

            # Save to metadata_json (existing column)
            for chunk, vector in zip(batch, vectors):
                # Save embedding в metadata_json как additional field
                try:
                    metadata = json.loads(chunk.metadata_json) if chunk.metadata_json else {}
                except json.JSONDecodeError:
                    metadata = {}

                metadata["embedding_v2"] = vector.tolist()
                metadata["embedding_model"] = "paraphrase-multilingual-MiniLM-L12-v2"
                metadata["embedding_dim"] = EMBEDDING_DIM
                chunk.metadata_json = json.dumps(metadata)

            db.commit()
            processed += len(batch)
            elapsed = time.time() - start
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total - processed) / rate if rate > 0 else 0
            logger.info(
                f"Processed {processed}/{total} ({processed*100//total}%), "
                f"rate={rate:.1f} chunks/sec, ETA={eta:.0f}s"
            )

        logger.info(f"Backfill DONE: {processed} chunks in {time.time()-start:.1f}s")


if __name__ == "__main__":
    main()
