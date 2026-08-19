"""Production-shaped Algebra source/RAG import runner with fail-closed guards.

The default mode is dry-run. Production writes require an explicit flag and are
still blocked by the higher-level execution-plan gate before this script should
be used. This module is intentionally small and auditable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from sqlalchemy import Column, Integer, MetaData, String, Table, Text, create_engine, delete, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from scripts.rag_metadata_audit import audit_rows, summarize_audit


def _tables(metadata: MetaData) -> tuple[Table, Table]:
    materials = Table(
        "learning_materials",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("topic_id", Integer, nullable=False, index=True),
        Column("title", String(300), nullable=False),
        Column("content", Text, nullable=False),
        Column("source", String(300), nullable=True),
        Column("file_path", String(500), nullable=True),
        Column("status", String(30), nullable=False),
        Column("source_type", String(20), nullable=False),
        Column("ai_confidence", Text, nullable=True),
    )
    chunks = Table(
        "rag_chunks",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("material_id", Integer, nullable=False, index=True),
        Column("hash", String(64), nullable=False, unique=True),
        Column("text", Text, nullable=False),
        Column("embedding_json", Text, nullable=False),
        Column("metadata_json", Text, nullable=False),
    )
    return materials, chunks


def _engine(db_url: str) -> tuple[Engine, Table, Table]:
    engine = create_engine(db_url, future=True)
    metadata = MetaData()
    materials, chunks = _tables(metadata)
    metadata.create_all(engine)
    return engine, materials, chunks


def _audit_manifest(manifest: dict[str, object]) -> dict[str, object]:
    rows = cast(list[dict[str, object]], manifest.get("audit_rows") or [])
    if not rows:
        rows = []
        materials_by_id = {
            int(cast(Any, material["id"])): material
            for material in cast(list[dict[str, Any]], manifest.get("materials") or [])
        }
        for chunk in cast(list[dict[str, Any]], manifest.get("chunks") or []):
            material = materials_by_id[int(cast(Any, chunk["material_id"]))]
            rows.append(
                {
                    "chunk_id": chunk["id"],
                    "material_id": chunk["material_id"],
                    "material_title": material["title"],
                    "material_topic_id": material["topic_id"],
                    "material_subject_code": "algebra",
                    "metadata_json": chunk["metadata_json"],
                }
            )
    return summarize_audit(audit_rows(rows, expected_subject_code="algebra"))


def build_algebra_import_plan(*, manifest: dict[str, object], target_env: str, dry_run: bool = True) -> dict[str, object]:
    """Build an auditable import plan from extracted-text material/chunk rows."""
    materials = cast(list[dict[str, Any]], manifest.get("materials") or [])
    chunks = cast(list[dict[str, Any]], manifest.get("chunks") or [])
    metadata_audit = _audit_manifest(manifest)
    return {
        "subject": "algebra",
        "target_env": target_env,
        "dry_run": dry_run,
        "material_count": len(materials),
        "chunk_count": len(chunks),
        "metadata_audit": metadata_audit,
        "production_mutation": False,
        "promotion_allowed": False,
    }


def execute_algebra_import_plan(
    *,
    manifest: dict[str, object],
    target_env: str,
    db_url: str,
    dry_run: bool = True,
    allow_production: bool = False,
) -> dict[str, object]:
    """Execute a guarded Algebra import against a caller-provided DB URL."""
    blockers: list[str] = []
    if target_env == "production" and not allow_production:
        blockers.append("allow_production_not_set")
    if target_env not in {"staging", "production"}:
        blockers.append("target_not_staging_or_production")
    plan = build_algebra_import_plan(manifest=manifest, target_env=target_env, dry_run=dry_run)
    metadata_audit = cast(dict[str, object], plan["metadata_audit"])
    if int(cast(Any, metadata_audit["bad_rows"])) != 0:
        blockers.append("metadata_audit_failed")
    if blockers:
        return {**plan, "decision": "block_import", "rows_written": 0, "blockers": blockers}
    if dry_run:
        return {**plan, "decision": "dry_run_only", "rows_written": 0, "blockers": []}

    materials = cast(list[dict[str, Any]], manifest.get("materials") or [])
    chunks = cast(list[dict[str, Any]], manifest.get("chunks") or [])
    engine, materials_table, chunks_table = _engine(db_url)
    topic_ids = [int(cast(Any, material["topic_id"])) for material in materials]
    with Session(engine) as session:
        with session.begin():
            if topic_ids:
                existing_material_ids = list(
                    session.execute(
                        select(materials_table.c.id).where(materials_table.c.topic_id.in_(topic_ids))
                    ).scalars()
                )
                if existing_material_ids:
                    session.execute(delete(chunks_table).where(chunks_table.c.material_id.in_(existing_material_ids)))
                    session.execute(delete(materials_table).where(materials_table.c.id.in_(existing_material_ids)))
            for material in materials:
                session.execute(
                    materials_table.insert().values(
                        id=material["id"],
                        topic_id=material["topic_id"],
                        title=material["title"],
                        content=material["content"],
                        source=str(material.get("source_url") or material.get("source") or "algebra_source"),
                        file_path=None,
                        status="published",
                        source_type="text",
                        ai_confidence=None,
                    )
                )
            for chunk in chunks:
                session.execute(
                    chunks_table.insert().values(
                        material_id=chunk["material_id"],
                        hash=chunk["hash"],
                        text=chunk["text"],
                        embedding_json=chunk["embedding_json"],
                        metadata_json=chunk["metadata_json"],
                    )
                )
        if topic_ids:
            imported_material_ids = list(
                session.execute(
                    select(materials_table.c.id).where(materials_table.c.topic_id.in_(topic_ids))
                ).scalars()
            )
            material_count = len(imported_material_ids)
            chunk_count = (
                session.scalar(
                    select(func.count()).select_from(chunks_table).where(chunks_table.c.material_id.in_(imported_material_ids))
                )
                or 0
            )
        else:
            material_count = 0
            chunk_count = 0
    engine.dispose()
    decision = "production_import_executed" if target_env == "production" else "staging_import_executed"
    return {
        **plan,
        "decision": decision,
        "rows_written": len(materials) + len(chunks),
        "material_count": int(material_count),
        "chunk_count": int(chunk_count),
        "blockers": [],
        "production_mutation": target_env == "production",
        "promotion_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run guarded Algebra source/RAG import plan")
    parser.add_argument("--manifest-json", required=True)
    parser.add_argument("--target-env", required=True, choices=["local", "staging", "production"])
    parser.add_argument("--db-url", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-production", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest_json).read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("--manifest-json must contain an object")
    result = execute_algebra_import_plan(
        manifest=manifest,
        target_env=args.target_env,
        db_url=args.db_url,
        dry_run=not args.execute,
        allow_production=args.allow_production,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["decision"] != "block_import" else 2


if __name__ == "__main__":
    raise SystemExit(main())
