"""Local Algebra source extraction probe.

This script validates fetched source-page text against the Stage 13 Algebra
source dry-run manifest. It does not download into the repo, write DB rows,
create RAG chunks, or mutate production.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

from scripts.algebra_source_import_dry_run import build_algebra_source_mappings

_REQUIRED_TERMS_BY_SOURCE: dict[str, tuple[str, ...]] = {
    "im_first_edition": (
        "Unit 2",
        "Linear Equations",
        "Systems",
        "Unit 4",
        "Functions",
    ),
    "wallace_algebra": (
        "Order of Operations",
        "Properties of Algebra",
        "General Linear Equations",
        "Exponent Properties",
        "Introduction to Polynomials",
    ),
}

_REQUIRED_TERMS_BY_TOPIC: dict[int, tuple[str, ...]] = {
    34: ("Order of Operations",),
    35: ("Properties of Algebra",),
    36: ("General Linear Equations",),
    37: ("Unit 2", "Linear Equations"),
    38: ("Unit 4", "Functions"),
    39: ("Unit 4", "Functions"),
    40: ("Variation", "Slope-Intercept"),
    41: ("Exponent Properties",),
    42: ("Exponent",),
    43: ("Polynomials",),
    44: ("Polynomials",),
    45: ("Add Polynomials",),
    46: ("Multiply Polynomials",),
    47: ("Multiply Polynomials",),
    48: ("Special Products",),
    49: ("Unit 2", "Linear Equations"),
    50: ("Unit 2", "Systems"),
    51: ("Unit 2", "Systems"),
    52: ("Unit 2", "Systems"),
}


def _contains_term(text: str, term: str) -> bool:
    return term.casefold() in text.casefold()


def evaluate_probe_text(
    *,
    source_key: str,
    source_section: str,
    text: str,
    required_terms: Sequence[str],
) -> dict[str, object]:
    """Evaluate whether fetched source text supports a mapping probe."""
    matched = [term for term in required_terms if _contains_term(text, term)]
    missing = [term for term in required_terms if term not in matched]
    section_terms = [part.strip() for part in source_section.replace("/", " ").split() if len(part.strip()) > 2]
    section_hits = [term for term in section_terms if _contains_term(text, term)]
    status = "pass" if not missing else "fail"
    return {
        "source_key": source_key,
        "source_section": source_section,
        "status": status,
        "matched_terms": matched,
        "missing_terms": missing,
        "section_hit_count": len(section_hits),
        "text_chars": len(text),
    }


def build_probe_rows(
    *,
    fetched_text_by_source: Mapping[str, str],
    topic_ids: Sequence[int] | None = None,
) -> list[dict[str, object]]:
    """Build per-topic extraction probe rows from manifest mappings and fetched text."""
    selected = set(topic_ids) if topic_ids is not None else None
    rows: list[dict[str, object]] = []
    for mapping in build_algebra_source_mappings():
        if selected is not None and mapping.topic_id not in selected:
            continue
        required_terms = _REQUIRED_TERMS_BY_TOPIC.get(
            mapping.topic_id,
            _REQUIRED_TERMS_BY_SOURCE.get(mapping.source_key, (mapping.source_section,)),
        )
        text = fetched_text_by_source.get(mapping.source_key, "")
        probe = evaluate_probe_text(
            source_key=mapping.source_key,
            source_section=mapping.source_section,
            text=text,
            required_terms=required_terms,
        )
        rows.append({
            "topic_id": mapping.topic_id,
            "topic_focus": mapping.topic_focus,
            "source_key": mapping.source_key,
            "source_title": mapping.source_title,
            "source_url": mapping.source_url,
            "source_section": mapping.source_section,
            "license": mapping.license,
            "decision": mapping.decision,
            "status": probe["status"],
            "matched_terms": probe["matched_terms"],
            "missing_terms": probe["missing_terms"],
            "section_hit_count": probe["section_hit_count"],
            "text_chars": probe["text_chars"],
            "production_mutation": False,
            "db_import": False,
            "rag_chunk_creation": False,
        })
    return rows


def summarize_probe_rows(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Summarize probe pass/fail and source counts."""
    source_counts = Counter(str(row.get("source_key")) for row in rows)
    pass_count = sum(1 for row in rows if row.get("status") == "pass")
    fail_count = sum(1 for row in rows if row.get("status") == "fail")
    return {
        "topic_count": len(rows),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "source_counts": dict(sorted(source_counts.items())),
    }


def build_probe_manifest(
    *,
    fetched_text_by_source: Mapping[str, str],
    topic_ids: Sequence[int] | None = None,
) -> dict[str, object]:
    rows = build_probe_rows(fetched_text_by_source=fetched_text_by_source, topic_ids=topic_ids)
    return {
        "mode": "local_extraction_probe_only",
        "production_mutation": False,
        "db_import": False,
        "rag_chunk_creation": False,
        "summary": summarize_probe_rows(rows),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Algebra source extraction text locally")
    parser.add_argument("--source-text-json", required=True, help="JSON object mapping source_key to extracted text")
    parser.add_argument("--out", default="/tmp/ai-tutor-algebra-extraction-probe.json")
    parser.add_argument("--topic", action="append", type=int, default=[])
    args = parser.parse_args()

    payload = json.loads(Path(args.source_text_json).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--source-text-json must contain a JSON object")
    fetched = {str(key): str(value) for key, value in payload.items()}
    manifest = build_probe_manifest(
        fetched_text_by_source=fetched,
        topic_ids=args.topic or None,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = summarize_probe_rows(rows=manifest["rows"] if isinstance(manifest["rows"], list) else [])
    print(json.dumps({"ok": True, "out": str(out), **summary}, ensure_ascii=False))
    return 0 if summary["fail_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
