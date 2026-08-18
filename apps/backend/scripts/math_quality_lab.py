"""Autonomous quality checks for Math pilot content.

Phase 1 starts with deterministic checks over existing Math fallback tasks. This
module is intentionally local/read-only: it does not call production, mutate DB,
or consume student AI budget.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from scripts.math_fallback_seed import FALLBACKS

DEFAULT_SAMPLE_TOPIC_IDS: list[int] = [187, 188, 189, 195, 200, 203, 208, 213, 219, 222, 225, 228]
_PROVIDER_WORDS = re.compile(r"\b(AI|JSON|provider|провайдер|резервн(?:ое|ый)|fallback)\b", re.IGNORECASE)
_RAW_JSON = re.compile(r"(?s)\{\s*\"[^{}]+\"\s*:")
_MARKDOWN_FENCE = re.compile(r"```")
_TABLE_SEPARATOR = re.compile(r"\|\s*-{3,}\s*\|")
_REASONING = re.compile(r"(?is)<\s*think\b|&lt;\s*think\b|reasoning")
_BROKEN_MATH = re.compile(r"\$\$|\\\\(?:frac|text)\b|\\(?:frac|text)\b")


@dataclass(frozen=True)
class QualityIssue:
    topic_id: int | None
    field: str
    code: str
    detail: str

    def to_dict(self) -> dict[str, object]:
        return {"topic_id": self.topic_id, "field": self.field, "code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class QualityReport:
    topic_count: int
    pass_count: int
    fail_count: int
    rows: list[dict[str, object]]
    issues: list[QualityIssue]

    def to_dict(self) -> dict[str, object]:
        return {
            "topic_count": self.topic_count,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "rows": self.rows,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def select_default_sample_topics() -> list[int]:
    """Return stable representative Math topics for the first quality sweep."""
    return list(DEFAULT_SAMPLE_TOPIC_IDS)


def audit_student_visible_text(text: object, *, field: str, topic_id: int | None = None) -> list[QualityIssue]:
    """Find student-facing output defects in a single text field."""
    value = str(text or "").strip()
    issues: list[QualityIssue] = []
    min_len_by_field = {"question_text": 12, "explanation": 24, "correct_answer": 1}
    min_len = min_len_by_field.get(field, 24)
    if len(value) < min_len:
        issues.append(QualityIssue(topic_id, field, "too_short", "Text is too short to be useful."))
    if _RAW_JSON.search(value):
        issues.append(QualityIssue(topic_id, field, "raw_json", "Looks like raw JSON."))
    if "correct_answer" in value or "\"answer\"" in value:
        issues.append(QualityIssue(topic_id, field, "hidden_answer_leak", "Hidden answer marker is visible."))
    if _REASONING.search(value):
        issues.append(QualityIssue(topic_id, field, "reasoning_leak", "Reasoning marker is visible."))
    if _MARKDOWN_FENCE.search(value):
        issues.append(QualityIssue(topic_id, field, "markdown_fence", "Markdown fence marker is visible."))
    if _TABLE_SEPARATOR.search(value):
        issues.append(QualityIssue(topic_id, field, "broken_table", "Markdown table separator is visible."))
    if _BROKEN_MATH.search(value):
        issues.append(QualityIssue(topic_id, field, "broken_math_marker", "Raw math marker is visible."))
    if _PROVIDER_WORDS.search(value):
        issues.append(QualityIssue(topic_id, field, "provider_artifact", "Provider/protocol wording is visible."))
    return issues


def _audit_fallback_row(topic_id: int, row: Mapping[str, object]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    for field in ("question_text", "correct_answer", "explanation"):
        issues.extend(audit_student_visible_text(row.get(field), field=field, topic_id=topic_id))
    options = row.get("options")
    if not isinstance(options, list) or len(options) < 2:
        issues.append(QualityIssue(topic_id, "options", "missing_options", "Single-choice fallback needs at least two options."))
    if row.get("type") != "single":
        issues.append(QualityIssue(topic_id, "type", "unsupported_type", "Pilot fallback should be single-choice."))
    mistakes = row.get("typical_mistakes")
    if not isinstance(mistakes, list) or not mistakes:
        issues.append(QualityIssue(topic_id, "typical_mistakes", "missing_mistakes", "Typical mistakes are required."))
    return issues


def build_quality_report(
    fallbacks: Mapping[int, Mapping[str, object]] | None = None,
    *,
    topic_ids: Sequence[int] | None = None,
) -> QualityReport:
    """Audit selected Math fallback rows and return a serializable report."""
    source = fallbacks or FALLBACKS
    selected = list(topic_ids) if topic_ids is not None else sorted(source)
    rows: list[dict[str, object]] = []
    all_issues: list[QualityIssue] = []
    for topic_id in selected:
        row = source.get(topic_id)
        if row is None:
            issue = QualityIssue(topic_id, "topic_id", "missing_topic", "No fallback exists for topic.")
            all_issues.append(issue)
            rows.append({"topic_id": topic_id, "status": "fail", "issues": [issue.to_dict()]})
            continue
        issues = _audit_fallback_row(topic_id, row)
        all_issues.extend(issues)
        rows.append({
            "topic_id": topic_id,
            "status": "pass" if not issues else "fail",
            "question_text": row.get("question_text"),
            "issue_count": len(issues),
            "issues": [issue.to_dict() for issue in issues],
        })
    fail_count = sum(1 for row in rows if row["status"] == "fail")
    return QualityReport(topic_count=len(rows), pass_count=len(rows) - fail_count, fail_count=fail_count, rows=rows, issues=all_issues)


def audit_fallback_bank(fallbacks: Mapping[int, Mapping[str, object]] | None = None) -> QualityReport:
    return build_quality_report(fallbacks or FALLBACKS)


def _format_markdown(report: QualityReport) -> str:
    lines = [
        "# Math Autonomous Quality Lab Snapshot",
        "",
        f"- Topics checked: {report.topic_count}",
        f"- Passed: {report.pass_count}",
        f"- Failed: {report.fail_count}",
        "",
        "| Topic ID | Status | Issues |",
        "|---:|---|---:|",
    ]
    for row in report.rows:
        raw_issue_count = row.get("issue_count", 0)
        issue_count = raw_issue_count if isinstance(raw_issue_count, int) else 0
        if "issues" in row and not issue_count:
            issue_values = row.get("issues")
            issue_count = len(issue_values) if isinstance(issue_values, list) else 0
        lines.append(f"| {row['topic_id']} | {row['status']} | {issue_count} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args()
    topic_ids = select_default_sample_topics() if args.sample_only else None
    report = build_quality_report(topic_ids=topic_ids)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    elif args.markdown:
        print(_format_markdown(report))
    else:
        print(json.dumps({"topic_count": report.topic_count, "pass_count": report.pass_count, "fail_count": report.fail_count}, ensure_ascii=False))
    return 0 if report.fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
