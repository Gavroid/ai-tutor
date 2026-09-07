#!/usr/bin/env python3
"""Sprint 4 RAG (MVP): CLI для PDF → RAG ingest.

Usage:
    python3 scripts/rag_ingest.py MATERIAL_ID /path/to/file.pdf [--db-url URL]

Требует DATABASE_URL (PostgreSQL на проде, SQLite для тестов).
Идемпотентно: re-ingest того же PDF не дублирует chunks (hash-based dedup).

MVP scope (НЕ production data ingestion):
- Single PDF за раз
- Нет admin UI
- Нет async processing
- Нет OCR

Для production data ingestion нужен отдельный sprint + UI решения владельца.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Allow running as `python3 scripts/rag_ingest.py ...`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal  # noqa: E402
from app.rag_ingest import ingest_pdf  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sprint 4 RAG MVP: ingest PDF в rag_chunks.",
    )
    parser.add_argument(
        "material_id",
        type=int,
        help="LearningMaterial.id (FK в rag_chunks.material_id).",
    )
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Путь к PDF файлу.",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="DATABASE_URL (default: env DATABASE_URL или sqlite in-memory для тестов).",
    )

    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        logger.error("PDF не найден: %s", pdf_path)
        return 2

    db_url = args.db_url or os.environ.get("DATABASE_URL")
    if db_url and db_url != "sqlite:///:memory:":
        # Override SessionLocal engine для этой команды.
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(db_url)
        SessionLocal.configure(bind=engine)

    session = SessionLocal()
    try:
        n = ingest_pdf(args.material_id, pdf_path, session)
        logger.info("Sprint 4 RAG: готово. Создано %d chunks для material_id=%d", n, args.material_id)
        return 0
    except Exception as exc:
        logger.exception("Sprint 4 RAG: ingest failed: %s", exc)
        session.rollback()
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
