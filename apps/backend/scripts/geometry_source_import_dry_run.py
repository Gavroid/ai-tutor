"""Stage 14 Geometry source import dry-run manifest.

No downloads, DB writes, RAG chunk creation, or production mutation. This only
validates topic-to-source mapping metadata for a later local import.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from app.geometry_plan import GEOMETRY_TOPIC_PLAN

Decision = Literal["approved_for_dry_run", "conditional_secondary"]

IM_GEOMETRY_URL = "https://im.kendallhunt.com/HS/students/2/index.html"
OTL_GEOMETRY_URL = "https://open.umn.edu/opentextbooks/subjects/geometry-and-trigonometry"

ATTRIBUTIONS = {
    "im_geometry": "Based on IM® Geometry authored by Illustrative Mathematics®. Used under a CC BY 4.0 license.",
    "euclid_redux": "Euclid's Elements Redux is listed by Open Textbook Library under a CC BY-SA license; verify final attribution on the book page before import.",
}


@dataclass(frozen=True)
class GeometrySourceMapping:
    topic_id: int
    topic_order: int
    topic_focus: str
    source_key: str
    source_title: str
    source_url: str
    source_section: str
    license: str
    attribution: str
    decision: Decision
    diagram_review_required: bool
    import_notes: str


_SOURCE_BY_TOPIC: dict[int, tuple[str, str, str, str, str, Decision, bool, str]] = {
    53: ("im_geometry", "Illustrative Mathematics Geometry", IM_GEOMETRY_URL, "Unit 1 Constructions and Rigid Transformations", "CC BY 4.0", "approved_for_dry_run", True, "Use for line/segment/ray/angle foundations; validate diagrams."),
    54: ("im_geometry", "Illustrative Mathematics Geometry", IM_GEOMETRY_URL, "Unit 1 Constructions and Rigid Transformations", "CC BY 4.0", "approved_for_dry_run", True, "Use for measurement context; confirm exact lesson anchors."),
    55: ("euclid_redux", "Euclid's Elements Redux", OTL_GEOMETRY_URL, "Euclid foundations / angle relationships", "CC BY-SA", "conditional_secondary", True, "Use only if IM lacks concise adjacent/vertical angle text; page-level review required."),
    56: ("im_geometry", "Illustrative Mathematics Geometry", IM_GEOMETRY_URL, "Unit 1 Constructions and Rigid Transformations", "CC BY 4.0", "approved_for_dry_run", True, "Use for perpendicular lines and construction context."),
    57: ("im_geometry", "Illustrative Mathematics Geometry", IM_GEOMETRY_URL, "Unit 2 Congruence", "CC BY 4.0", "approved_for_dry_run", True, "Primary mapping for triangle congruence."),
    58: ("euclid_redux", "Euclid's Elements Redux", OTL_GEOMETRY_URL, "Triangle elements / classical definitions", "CC BY-SA", "conditional_secondary", True, "Use only for definitions of median/bisector/altitude if IM extraction is insufficient."),
    59: ("im_geometry", "Illustrative Mathematics Geometry", IM_GEOMETRY_URL, "Unit 2 Congruence", "CC BY 4.0", "approved_for_dry_run", True, "Use for isosceles triangle reasoning through congruence."),
    60: ("im_geometry", "Illustrative Mathematics Geometry", IM_GEOMETRY_URL, "Unit 7 Circles", "CC BY 4.0", "approved_for_dry_run", True, "Use for circles; construction tasks need diagram validation."),
    61: ("im_geometry", "Illustrative Mathematics Geometry", IM_GEOMETRY_URL, "Unit 1 Constructions and Rigid Transformations", "CC BY 4.0", "approved_for_dry_run", True, "Map to parallel-line reasoning only after lesson-level check."),
    62: ("im_geometry", "Illustrative Mathematics Geometry", IM_GEOMETRY_URL, "Unit 1 Constructions and Rigid Transformations", "CC BY 4.0", "approved_for_dry_run", True, "Use for properties of parallel lines if lesson anchors support it."),
    63: ("im_geometry", "Illustrative Mathematics Geometry", IM_GEOMETRY_URL, "Unit 2 Congruence", "CC BY 4.0", "approved_for_dry_run", True, "Use for triangle angle sum through congruence/proof lessons."),
    64: ("euclid_redux", "Euclid's Elements Redux", OTL_GEOMETRY_URL, "Triangle angle relationships", "CC BY-SA", "conditional_secondary", True, "Use only if page-level text clearly supports exterior angle theorem."),
    65: ("euclid_redux", "Euclid's Elements Redux", OTL_GEOMETRY_URL, "Triangle inequality / classical propositions", "CC BY-SA", "conditional_secondary", True, "Use only after proving grade-level readability and attribution/share-alike handling."),
}


def build_geometry_source_mappings() -> list[GeometrySourceMapping]:
    rows: list[GeometrySourceMapping] = []
    for topic in GEOMETRY_TOPIC_PLAN:
        source_key, title, url, section, license_name, decision, diagram_review, notes = _SOURCE_BY_TOPIC[topic.topic_id]
        rows.append(
            GeometrySourceMapping(
                topic_id=topic.topic_id,
                topic_order=topic.order,
                topic_focus=topic.focus,
                source_key=source_key,
                source_title=title,
                source_url=url,
                source_section=section,
                license=license_name,
                attribution=ATTRIBUTIONS[source_key],
                decision=decision,
                diagram_review_required=diagram_review,
                import_notes=notes,
            )
        )
    return rows


def build_manifest() -> dict[str, object]:
    rows = build_geometry_source_mappings()
    source_counts: dict[str, int] = {}
    for row in rows:
        source_counts[row.source_key] = source_counts.get(row.source_key, 0) + 1
    return {
        "stage": "14",
        "subject": "Geometry",
        "mode": "local_dry_run_manifest_only",
        "production_mutation": False,
        "db_import": False,
        "rag_chunk_creation": False,
        "requires_diagram_review": True,
        "topic_count": len(rows),
        "source_counts": source_counts,
        "mappings": [asdict(row) for row in rows],
    }


def write_manifest(path: Path) -> Path:
    manifest = build_manifest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build Stage 14 Geometry source dry-run manifest")
    parser.add_argument("--out", default="/tmp/ai-tutor-geometry-source-dry-run.json")
    args = parser.parse_args()
    out = write_manifest(Path(args.out))
    manifest = json.loads(out.read_text(encoding="utf-8"))
    print(json.dumps({"ok": True, "out": str(out), "topic_count": manifest["topic_count"], "source_counts": manifest["source_counts"], "requires_diagram_review": manifest["requires_diagram_review"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
