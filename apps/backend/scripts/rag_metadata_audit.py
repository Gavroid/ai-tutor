"""Audit RAG chunk metadata quality before subject readiness promotion.

Stage 15 contract: false source/RAG readiness must be automatically detectable.
The audit is read-only; it can run against DB rows or pure test fixtures.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Iterable, cast

REQUIRED_KEYS = (
    "topic_id",
    "topic_name",
    "source_title",
    "license",
    "attribution",
)

SUBJECT_SOURCE_HINTS = {
    "algebra": ("algebra", "алгебра"),
    "geometry": ("geometry", "геометр", "euclid", "евклид"),
    "math": ("математ", "vilenkin", "виленкин"),
}


@dataclass(frozen=True)
class AuditFinding:
    chunk_id: int | str | None
    material_id: int | None
    material_topic_id: int | None
    problems: list[str]


def _loads_metadata(value: object) -> tuple[dict[str, Any], list[str]]:
    if isinstance(value, dict):
        return value, []
    if value is None or value == "":
        return {}, ["metadata_json_empty"]
    if not isinstance(value, str):
        return {}, ["metadata_json_not_string_or_dict"]
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}, ["metadata_json_invalid"]
    if not isinstance(parsed, dict):
        return {}, ["metadata_json_not_object"]
    return parsed, []


def _text(value: object) -> str:
    return str(value or "").strip()


def audit_chunk_metadata(row: dict[str, object], *, expected_subject_code: str | None = None) -> list[str]:
    metadata, problems = _loads_metadata(row.get("metadata_json"))

    for key in REQUIRED_KEYS:
        if not _text(metadata.get(key)):
            problems.append(f"missing:{key}")

    if not (_text(metadata.get("source_section")) or _text(metadata.get("page_number")) or _text(metadata.get("page_range"))):
        problems.append("missing:source_section_or_page")

    material_topic_id = row.get("material_topic_id")
    metadata_topic_id = metadata.get("topic_id")
    if material_topic_id is not None and metadata_topic_id is not None:
        try:
            if int(cast(Any, material_topic_id)) != int(cast(Any, metadata_topic_id)):
                problems.append(f"topic_id_mismatch:metadata={metadata_topic_id} material={material_topic_id}")
        except (TypeError, ValueError):
            problems.append("topic_id_not_int")

    material_subject_code = _text(row.get("material_subject_code")).lower()
    metadata_subject_code = _text(metadata.get("subject_code")).lower()
    if expected_subject_code:
        expected = expected_subject_code.lower()
        if metadata_subject_code and metadata_subject_code != expected:
            problems.append(f"subject_code_mismatch:metadata={metadata_subject_code} expected={expected}")
        if material_subject_code and material_subject_code != expected:
            problems.append(f"material_subject_mismatch:material={material_subject_code} expected={expected}")

    if material_subject_code and metadata_subject_code and material_subject_code != metadata_subject_code:
        problems.append(f"material_metadata_subject_mismatch:metadata={metadata_subject_code} material={material_subject_code}")

    expected_for_source = (expected_subject_code or material_subject_code or metadata_subject_code).lower()
    if expected_for_source:
        haystack = " ".join(
            [
                _text(metadata.get("source_title")),
                _text(metadata.get("material_title")),
                _text(row.get("material_title")),
                _text(metadata.get("source_url")),
            ]
        ).lower()
        for subject, hints in SUBJECT_SOURCE_HINTS.items():
            if subject == expected_for_source:
                continue
            if any(hint in haystack for hint in hints):
                problems.append(f"source_subject_mismatch:source_looks_like={subject} expected={expected_for_source}")
                break

    return problems


def audit_rows(rows: Iterable[dict[str, object]], *, expected_subject_code: str | None = None) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for row in rows:
        problems = audit_chunk_metadata(row, expected_subject_code=expected_subject_code)
        chunk_id_value = row.get("chunk_id")
        material_id_value = row.get("material_id")
        material_topic_id_value = row.get("material_topic_id")
        findings.append(
            AuditFinding(
                chunk_id=cast(int | str | None, chunk_id_value),
                material_id=int(cast(Any, material_id_value)) if material_id_value is not None else None,
                material_topic_id=int(cast(Any, material_topic_id_value)) if material_topic_id_value is not None else None,
                problems=problems,
            )
        )
    return findings


def summarize_audit(findings: Iterable[AuditFinding]) -> dict[str, object]:
    rows = list(findings)
    problem_counter: Counter[str] = Counter(problem for row in rows for problem in row.problems)
    bad_rows = sum(1 for row in rows if row.problems)
    return {
        "rows_checked": len(rows),
        "ok_rows": len(rows) - bad_rows,
        "bad_rows": bad_rows,
        "problems": dict(sorted(problem_counter.items())),
    }


def _fetch_db_rows(expected_subject_code: str | None = None) -> list[dict[str, object]]:
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.rag_models import RagChunk
    from app.subjects import models as subj_models

    with SessionLocal() as db:
        stmt = (
            select(
                RagChunk.id.label("chunk_id"),
                RagChunk.material_id,
                RagChunk.metadata_json,
                subj_models.LearningMaterial.topic_id.label("material_topic_id"),
                subj_models.LearningMaterial.title.label("material_title"),
                subj_models.Subject.code.label("material_subject_code"),
            )
            .join(subj_models.LearningMaterial, subj_models.LearningMaterial.id == RagChunk.material_id)
            .join(subj_models.Topic, subj_models.Topic.id == subj_models.LearningMaterial.topic_id)
            .join(subj_models.Section, subj_models.Section.id == subj_models.Topic.section_id)
            .join(subj_models.Subject, subj_models.Subject.id == subj_models.Section.subject_id)
        )
        if expected_subject_code:
            stmt = stmt.where(subj_models.Subject.code == expected_subject_code)
        return [dict(row._mapping) for row in db.execute(stmt).all()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit RAG metadata quality contract")
    parser.add_argument("--subject-code", choices=["math", "algebra", "geometry"], default=None)
    parser.add_argument("--input-json", help="Read audit rows from a JSON fixture instead of the database")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    rows = json.loads(open(args.input_json, encoding="utf-8").read()) if args.input_json else _fetch_db_rows(args.subject_code)
    if not isinstance(rows, list):
        raise SystemExit("input JSON must be a list of row objects")
    findings = audit_rows(cast(list[dict[str, object]], rows), expected_subject_code=args.subject_code)
    summary = summarize_audit(findings)
    payload = {"summary": summary, "bad_rows": [asdict(row) for row in findings if row.problems]}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(summary, ensure_ascii=False))
    return 1 if summary["bad_rows"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
