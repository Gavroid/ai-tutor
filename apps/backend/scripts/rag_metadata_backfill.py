"""Backfill citation-safe metadata for rag_chunks.

Safe/idempotent: only enriches metadata_json for chunks joined to learning_materials/topics.
Does not touch chunk text, embeddings, materials, or generated content.
"""
from __future__ import annotations

import argparse
import json
import re
from typing import Any

from app.db.session import SessionLocal
from app.rag_models import RagChunk
from app.subjects.models import LearningMaterial, Topic

P0_TOPIC_IDS = [187,188,189,192,193,194,195,196,197,198,199,201,203,204,225]


def infer_part(material_title: str | None, existing: Any = None) -> int | None:
    if existing not in (None, "", 0):
        try:
            return int(existing)
        except (TypeError, ValueError):
            pass
    if not material_title:
        return None
    match = re.search(r"часть\s*(\d+)", material_title, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def enrich_metadata(meta: dict[str, Any], *, topic: Topic, material: LearningMaterial) -> tuple[dict[str, Any], bool]:
    next_meta = dict(meta)
    changed = False
    updates = {
        "topic_id": int(topic.id),
        "topic_name": topic.name,
        "material_title": material.title,
        "part": infer_part(material.title, next_meta.get("part")),
    }
    for key, value in updates.items():
        if value is None:
            continue
        if next_meta.get(key) != value:
            next_meta[key] = value
            changed = True
    # Keep existing page_number only; do not invent pages.
    return next_meta, changed


def run(topic_ids: list[int], *, dry_run: bool = False) -> dict[str, Any]:
    with SessionLocal() as db:
        rows = (
            db.query(RagChunk, LearningMaterial, Topic)
            .join(LearningMaterial, RagChunk.material_id == LearningMaterial.id)
            .join(Topic, LearningMaterial.topic_id == Topic.id)
            .filter(Topic.id.in_(topic_ids))
            .all()
        )
        changed = 0
        scanned = 0
        by_topic: dict[int, int] = {}
        for chunk, material, topic in rows:
            scanned += 1
            try:
                meta = json.loads(chunk.metadata_json or "{}")
                if not isinstance(meta, dict):
                    meta = {}
            except Exception:
                meta = {}
            enriched, did_change = enrich_metadata(meta, topic=topic, material=material)
            if did_change:
                changed += 1
                by_topic[int(topic.id)] = by_topic.get(int(topic.id), 0) + 1
                if not dry_run:
                    chunk.metadata_json = json.dumps(enriched, ensure_ascii=False)
        if not dry_run:
            db.commit()
        return {"dry_run": dry_run, "scanned": scanned, "changed": changed, "by_topic": by_topic}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topics", default=",".join(map(str, P0_TOPIC_IDS)))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    topic_ids = [int(part.strip()) for part in args.topics.split(",") if part.strip()]
    print(json.dumps(run(topic_ids, dry_run=args.dry_run), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
