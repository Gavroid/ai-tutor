"""Local-only Algebra import dry-run manifest.

Creates disposable material/chunk-shaped JSON records for a small Algebra subset.
This is not a DB importer: it writes no database rows, creates no real RAG
chunks, and performs no production mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence, cast

from scripts.algebra_rag_subset_fixture import build_subset_fixture


def _chunk_hash(material_id: int, text: str) -> str:
    return hashlib.sha256(f"{material_id}:{text}".encode("utf-8")).hexdigest()[:16]


def _metadata(row: dict[str, object]) -> dict[str, object]:
    return json.loads(str(row["metadata_json"]))


def build_local_import_manifest(*, topic_ids: Sequence[int] | None = None) -> dict[str, object]:
    """Build local material/chunk-shaped rows for audit-only import rehearsal."""
    fixture_rows = build_subset_fixture(topic_ids=topic_ids)
    materials: list[dict[str, object]] = []
    chunks: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []

    for row in fixture_rows:
        metadata = _metadata(row)
        material_id = int(cast(Any, row["material_id"]))
        topic_id = int(cast(Any, row["material_topic_id"]))
        material = {
            "id": material_id,
            "topic_id": topic_id,
            "subject_code": "algebra",
            "title": row["material_title"],
            "source": metadata["source_title"],
            "source_url": metadata["source_url"],
            "source_section": metadata["source_section"],
            "license": metadata["license"],
            "attribution": metadata["attribution"],
            "status": "draft_local_only",
        }
        text = str(row.get("text") or "")
        chunk = {
            "id": row["chunk_id"],
            "material_id": material_id,
            "hash": _chunk_hash(material_id, text),
            "text": text,
            "embedding_json": "[]",
            "metadata_json": row["metadata_json"],
        }
        materials.append(material)
        chunks.append(chunk)
        audit_rows.append({
            "chunk_id": chunk["id"],
            "material_id": material_id,
            "material_title": material["title"],
            "material_topic_id": topic_id,
            "material_subject_code": "algebra",
            "metadata_json": row["metadata_json"],
        })

    return {
        "mode": "local_import_dry_run_only",
        "subject": "algebra",
        "topic_count": len(materials),
        "production_mutation": False,
        "db_write": False,
        "rag_write": False,
        "promotion_allowed": False,
        "readiness_decision": "keep_preview_local_dry_run_only",
        "materials": materials,
        "chunks": chunks,
        "audit_rows": audit_rows,
    }


def write_manifest(path: Path, *, topic_ids: Sequence[int] | None = None) -> Path:
    manifest = build_local_import_manifest(topic_ids=topic_ids)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local-only Algebra import dry-run manifest")
    parser.add_argument("--out", default="/tmp/ai-tutor-algebra-local-import-dry-run.json")
    parser.add_argument("--topic", action="append", type=int, default=[])
    args = parser.parse_args()
    out = write_manifest(Path(args.out), topic_ids=args.topic or None)
    manifest = json.loads(out.read_text(encoding="utf-8"))
    print(json.dumps({
        "ok": True,
        "out": str(out),
        "topic_count": manifest["topic_count"],
        "material_count": len(manifest["materials"]),
        "chunk_count": len(manifest["chunks"]),
        "readiness_decision": manifest["readiness_decision"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
