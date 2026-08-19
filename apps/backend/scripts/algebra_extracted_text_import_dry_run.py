"""Build Algebra import dry-run rows from verified extracted asset text.

Consumes output from algebra_exact_asset_fetch_probe and converts passed rows into
material/chunk-shaped local dry-run rows. No DB writes, RAG writes, production
mutation, or promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, cast

from scripts.algebra_source_asset_manifest import build_asset_manifest


def _chunk_hash(material_id: int, text: str) -> str:
    return hashlib.sha256(f"{material_id}:{text}".encode("utf-8")).hexdigest()[:16]


def _asset_by_topic() -> dict[int, dict[str, Any]]:
    assets = cast(list[dict[str, Any]], build_asset_manifest()["assets"])
    return {int(cast(Any, asset["topic_id"])): asset for asset in assets}


def build_extracted_text_import_manifest(*, probe_manifest: dict[str, object]) -> dict[str, object]:
    """Build local import dry-run rows from passed exact-asset extraction rows."""
    rows = cast(list[dict[str, Any]], probe_manifest.get("rows") or [])
    assets = _asset_by_topic()
    materials: list[dict[str, object]] = []
    chunks: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []
    for row in rows:
        if row.get("status") != "pass":
            continue
        topic_id = int(cast(Any, row["topic_id"]))
        asset = assets[topic_id]
        material_id = 10000 + len(materials) + 1
        text = str(row.get("text_excerpt") or row.get("snippet") or "").strip()
        if not text:
            continue
        title = f"{asset['source_key']} — extracted {asset['asset_label']}"
        metadata = {
            "subject_code": "algebra",
            "topic_id": topic_id,
            "topic_name": asset["topic_focus"],
            "source_title": title,
            "material_title": title,
            "source_url": asset["asset_url"],
            "source_section": asset["source_section"],
            "license": asset["license"],
            "attribution": asset["attribution"],
            "extraction_mode": row.get("extraction_source") or "exact_asset_fetch_probe",
        }
        material = {
            "id": material_id,
            "topic_id": topic_id,
            "subject_code": "algebra",
            "title": title,
            "content": text,
            "source": asset["source_key"],
            "source_url": asset["asset_url"],
            "source_section": asset["source_section"],
            "license": asset["license"],
            "attribution": asset["attribution"],
            "status": "draft_extracted_text_local_only",
        }
        chunk = {
            "id": f"algebra-extracted-{topic_id}-1",
            "material_id": material_id,
            "hash": _chunk_hash(material_id, text),
            "text": text,
            "embedding_json": "[]",
            "metadata_json": json.dumps(metadata, ensure_ascii=False),
        }
        materials.append(material)
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
        "mode": "extracted_text_import_dry_run_only",
        "subject": "algebra",
        "topic_count": len(materials),
        "production_mutation": False,
        "db_write": False,
        "rag_write": False,
        "promotion_allowed": False,
        "readiness_decision": "keep_preview_extracted_text_dry_run_only",
        "materials": materials,
        "chunks": chunks,
        "audit_rows": audit_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Algebra extracted-text import dry-run rows")
    parser.add_argument("--probe-json", required=True)
    parser.add_argument("--out", default="/tmp/ai-tutor-algebra-extracted-text-import.json")
    args = parser.parse_args()
    probe = json.loads(Path(args.probe_json).read_text(encoding="utf-8"))
    if not isinstance(probe, dict):
        raise ValueError("--probe-json must contain an object")
    manifest = build_extracted_text_import_manifest(probe_manifest=probe)
    out = Path(args.out)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    materials = cast(list[dict[str, object]], manifest["materials"])
    chunks = cast(list[dict[str, object]], manifest["chunks"])
    print(json.dumps({"ok": True, "out": str(out), "topic_count": manifest["topic_count"], "material_count": len(materials), "chunk_count": len(chunks), "readiness_decision": manifest["readiness_decision"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
