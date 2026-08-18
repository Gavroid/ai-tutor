"""Local Algebra RAG subset fixture builder.

Builds JSON rows compatible with scripts.rag_metadata_audit without importing
source files, writing DB rows, creating RAG chunks, or mutating production.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from scripts.algebra_source_import_dry_run import build_algebra_source_mappings

_DEFAULT_SUBSET_TOPIC_IDS = [34, 37, 41]


def _topic_name(focus: str) -> str:
    return focus.strip() or "algebra topic"


def build_subset_fixture(*, topic_ids: Sequence[int] | None = None) -> list[dict[str, object]]:
    """Build metadata-audit rows for a small Algebra local subset."""
    selected = list(topic_ids) if topic_ids is not None else list(_DEFAULT_SUBSET_TOPIC_IDS)
    mappings = {row.topic_id: row for row in build_algebra_source_mappings()}
    rows: list[dict[str, object]] = []
    for idx, topic_id in enumerate(selected, start=1):
        mapping = mappings[topic_id]
        topic_name = _topic_name(mapping.topic_focus)
        metadata = {
            "subject_code": "algebra",
            "topic_id": mapping.topic_id,
            "topic_name": topic_name,
            "source_title": mapping.source_title,
            "source_url": mapping.source_url,
            "source_section": mapping.source_section,
            "license": mapping.license,
            "attribution": mapping.attribution,
            "source_key": mapping.source_key,
            "import_decision": mapping.decision,
        }
        rows.append({
            "chunk_id": f"algebra-subset-{topic_id}-1",
            "material_id": 7000 + idx,
            "material_title": f"{mapping.source_title} — {mapping.source_section}",
            "material_topic_id": mapping.topic_id,
            "material_subject_code": "algebra",
            "metadata_json": json.dumps(metadata, ensure_ascii=False),
            "text": (
                f"Local fixture for Algebra topic {topic_id}: {topic_name}. "
                f"Source section: {mapping.source_section}. This text is for metadata audit only."
            ),
            "production_mutation": False,
            "db_import": False,
            "rag_chunk_creation": False,
        })
    return rows


def build_subset_manifest(*, topic_ids: Sequence[int] | None = None) -> dict[str, object]:
    rows = build_subset_fixture(topic_ids=topic_ids)
    source_counts: dict[str, int] = {}
    for row in rows:
        metadata = json.loads(str(row["metadata_json"]))
        source_key = str(metadata["source_key"])
        source_counts[source_key] = source_counts.get(source_key, 0) + 1
    return {
        "mode": "local_subset_fixture_only",
        "subject": "algebra",
        "topic_count": len(rows),
        "source_counts": source_counts,
        "production_mutation": False,
        "db_import": False,
        "rag_chunk_creation": False,
        "readiness_decision": "keep_preview_until_real_import_and_audit",
        "rows": rows,
    }


def write_manifest(path: Path, *, topic_ids: Sequence[int] | None = None) -> Path:
    manifest = build_subset_manifest(topic_ids=topic_ids)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local Algebra RAG subset fixture manifest")
    parser.add_argument("--out", default="/tmp/ai-tutor-algebra-rag-subset-fixture.json")
    parser.add_argument("--topic", action="append", type=int, default=[])
    args = parser.parse_args()
    out = write_manifest(Path(args.out), topic_ids=args.topic or None)
    manifest = json.loads(out.read_text(encoding="utf-8"))
    print(json.dumps({
        "ok": True,
        "out": str(out),
        "topic_count": manifest["topic_count"],
        "source_counts": manifest["source_counts"],
        "readiness_decision": manifest["readiness_decision"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
