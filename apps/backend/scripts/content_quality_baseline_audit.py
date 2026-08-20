"""All-subject content quality baseline audit.

This script is read-only. It audits local source manifests and deterministic
fallback banks, then optionally overlays production readiness counts from
/api/v1/subjects. It does not mutate DB, RAG, Redis, or production.
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Mapping, Sequence, cast

from app.subjects.curriculum_7_class import CURRICULUM_7_CLASS
from scripts.algebra_fallback_seed import FALLBACKS as ALGEBRA_FALLBACKS
from scripts.geometry_fallback_seed import FALLBACKS as GEOMETRY_FALLBACKS
from scripts.geometry_internal_source_manifest import build_geometry_internal_source_manifest
from scripts.math_fallback_seed import FALLBACKS as MATH_FALLBACKS
from scripts.math_quality_lab import audit_student_visible_text
from scripts.remaining_subjects_internal_source_manifest import build_remaining_subjects_internal_source_manifest

SUBJECT_CODE_ALIAS = {"geometry": "geom"}
TEXTBOOK_GRADE_MIN_CHARS = 420
INTERNAL_SOURCE_MARKERS = ("internal://", "project_owned_text_notes", "project-owned internal notes")
SUBJECT_ANCHORS: dict[str, tuple[str, ...]] = {
    "rus": ("орфограмм", "морфолог", "синтакс", "пунктуац"),
    "lit": ("жанр", "герой", "деталь", "конфликт", "автор"),
    "math": ("числ", "дроб", "процент", "координат", "уравнен"),
    "algebra": ("выраж", "уравнен", "функц", "степен", "многочлен"),
    "geom": ("угол", "прям", "треуголь", "окруж", "отрез"),
    "phys": ("величин", "единиц", "опыт", "формул", "явлен"),
    "inf": ("алгоритм", "данн", "код", "программ", "устрой"),
    "hist": ("период", "событ", "причин", "последств", "участник"),
    "soc": ("обще", "прав", "государ", "эконом", "норм"),
    "geo": ("карт", "объект", "процесс", "земл", "населен"),
    "bio": ("организм", "клет", "орган", "сред", "признак"),
    "eng": ("англий", "grammar", "phrase", "слово", "форма", "реч"),
}


@dataclass(frozen=True)
class SubjectAudit:
    code: str
    name: str
    topic_count: int
    fallback_count: int
    source_count: int
    source_mode: str
    technical_issue_count: int
    quality_flags: list[str]
    priority: str

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "name": self.name,
            "topic_count": self.topic_count,
            "fallback_count": self.fallback_count,
            "source_count": self.source_count,
            "source_mode": self.source_mode,
            "technical_issue_count": self.technical_issue_count,
            "quality_flags": self.quality_flags,
            "priority": self.priority,
        }


def _subject_topic_counts() -> dict[str, tuple[str, int]]:
    return {
        str(subject["code"]): (
            str(subject["name"]),
            sum(len(topics) for _section, topics in subject["sections"]),
        )
        for subject in CURRICULUM_7_CLASS
    }


def _normalize_subject_code(code: object) -> str:
    value = str(code or "").strip()
    return SUBJECT_CODE_ALIAS.get(value, value)


def _fallback_banks() -> dict[str, Mapping[int, Mapping[str, object]]]:
    remaining = build_remaining_subjects_internal_source_manifest()
    remaining_by_code: dict[str, dict[int, Mapping[str, object]]] = defaultdict(dict)
    for fallback in cast(list[Mapping[str, object]], remaining["fallbacks"]):
        topic_id = fallback.get("topic_id")
        if not isinstance(topic_id, int):
            continue
        # Remaining-subject topic ids are unique in the generated curriculum. Map by manifest material rows.
        material = next(
            (
                row
                for row in cast(list[Mapping[str, object]], remaining["materials"])
                if row.get("topic_id") == topic_id
            ),
            None,
        )
        if material is None:
            continue
        remaining_by_code[str(material["subject_code"])][topic_id] = fallback
    banks: dict[str, Mapping[int, Mapping[str, object]]] = {
        "math": MATH_FALLBACKS,
        "algebra": ALGEBRA_FALLBACKS,
        "geom": GEOMETRY_FALLBACKS,
    }
    banks.update(remaining_by_code)
    return banks


def _source_rows_by_subject() -> dict[str, list[Mapping[str, object]]]:
    rows: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    geometry = build_geometry_internal_source_manifest()
    for material in cast(list[Mapping[str, object]], geometry["materials"]):
        rows[_normalize_subject_code(material.get("subject_code"))].append(material)
    remaining = build_remaining_subjects_internal_source_manifest()
    for material in cast(list[Mapping[str, object]], remaining["materials"]):
        rows[_normalize_subject_code(material.get("subject_code"))].append(material)
    return rows


def _fallback_issues(code: str, fallback: Mapping[str, object]) -> list[str]:
    issues: list[str] = []
    raw_topic_id = fallback.get("topic_id")
    topic_id: int | None = raw_topic_id if isinstance(raw_topic_id, int) else None
    for field in ("question_text", "correct_answer", "explanation"):
        issues.extend(issue.code for issue in audit_student_visible_text(fallback.get(field), field=field, topic_id=topic_id))
    options = fallback.get("options")
    if not isinstance(options, list) or len(options) < 2:
        issues.append("missing_options")
    if fallback.get("type") != "single":
        issues.append("unsupported_type")
    mistakes = fallback.get("typical_mistakes")
    if not isinstance(mistakes, list) or not mistakes:
        issues.append("missing_typical_mistakes")
    return issues


def _fallback_anchor_miss_ratio(code: str, fallbacks: Sequence[Mapping[str, object]]) -> float:
    anchors = SUBJECT_ANCHORS.get(code, ())
    if not anchors or not fallbacks:
        return 0.0
    misses = 0
    for fallback in fallbacks:
        text = " ".join(str(fallback.get(key) or "") for key in ("question_text", "explanation", "correct_answer"))
        lowered = text.lower()
        if not any(anchor in lowered for anchor in anchors):
            misses += 1
    return misses / len(fallbacks)


def _source_issues(code: str, material: Mapping[str, object]) -> list[str]:
    issues: list[str] = []
    content = str(material.get("content") or "").strip()
    lowered = content.lower()
    if len(content) < 180:
        issues.append("source_note_too_short")
    visible_tokens = ("<think>", "json", "correct_answer", "parser", "provider", "|---")
    if any(token in lowered for token in visible_tokens):
        issues.append("student_visible_artifact")
    anchors = SUBJECT_ANCHORS.get(code, ())
    if anchors and not any(anchor in lowered for anchor in anchors):
        issues.append("missing_subject_anchor")
    return issues


def _source_mode(materials: Sequence[Mapping[str, object]]) -> str:
    if not materials:
        return "missing_local_manifest"
    blob = " ".join(
        str(material.get(key) or "")
        for material in materials
        for key in ("source_url", "license", "source", "status")
    ).lower()
    if any(marker in blob for marker in INTERNAL_SOURCE_MARKERS):
        return "project_owned_internal_notes"
    return "external_or_mixed_sources"


def _quality_flags(
    *,
    code: str,
    topic_count: int,
    fallback_count: int,
    source_count: int,
    source_mode: str,
    fallbacks: Sequence[Mapping[str, object]],
    materials: Sequence[Mapping[str, object]],
) -> list[str]:
    flags: list[str] = []
    if fallback_count != topic_count:
        flags.append("fallback_coverage_gap")
    if source_count != topic_count:
        flags.append("source_manifest_gap")
    if source_mode == "project_owned_internal_notes":
        flags.append("internal_notes_not_textbook_grade")
    if source_mode == "missing_local_manifest":
        flags.append("no_local_source_manifest")
    source_lengths = [len(str(material.get("content") or "")) for material in materials]
    if source_lengths and sum(source_lengths) / len(source_lengths) < TEXTBOOK_GRADE_MIN_CHARS:
        flags.append("source_notes_shallow")
    if fallback_count and _fallback_anchor_miss_ratio(code, fallbacks) >= 0.35:
        flags.append("fallbacks_need_subject_language_depth")
    if code in {"phys", "eng", "hist", "bio", "geo", "lit"} and source_mode == "project_owned_internal_notes":
        flags.append("needs_verified_subject_sources")
    return flags


def _priority(flags: Sequence[str], technical_issue_count: int) -> str:
    if technical_issue_count:
        return "P0_fix_technical_gate"
    high_risk = {"no_local_source_manifest", "source_manifest_gap", "fallback_coverage_gap"}
    if high_risk.intersection(flags):
        return "P0_fill_coverage"
    if "needs_verified_subject_sources" in flags or "fallbacks_template_like" in flags:
        return "P1_textbook_grade_upgrade"
    if "source_notes_shallow" in flags or "internal_notes_not_textbook_grade" in flags:
        return "P2_depth_upgrade"
    return "P3_monitor"


def build_content_quality_baseline() -> dict[str, object]:
    counts = _subject_topic_counts()
    banks = _fallback_banks()
    sources = _source_rows_by_subject()
    rows: list[SubjectAudit] = []
    issue_counter: Counter[str] = Counter()
    for code, (name, topic_count) in counts.items():
        fallbacks = list(banks.get(code, {}).values())
        materials = sources.get(code, [])
        fallback_issue_codes = [issue for fallback in fallbacks for issue in _fallback_issues(code, fallback)]
        source_issue_codes = [issue for material in materials for issue in _source_issues(code, material)]
        for issue in fallback_issue_codes + source_issue_codes:
            issue_counter[issue] += 1
        source_mode = _source_mode(materials)
        flags = _quality_flags(
            code=code,
            topic_count=topic_count,
            fallback_count=len(fallbacks),
            source_count=len(materials),
            source_mode=source_mode,
            fallbacks=fallbacks,
            materials=materials,
        )
        technical_issue_count = len(fallback_issue_codes) + len(source_issue_codes)
        rows.append(
            SubjectAudit(
                code=code,
                name=name,
                topic_count=topic_count,
                fallback_count=len(fallbacks),
                source_count=len(materials),
                source_mode=source_mode,
                technical_issue_count=technical_issue_count,
                quality_flags=flags,
                priority=_priority(flags, technical_issue_count),
            )
        )
    priority_counts = Counter(row.priority for row in rows)
    return {
        "ok": True,
        "mode": "content_quality_baseline_local_read_only",
        "production_mutation": False,
        "db_write": False,
        "rag_write": False,
        "subject_count": len(rows),
        "topic_count": sum(row.topic_count for row in rows),
        "technical_issue_count": sum(row.technical_issue_count for row in rows),
        "priority_counts": dict(sorted(priority_counts.items())),
        "issue_counts": dict(sorted(issue_counter.items())),
        "subjects": [row.to_dict() for row in rows],
    }


def fetch_production_subjects(base_url: str, *, insecure: bool = False) -> list[dict[str, Any]]:
    context = ssl._create_unverified_context() if insecure else None
    with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/v1/subjects", timeout=20, context=context) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("subjects endpoint must return a list")
    return cast(list[dict[str, Any]], payload)


def overlay_production_readiness(report: dict[str, object], subjects: Sequence[Mapping[str, object]]) -> dict[str, object]:
    by_code = {_normalize_subject_code(subject.get("code")): subject for subject in subjects}
    out = dict(report)
    enriched_subjects: list[dict[str, object]] = []
    readiness_problems: list[str] = []
    for row in cast(list[dict[str, object]], report["subjects"]):
        code = str(row["code"])
        prod = by_code.get(code)
        enriched = dict(row)
        if prod is None:
            readiness_problems.append(f"{code}:missing_in_production")
        else:
            enriched["production_mvp_status"] = prod.get("mvp_status")
            enriched["production_route_ready"] = prod.get("route_ready")
            enriched["production_rag_ready"] = prod.get("rag_ready")
            enriched["production_practice_ready"] = prod.get("practice_ready")
            prod_counts = {
                "topic_count": prod.get("topic_count"),
                "route_topic_count": prod.get("route_topic_count"),
                "source_topic_count": prod.get("source_topic_count"),
                "practice_topic_count": prod.get("practice_topic_count"),
            }
            enriched["production_counts"] = prod_counts
            if prod.get("mvp_status") != "mvp_ready":
                readiness_problems.append(f"{code}:not_mvp_ready")
            if not (prod_counts["topic_count"] == prod_counts["route_topic_count"] == prod_counts["source_topic_count"] == prod_counts["practice_topic_count"]):
                readiness_problems.append(f"{code}:production_count_mismatch")
        enriched_subjects.append(enriched)
    out["subjects"] = enriched_subjects
    out["production_subject_count"] = len(subjects)
    out["production_readiness_problems"] = readiness_problems
    return out


def format_markdown(report: Mapping[str, object]) -> str:
    subjects = cast(list[Mapping[str, object]], report["subjects"])
    lines = [
        "# AI-Tutor Content Quality Baseline",
        "",
        "## Summary",
        "",
        f"- Mode: `{report['mode']}`",
        f"- Production mutation: `{report['production_mutation']}`",
        f"- Subjects audited: {report['subject_count']}",
        f"- Topics audited: {report['topic_count']}",
        f"- Technical issue count: {report['technical_issue_count']}",
        f"- Priority counts: `{json.dumps(report['priority_counts'], ensure_ascii=False)}`",
    ]
    if "production_readiness_problems" in report:
        lines.append(f"- Production readiness problems: `{json.dumps(report['production_readiness_problems'], ensure_ascii=False)}`")
    lines.extend([
        "",
        "## Subject Matrix",
        "",
        "| Subject | Topics | Fallbacks | Sources | Source Mode | Technical Issues | Priority | Flags |",
        "|---|---:|---:|---:|---|---:|---|---|",
    ])
    for row in subjects:
        lines.append(
            "| {code} | {topic_count} | {fallback_count} | {source_count} | {source_mode} | {technical_issue_count} | {priority} | {flags} |".format(
                code=row["code"],
                topic_count=row["topic_count"],
                fallback_count=row["fallback_count"],
                source_count=row["source_count"],
                source_mode=row["source_mode"],
                technical_issue_count=row["technical_issue_count"],
                priority=row["priority"],
                flags=", ".join(cast(list[str], row["quality_flags"])) or "—",
            )
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- `P0_*` means coverage or technical gates must be fixed before content depth work.",
        "- `P1_textbook_grade_upgrade` means mechanically ready but should receive verified subject sources and richer explanations next.",
        "- `P2_depth_upgrade` means safe MVP internal notes exist but remain shallow compared with textbook-grade coverage.",
        "- This audit is local/read-only; it does not import sources, rebuild RAG, or mutate production data.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit all-subject AI-Tutor content quality baseline")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--base-url", help="Optional production base URL for readiness overlay")
    parser.add_argument("--insecure", action="store_true", help="Allow self-signed TLS for LAN checks")
    args = parser.parse_args()
    report = build_content_quality_baseline()
    if args.base_url:
        report = overlay_production_readiness(report, fetch_production_subjects(args.base_url, insecure=args.insecure))
    if args.markdown:
        print(format_markdown(report))
    elif args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({
            "ok": report["ok"],
            "subject_count": report["subject_count"],
            "topic_count": report["topic_count"],
            "technical_issue_count": report["technical_issue_count"],
            "priority_counts": report["priority_counts"],
        }, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
