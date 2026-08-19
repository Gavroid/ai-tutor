"""Local extraction snippet manifest for exact Algebra source assets.

This module creates short, auditable snippet placeholders tied to exact approved
assets. It is metadata-only and does not download, import, or mutate production.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence, cast

from scripts.algebra_source_asset_manifest import build_asset_manifest

_SNIPPET_HINT_BY_TOPIC: dict[int, str] = {
    34: "Order of operations: evaluate grouped arithmetic expressions using operation priority.",
    35: "Properties of algebra: variables and formulas represent changing quantities.",
    36: "General linear equations: transform equivalent expressions to solve for a variable.",
    37: "Linear equations in one variable: solve equations by preserving equality.",
    38: "Functions: a function assigns each input exactly one output.",
    39: "Linear functions: slope and intercept describe a line and its graph.",
    40: "Variation and proportionality: direct variation connects two quantities by a constant ratio.",
    41: "Exponent properties: repeated multiplication defines powers with natural exponents.",
    42: "Exponent properties: products and powers can be simplified with exponent rules.",
    43: "Polynomials: monomials and polynomial terms have coefficients, variables, and degrees.",
    44: "Polynomials: a polynomial is a sum of terms that can be classified by degree and terms.",
    45: "Add polynomials: combine like terms when adding or subtracting polynomials.",
    46: "Multiply polynomials: distribute a monomial across each polynomial term.",
    47: "Multiply polynomials: use distribution for each term of the first polynomial.",
    48: "Special products: square and conjugate patterns make multiplication faster.",
    49: "Two-variable linear equations: solutions are ordered pairs that satisfy the equation.",
    50: "Systems of equations: graphing finds an intersection that satisfies both equations.",
    51: "Systems of equations: substitution replaces one variable expression in another equation.",
    52: "Systems of equations: elimination combines equations to remove one variable.",
}


def build_snippet_manifest(*, topic_ids: Sequence[int] | None = None) -> dict[str, object]:
    """Build local snippet metadata for exact Algebra assets."""
    asset_manifest = build_asset_manifest(topic_ids=topic_ids)
    assets = cast(list[dict[str, Any]], asset_manifest["assets"])
    snippets: list[dict[str, object]] = []
    for asset in assets:
        topic_id = int(cast(Any, asset["topic_id"]))
        snippets.append({
            "topic_id": topic_id,
            "topic_focus": asset["topic_focus"],
            "source_key": asset["source_key"],
            "asset_url": asset["asset_url"],
            "asset_label": asset["asset_label"],
            "source_section": asset["source_section"],
            "license": asset["license"],
            "attribution": asset["attribution"],
            "snippet": _SNIPPET_HINT_BY_TOPIC[topic_id],
            "extraction_mode": "local_curated_snippet_from_exact_asset",
            "production_mutation": False,
            "db_import": False,
            "rag_chunk_creation": False,
        })
    return {
        "mode": "local_asset_snippet_manifest_only",
        "subject": "algebra",
        "topic_count": len(snippets),
        "production_mutation": False,
        "db_import": False,
        "rag_chunk_creation": False,
        "snippets": snippets,
    }


def validate_snippet_manifest(manifest: dict[str, object]) -> dict[str, object]:
    snippets = cast(list[dict[str, Any]], manifest.get("snippets") or [])
    problems: list[str] = []
    topic_ids = [row.get("topic_id") for row in snippets]
    if len(topic_ids) != len(set(topic_ids)):
        problems.append("duplicate_topic_id")
    if manifest.get("topic_count") != len(snippets):
        problems.append("topic_count_mismatch")
    for row in snippets:
        if not str(row.get("snippet") or "").strip():
            problems.append("empty_snippet")
            break
        if not row.get("asset_url") or not row.get("source_section"):
            problems.append("missing_asset_reference")
            break
        if row.get("production_mutation") is not False:
            problems.append("production_mutation_not_false")
            break
    return {"ok": not problems, "snippet_count": len(snippets), "problems": problems}


def write_manifest(path: Path, *, topic_ids: Sequence[int] | None = None) -> Path:
    manifest = build_snippet_manifest(topic_ids=topic_ids)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local Algebra exact-asset snippet manifest")
    parser.add_argument("--out", default="/tmp/ai-tutor-algebra-asset-snippets.json")
    parser.add_argument("--topic", action="append", type=int, default=[])
    args = parser.parse_args()
    out = write_manifest(Path(args.out), topic_ids=args.topic or None)
    manifest = json.loads(out.read_text(encoding="utf-8"))
    validation = validate_snippet_manifest(manifest)
    print(json.dumps({"ok": validation["ok"], "out": str(out), "topic_count": manifest["topic_count"], "snippet_count": validation["snippet_count"], "problems": validation["problems"]}, ensure_ascii=False))
    return 0 if validation["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
