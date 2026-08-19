"""Exact source asset manifest for Algebra local import planning.

This manifest narrows Stage 13 broad source mappings into concrete source assets
(unit pages or section PDFs). It is metadata only: no downloads, DB writes, RAG
chunks, production mutation, or readiness promotion.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence, cast

from scripts.algebra_source_import_dry_run import build_algebra_source_mappings

_APPROVED_PREFIXES = (
    "https://im.kendallhunt.com/HS/students/1/",
    "http://www.wallace.ccfaculty.org/book/",
)

_ASSET_BY_TOPIC: dict[int, tuple[str, str]] = {
    34: ("http://www.wallace.ccfaculty.org/book/0.3%20Order%20of%20Operations.pdf", "0.3 Order of Operations PDF"),
    35: ("http://www.wallace.ccfaculty.org/book/0.4%20Properties%20of%20Algebra.pdf", "0.4 Properties of Algebra PDF"),
    36: ("http://www.wallace.ccfaculty.org/book/1.3%20General%20Linear%20Equations.pdf", "1.3 General Linear Equations PDF"),
    37: ("https://im.kendallhunt.com/HS/students/1/2/index.html", "IM Algebra 1 Unit 2 page"),
    38: ("https://im.kendallhunt.com/HS/students/1/4/index.html", "IM Algebra 1 Unit 4 page"),
    39: ("https://im.kendallhunt.com/HS/students/1/4/index.html", "IM Algebra 1 Unit 4 page"),
    40: ("http://www.wallace.ccfaculty.org/book/1.7%20Variation.pdf", "1.7 Variation PDF"),
    41: ("http://www.wallace.ccfaculty.org/book/5.1%20Exponents.pdf", "5.1 Exponent Properties PDF"),
    42: ("http://www.wallace.ccfaculty.org/book/5.1%20Exponents.pdf", "5.1 Exponent Properties PDF"),
    43: ("http://www.wallace.ccfaculty.org/book/5.4%20Add%20Polynomials.pdf", "5.4 Introduction/Add Polynomials PDF"),
    44: ("http://www.wallace.ccfaculty.org/book/5.4%20Add%20Polynomials.pdf", "5.4 Introduction/Add Polynomials PDF"),
    45: ("http://www.wallace.ccfaculty.org/book/5.4%20Add%20Polynomials.pdf", "5.4 Add Polynomials PDF"),
    46: ("http://www.wallace.ccfaculty.org/book/5.5%20Multiply%20Polynomials.pdf", "5.5 Multiply Polynomials PDF"),
    47: ("http://www.wallace.ccfaculty.org/book/5.5%20Multiply%20Polynomials.pdf", "5.5 Multiply Polynomials PDF"),
    48: ("http://www.wallace.ccfaculty.org/book/5.6%20Multiply%20Special%20Products.pdf", "5.6 Multiply Special Products PDF"),
    49: ("https://im.kendallhunt.com/HS/students/1/2/index.html", "IM Algebra 1 Unit 2 page"),
    50: ("https://im.kendallhunt.com/HS/students/1/2/index.html", "IM Algebra 1 Unit 2 page"),
    51: ("https://im.kendallhunt.com/HS/students/1/2/index.html", "IM Algebra 1 Unit 2 page"),
    52: ("https://im.kendallhunt.com/HS/students/1/2/index.html", "IM Algebra 1 Unit 2 page"),
}


def build_asset_manifest(*, topic_ids: Sequence[int] | None = None) -> dict[str, object]:
    """Build exact source asset metadata for Algebra route topics."""
    selected = set(topic_ids) if topic_ids is not None else None
    assets: list[dict[str, object]] = []
    for mapping in build_algebra_source_mappings():
        if selected is not None and mapping.topic_id not in selected:
            continue
        asset_url, asset_label = _ASSET_BY_TOPIC[mapping.topic_id]
        assets.append({
            "topic_id": mapping.topic_id,
            "topic_order": mapping.topic_order,
            "topic_focus": mapping.topic_focus,
            "source_key": mapping.source_key,
            "source_title": mapping.source_title,
            "source_section": mapping.source_section,
            "asset_url": asset_url,
            "asset_label": asset_label,
            "license": mapping.license,
            "attribution": mapping.attribution,
            "decision": mapping.decision,
            "production_mutation": False,
            "db_import": False,
            "rag_chunk_creation": False,
        })
    return {
        "mode": "exact_source_asset_manifest_only",
        "subject": "algebra",
        "topic_count": len(assets),
        "production_mutation": False,
        "db_import": False,
        "rag_chunk_creation": False,
        "assets": assets,
    }


def validate_asset_manifest(manifest: dict[str, object]) -> dict[str, object]:
    """Validate asset manifest is complete, unique, and source-policy constrained."""
    problems: list[str] = []
    assets = cast(list[dict[str, Any]], manifest.get("assets") or [])
    topic_ids = [asset.get("topic_id") for asset in assets]
    if len(topic_ids) != len(set(topic_ids)):
        problems.append("duplicate_topic_id")
    if manifest.get("topic_count") != len(assets):
        problems.append("topic_count_mismatch")
    for asset in assets:
        url = str(asset.get("asset_url") or "")
        if not url.startswith(_APPROVED_PREFIXES):
            problems.append("unapproved_asset_url")
            break
        if not asset.get("license") or "ND" in str(asset.get("license")):
            problems.append("invalid_license")
            break
        if asset.get("production_mutation") is not False:
            problems.append("production_mutation_not_false")
            break
    return {"ok": not problems, "asset_count": len(assets), "problems": problems}


def write_manifest(path: Path, *, topic_ids: Sequence[int] | None = None) -> Path:
    manifest = build_asset_manifest(topic_ids=topic_ids)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build exact Algebra source asset manifest")
    parser.add_argument("--out", default="/tmp/ai-tutor-algebra-source-assets.json")
    parser.add_argument("--topic", action="append", type=int, default=[])
    args = parser.parse_args()
    out = write_manifest(Path(args.out), topic_ids=args.topic or None)
    manifest = json.loads(out.read_text(encoding="utf-8"))
    validation = validate_asset_manifest(manifest)
    print(json.dumps({"ok": validation["ok"], "out": str(out), "topic_count": manifest["topic_count"], "asset_count": validation["asset_count"], "problems": validation["problems"]}, ensure_ascii=False))
    return 0 if validation["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
