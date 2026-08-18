"""Disposable Algebra import rehearsal in isolated SQLite.

This module proves material/chunk-shaped rows can be inserted and rolled back in
an isolated in-memory database. It never touches the application's configured
production database.
"""
from __future__ import annotations

import argparse
import json
from typing import Any, Sequence, cast

from sqlalchemy import Column, Integer, MetaData, String, Table, Text, create_engine, func, select
from sqlalchemy.orm import Session

from scripts.algebra_local_import_dry_run import build_local_import_manifest
from scripts.rag_metadata_audit import audit_rows, summarize_audit


def _tables(metadata: MetaData) -> tuple[Table, Table]:
    materials = Table(
        "learning_materials_rehearsal",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("topic_id", Integer, nullable=False),
        Column("subject_code", String(50), nullable=False),
        Column("title", String(300), nullable=False),
        Column("content", Text, nullable=False),
        Column("source", String(300), nullable=False),
        Column("status", String(30), nullable=False),
    )
    chunks = Table(
        "rag_chunks_rehearsal",
        metadata,
        Column("id", String(100), primary_key=True),
        Column("material_id", Integer, nullable=False),
        Column("hash", String(64), nullable=False),
        Column("text", Text, nullable=False),
        Column("embedding_json", Text, nullable=False),
        Column("metadata_json", Text, nullable=False),
    )
    return materials, chunks


def run_disposable_import_rehearsal(*, topic_ids: Sequence[int] | None = None) -> dict[str, object]:
    """Insert local dry-run rows into an isolated DB transaction and roll back."""
    manifest = build_local_import_manifest(topic_ids=topic_ids)
    materials = cast(list[dict[str, Any]], manifest["materials"])
    chunks = cast(list[dict[str, Any]], manifest["chunks"])
    audit_input_rows = cast(list[dict[str, object]], manifest["audit_rows"])
    metadata = MetaData()
    materials_table, chunks_table = _tables(metadata)
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    metadata.create_all(engine)

    with Session(engine) as session:
        tx = session.begin()
        try:
            for material in materials:
                session.execute(
                    materials_table.insert().values(
                        id=material["id"],
                        topic_id=material["topic_id"],
                        subject_code=material["subject_code"],
                        title=material["title"],
                        content=f"Local rehearsal content for topic {material['topic_id']}",
                        source=material["source"],
                        status=material["status"],
                    )
                )
            for chunk in chunks:
                session.execute(chunks_table.insert().values(**chunk))
            session.flush()
            material_count_before = session.scalar(select(func.count()).select_from(materials_table)) or 0
            chunk_count_before = session.scalar(select(func.count()).select_from(chunks_table)) or 0
            findings = audit_rows(audit_input_rows, expected_subject_code="algebra")
            metadata_audit = summarize_audit(findings)
        finally:
            tx.rollback()

        material_count_after = session.scalar(select(func.count()).select_from(materials_table)) or 0
        chunk_count_after = session.scalar(select(func.count()).select_from(chunks_table)) or 0

    engine.dispose()
    return {
        "mode": "disposable_sqlite_import_rehearsal",
        "topic_count": manifest["topic_count"],
        "material_count_before_rollback": int(material_count_before),
        "chunk_count_before_rollback": int(chunk_count_before),
        "material_count_after_rollback": int(material_count_after),
        "chunk_count_after_rollback": int(chunk_count_after),
        "metadata_audit": metadata_audit,
        "production_mutation": False,
        "promotion_allowed": False,
        "readiness_decision": "keep_preview_disposable_rehearsal_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run disposable SQLite Algebra import rehearsal")
    parser.add_argument("--topic", action="append", type=int, default=[])
    args = parser.parse_args()
    result = run_disposable_import_rehearsal(topic_ids=args.topic or None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    audit_summary = cast(dict[str, object], result["metadata_audit"])
    return 0 if audit_summary["bad_rows"] == 0 and result["material_count_after_rollback"] == 0 and result["chunk_count_after_rollback"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
