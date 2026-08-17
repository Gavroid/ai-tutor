"""Stage 13 Algebra source import dry-run manifest.

This script does not download source files, write DB rows, create RAG chunks, or
mutate production. It validates a topic-to-source mapping for later local import.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from app.algebra_plan import ALGEBRA_TOPIC_PLAN

Decision = Literal["approved_for_dry_run", "secondary_support"]

IM_BASE = "https://im.kendallhunt.com/HS/students/1/index.html"
WALLACE_BASE = "http://www.wallace.ccfaculty.org/book/book.html"

ATTRIBUTIONS = {
    "im_first_edition": "Based on IM® K–12 Math authored by Illustrative Mathematics®. Used under a CC BY 4.0 license.",
    "wallace_algebra": "Beginning and Intermediate Algebra by Tyler Wallace is licensed under CC BY 3.0 Unported.",
}


@dataclass(frozen=True)
class AlgebraSourceMapping:
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
    import_notes: str


_SOURCE_BY_TOPIC: dict[int, tuple[str, str, str, str, str, Decision, str]] = {
    34: ("wallace_algebra", "Beginning and Intermediate Algebra", WALLACE_BASE, "0.3 Order of Operations", "CC BY 3.0", "secondary_support", "Use for numeric expression conventions and examples."),
    35: ("wallace_algebra", "Beginning and Intermediate Algebra", WALLACE_BASE, "0.4 Properties of Algebra / 1.5 Formulas", "CC BY 3.0", "secondary_support", "Use for variables, expressions, and formula manipulation."),
    36: ("wallace_algebra", "Beginning and Intermediate Algebra", WALLACE_BASE, "1.3 General Linear Equations", "CC BY 3.0", "secondary_support", "Use for algebraic transformations while checking grade fit."),
    37: ("im_first_edition", "Illustrative Mathematics Algebra 1", IM_BASE, "Unit 2 Linear Equations, Inequalities, and Systems", "CC BY 4.0", "approved_for_dry_run", "Primary IM mapping for one-variable linear equations."),
    38: ("im_first_edition", "Illustrative Mathematics Algebra 1", IM_BASE, "Unit 4 Functions", "CC BY 4.0", "approved_for_dry_run", "Primary IM mapping for function concept."),
    39: ("im_first_edition", "Illustrative Mathematics Algebra 1", IM_BASE, "Unit 4 Functions", "CC BY 4.0", "approved_for_dry_run", "Primary IM mapping for linear function concepts; validate y=kx+b section before import."),
    40: ("wallace_algebra", "Beginning and Intermediate Algebra", WALLACE_BASE, "1.7 Variation / 2.3 Slope-Intercept Form", "CC BY 3.0", "secondary_support", "Use for direct proportionality if IM Unit 4 mapping is too broad."),
    41: ("wallace_algebra", "Beginning and Intermediate Algebra", WALLACE_BASE, "5.1 Exponent Properties", "CC BY 3.0", "secondary_support", "IM Algebra 1 index does not expose powers directly; use Wallace section after level review."),
    42: ("wallace_algebra", "Beginning and Intermediate Algebra", WALLACE_BASE, "5.1 Exponent Properties / 5.2 Negative Exponents", "CC BY 3.0", "secondary_support", "Use for exponent rules; exclude negative exponents if outside route scope."),
    43: ("wallace_algebra", "Beginning and Intermediate Algebra", WALLACE_BASE, "5.4 Introduction to Polynomials", "CC BY 3.0", "secondary_support", "Use for monomial/polynomial vocabulary."),
    44: ("wallace_algebra", "Beginning and Intermediate Algebra", WALLACE_BASE, "5.4 Introduction to Polynomials", "CC BY 3.0", "secondary_support", "Use for polynomial concept."),
    45: ("wallace_algebra", "Beginning and Intermediate Algebra", WALLACE_BASE, "5.4 Add Polynomials", "CC BY 3.0", "secondary_support", "Use for addition/subtraction of polynomials."),
    46: ("wallace_algebra", "Beginning and Intermediate Algebra", WALLACE_BASE, "5.5 Multiply Polynomials", "CC BY 3.0", "secondary_support", "Use only examples matching monomial times polynomial."),
    47: ("wallace_algebra", "Beginning and Intermediate Algebra", WALLACE_BASE, "5.5 Multiply Polynomials", "CC BY 3.0", "secondary_support", "Use for polynomial multiplication; validate complexity."),
    48: ("wallace_algebra", "Beginning and Intermediate Algebra", WALLACE_BASE, "5.6 Multiply Special Products", "CC BY 3.0", "secondary_support", "Use for special products; check notation readability."),
    49: ("im_first_edition", "Illustrative Mathematics Algebra 1", IM_BASE, "Unit 2 Linear Equations, Inequalities, and Systems", "CC BY 4.0", "approved_for_dry_run", "Primary IM mapping for two-variable linear equations."),
    50: ("im_first_edition", "Illustrative Mathematics Algebra 1", IM_BASE, "Unit 2 Linear Equations, Inequalities, and Systems", "CC BY 4.0", "approved_for_dry_run", "Primary IM mapping for graphing systems."),
    51: ("im_first_edition", "Illustrative Mathematics Algebra 1", IM_BASE, "Unit 2 Linear Equations, Inequalities, and Systems", "CC BY 4.0", "approved_for_dry_run", "Primary IM mapping for solving systems; verify substitution lesson."),
    52: ("im_first_edition", "Illustrative Mathematics Algebra 1", IM_BASE, "Unit 2 Linear Equations, Inequalities, and Systems", "CC BY 4.0", "approved_for_dry_run", "Primary IM mapping for systems; verify elimination/addition method lesson."),
}


def build_algebra_source_mappings() -> list[AlgebraSourceMapping]:
    rows: list[AlgebraSourceMapping] = []
    for topic in ALGEBRA_TOPIC_PLAN:
        source_key, title, url, section, license_name, decision, notes = _SOURCE_BY_TOPIC[topic.topic_id]
        rows.append(
            AlgebraSourceMapping(
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
                import_notes=notes,
            )
        )
    return rows


def build_manifest() -> dict[str, object]:
    rows = build_algebra_source_mappings()
    source_counts: dict[str, int] = {}
    for row in rows:
        source_counts[row.source_key] = source_counts.get(row.source_key, 0) + 1
    return {
        "stage": "13",
        "subject": "Algebra",
        "mode": "local_dry_run_manifest_only",
        "production_mutation": False,
        "db_import": False,
        "rag_chunk_creation": False,
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

    parser = argparse.ArgumentParser(description="Build Stage 13 Algebra source dry-run manifest")
    parser.add_argument("--out", default="/tmp/ai-tutor-algebra-source-dry-run.json")
    args = parser.parse_args()
    out = write_manifest(Path(args.out))
    manifest = json.loads(out.read_text(encoding="utf-8"))
    print(json.dumps({"ok": True, "out": str(out), "topic_count": manifest["topic_count"], "source_counts": manifest["source_counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
