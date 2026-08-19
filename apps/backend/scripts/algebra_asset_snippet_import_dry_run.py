"""Asset-snippet based Algebra import dry run.

Builds material/chunk-shaped rows from exact asset snippet metadata. It does not
write DB rows, create real RAG chunks, mutate production, or promote Algebra.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence, cast

from scripts.algebra_asset_extraction_snippets import build_snippet_manifest


def _chunk_hash(material_id: int, text: str) -> str:
    return hashlib.sha256(f"{material_id}:{text}".encode("utf-8")).hexdigest()[:16]


def build_asset_snippet_import_manifest(*, topic_ids: Sequence[int] | None = None) -> dict[str, object]:
    """Build material/chunk-shaped rows from exact asset snippets."""
    snippet_manifest = build_snippet_manifest(topic_ids=topic_ids)
    snippets = cast(list[dict[str, Any]], snippet_manifest["snippets"])
    materials: list[dict[str, object]] = []
    chunks: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []
    for idx, row in enumerate(snippets, start=1):
        topic_id = int(cast(Any, row["topic_id"]))
        material_id = 9000 + idx
        title = f"{row['source_key']} — {row['asset_label']}"
        metadata = {
            "subject_code": "algebra",
            "topic_id": topic_id,
            "topic_name": row["topic_focus"],
            "source_title": title,
            "material_title": title,
            "source_url": row["asset_url"],
            "source_section": row["source_section"],
            "license": row["license"],
            "attribution": row["attribution"],
            "extraction_mode": row["extraction_mode"],
        }
        text = str(row["snippet"])
        materials.append({
            "id": material_id,
            "topic_id": topic_id,
            "subject_code": "algebra",
            "title": title,
            "content": text,
            "source": row["source_key"],
            "source_url": row["asset_url"],
            "source_section": row["source_section"],
            "license": row["license"],
            "attribution": row["attribution"],
            "status": "draft_asset_snippet_local_only",
        })
        chunk = {
            "id": f"algebra-asset-snippet-{topic_id}-1",
            "material_id": material_id,
            "hash": _chunk_hash(material_id, text),
            "text": text,
            "embedding_json": "[]",
            "metadata_json": json.dumps(metadata, ensure_ascii=False),
        }
        chunks.append(chunk)
        audit_rows.append({
            "chunk_id": chunk["id"],
            "material_id": material_id,
            "material_title": title,
            "material_topic_id": topic_id,
            "material_subject_code": "algebra",
            "metadata_json": chunk["metadata_json"],
        })
    return {
        "mode": "asset_snippet_import_dry_run_only",
        "subject": "algebra",
        "topic_count": len(materials),
        "production_mutation": False,
        "db_write": False,
        "rag_write": False,
        "promotion_allowed": False,
        "readiness_decision": "keep_preview_asset_snippet_dry_run_only",
        "materials": materials,
        "chunks": chunks,
        "audit_rows": audit_rows,
    }


def write_manifest(path: Path, *, topic_ids: Sequence[int] | None = None) -> Path:
    manifest = build_asset_snippet_import_manifest(topic_ids=topic_ids)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Algebra asset-snippet import dry-run rows")
    parser.add_argument("--out", default="/tmp/ai-tutor-algebra-asset-snippet-import.json")
    parser.add_argument("--topic", action="append", type=int, default=[])
    args = parser.parse_args()
    out = write_manifest(Path(args.out), topic_ids=args.topic or None)
    manifest = json.loads(out.read_text(encoding="utf-8"))
    print(json.dumps({"ok": True, "out": str(out), "topic_count": manifest["topic_count"], "material_count": len(manifest["materials"]), "chunk_count": len(manifest["chunks"]), "readiness_decision": manifest["readiness_decision"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
