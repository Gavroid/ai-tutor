"""Durable local SQLite import target for Algebra extracted-text rows.

Writes verified exact-asset extracted text material/chunk rows to a caller-owned
SQLite file, reads them back for metadata audit/readiness snapshot, and supports
cleanup. It never uses the configured application database or mutates production.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from sqlalchemy import Column, Integer, MetaData, String, Table, Text, create_engine, delete, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from scripts.algebra_extracted_text_import_dry_run import build_extracted_text_import_manifest
from scripts.rag_metadata_audit import audit_rows, summarize_audit


def _tables(metadata: MetaData) -> tuple[Table, Table]:
    materials = Table(
        "learning_materials_local_import",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("topic_id", Integer, nullable=False),
        Column("subject_code", String(50), nullable=False),
        Column("title", String(300), nullable=False),
        Column("content", Text, nullable=False),
        Column("source", String(300), nullable=False),
        Column("source_url", Text, nullable=False),
        Column("source_section", Text, nullable=False),
        Column("license", String(80), nullable=False),
        Column("attribution", Text, nullable=False),
        Column("status", String(40), nullable=False),
    )
    chunks = Table(
        "rag_chunks_local_import",
        metadata,
        Column("id", String(100), primary_key=True),
        Column("material_id", Integer, nullable=False),
        Column("hash", String(64), nullable=False),
        Column("text", Text, nullable=False),
        Column("embedding_json", Text, nullable=False),
        Column("metadata_json", Text, nullable=False),
    )
    return materials, chunks


def _engine(db_path: Path) -> tuple[Engine, Table, Table]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    metadata = MetaData()
    materials, chunks = _tables(metadata)
    metadata.create_all(engine)
    return engine, materials, chunks


def run_extracted_text_import_target(*, db_path: Path, probe_manifest: dict[str, object]) -> dict[str, object]:
    """Commit extracted-text dry-run rows into a local SQLite file."""
    manifest = build_extracted_text_import_manifest(probe_manifest=probe_manifest)
    materials = cast(list[dict[str, Any]], manifest["materials"])
    chunks = cast(list[dict[str, Any]], manifest["chunks"])
    engine, materials_table, chunks_table = _engine(db_path)
    with Session(engine) as session:
        with session.begin():
            session.execute(delete(chunks_table))
            session.execute(delete(materials_table))
            for material in materials:
                session.execute(materials_table.insert().values(**material))
            for chunk in chunks:
                session.execute(chunks_table.insert().values(**chunk))
        material_count = session.scalar(select(func.count()).select_from(materials_table)) or 0
        chunk_count = session.scalar(select(func.count()).select_from(chunks_table)) or 0
    audit_rows_payload = read_extracted_text_audit_rows(db_path=db_path)
    metadata_audit = summarize_audit(audit_rows(audit_rows_payload, expected_subject_code="algebra"))
    engine.dispose()
    return {
        "mode": "extracted_text_durable_local_import_target",
        "db_path": str(db_path),
        "topic_count": manifest["topic_count"],
        "material_count": int(material_count),
        "chunk_count": int(chunk_count),
        "metadata_audit": metadata_audit,
        "production_mutation": False,
        "promotion_allowed": False,
        "readiness_decision": "keep_preview_extracted_text_durable_local_only",
    }


def read_extracted_text_audit_rows(*, db_path: Path) -> list[dict[str, object]]:
    """Read local extracted-text import rows in rag_metadata_audit shape."""
    engine, materials_table, chunks_table = _engine(db_path)
    stmt = (
        select(
            chunks_table.c.id.label("chunk_id"),
            chunks_table.c.material_id,
            chunks_table.c.metadata_json,
            materials_table.c.topic_id.label("material_topic_id"),
            materials_table.c.title.label("material_title"),
            materials_table.c.subject_code.label("material_subject_code"),
        )
        .join(materials_table, materials_table.c.id == chunks_table.c.material_id)
        .order_by(materials_table.c.topic_id)
    )
    with Session(engine) as session:
        rows = [dict(row._mapping) for row in session.execute(stmt).all()]
    engine.dispose()
    return rows


def cleanup_extracted_text_import_target(*, db_path: Path) -> dict[str, int]:
    """Delete local extracted-text import rows while preserving the DB file."""
    engine, materials_table, chunks_table = _engine(db_path)
    with Session(engine) as session:
        with session.begin():
            chunks_deleted = session.execute(delete(chunks_table)).rowcount or 0
            materials_deleted = session.execute(delete(materials_table)).rowcount or 0
        material_count_after = session.scalar(select(func.count()).select_from(materials_table)) or 0
        chunk_count_after = session.scalar(select(func.count()).select_from(chunks_table)) or 0
    engine.dispose()
    return {
        "materials_deleted": int(materials_deleted),
        "chunks_deleted": int(chunks_deleted),
        "material_count_after": int(material_count_after),
        "chunk_count_after": int(chunk_count_after),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run durable local Algebra extracted-text import")
    parser.add_argument("--db-path", default="/tmp/ai-tutor-algebra-extracted-text-import.sqlite3")
    parser.add_argument("--probe-json")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    db_path = Path(args.db_path)
    if args.cleanup:
        print(json.dumps(cleanup_extracted_text_import_target(db_path=db_path), ensure_ascii=False, indent=2))
        return 0
    if not args.probe_json:
        raise SystemExit("--probe-json is required unless --cleanup is used")
    probe = json.loads(Path(args.probe_json).read_text(encoding="utf-8"))
    if not isinstance(probe, dict):
        raise ValueError("--probe-json must contain an object")
    result = run_extracted_text_import_target(db_path=db_path, probe_manifest=probe)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    audit_summary = cast(dict[str, object], result["metadata_audit"])
    return 0 if audit_summary["bad_rows"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
