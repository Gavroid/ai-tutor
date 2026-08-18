"""Autonomous quality checks for Math pilot content.

Phase 1 starts with deterministic checks over existing Math fallback tasks. This
module is intentionally local/read-only: it does not call production, mutate DB,
or consume student AI budget.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
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


def audit_explanation_samples(samples: Sequence[Mapping[str, object]]) -> QualityReport:
    """Audit captured explain outputs without calling a provider or production."""
    rows: list[dict[str, object]] = []
    all_issues: list[QualityIssue] = []
    for idx, sample in enumerate(samples, start=1):
        raw_topic_id = sample.get("topic_id")
        topic_id = raw_topic_id if isinstance(raw_topic_id, int) else None
        content = str(sample.get("content") or "").strip()
        issues = audit_student_visible_text(content, field="explanation", topic_id=topic_id)
        if len(content) < 250:
            issues.append(
                QualityIssue(
                    topic_id,
                    "explanation",
                    "explanation_too_short",
                    "Explanation is shorter than the runtime retry/fallback threshold.",
                )
            )
        required_markers = ("пример", "проверь", "правил")
        lowered = content.lower()
        if content and not any(marker in lowered for marker in required_markers):
            issues.append(
                QualityIssue(
                    topic_id,
                    "explanation",
                    "missing_instructional_structure",
                    "Explanation lacks example/check/rule structure.",
                )
            )
        all_issues.extend(issues)
        rows.append({
            "sample_id": sample.get("sample_id") or idx,
            "topic_id": topic_id,
            "topic_name": sample.get("topic_name"),
            "status": "pass" if not issues else "fail",
            "content_chars": len(content),
            "issue_count": len(issues),
            "issues": [issue.to_dict() for issue in issues],
        })
    fail_count = sum(1 for row in rows if row["status"] == "fail")
    return QualityReport(topic_count=len(rows), pass_count=len(rows) - fail_count, fail_count=fail_count, rows=rows, issues=all_issues)


def load_explanation_samples(path: str | Path) -> list[Mapping[str, object]]:
    """Load explanation samples from a JSON array for offline quality audits."""
    payload = json.loads(Path(path).read_text())
    if not isinstance(payload, list):
        raise ValueError("Explanation samples file must contain a JSON array.")
    samples: list[Mapping[str, object]] = []
    for item in payload:
        if not isinstance(item, Mapping):
            raise ValueError("Each explanation sample must be an object.")
        samples.append(item)
    return samples


def _format_local_explanation_sample(topic_id: int, row: Mapping[str, object]) -> str:
    question = str(row.get("question_text") or "").strip()
    explanation = str(row.get("explanation") or "").strip()
    mistakes_raw = row.get("typical_mistakes")
    mistakes = [str(item).strip() for item in mistakes_raw] if isinstance(mistakes_raw, list) else []
    mistake_text = mistakes[0] if mistakes else "Не пропускай промежуточные шаги."
    return (
        f"### Правило\n{explanation} Это правило помогает решить задание по теме без угадывания.\n\n"
        f"### Пример\n{question} Сначала прочитай условие, затем выполни действие из правила и сравни с вариантами ответа.\n\n"
        f"### Частая ошибка\n{mistake_text}. Проверь, что ты не сделал эту ошибку.\n\n"
        f"### Проверь себя\nОбъясни своими словами, почему правильный ответ получается именно так. Тема #{topic_id}."
    )


def build_local_sample_capture(
    *,
    topic_ids: Sequence[int] | None = None,
    fallbacks: Mapping[int, Mapping[str, object]] | None = None,
) -> list[dict[str, object]]:
    """Build offline explanation/practice samples from the deterministic Math fallback bank."""
    source = fallbacks or FALLBACKS
    selected = list(topic_ids) if topic_ids is not None else select_default_sample_topics()
    samples: list[dict[str, object]] = []
    for topic_id in selected:
        row = source.get(topic_id)
        if row is None:
            samples.append({
                "sample_id": f"missing-{topic_id}",
                "kind": "missing",
                "topic_id": topic_id,
                "topic_name": None,
                "source": "local_fallback_bank",
                "content": "",
                "metadata": {"error": "missing_topic"},
            })
            continue
        topic_name = str(row.get("topic_name") or row.get("topic") or row.get("question_text") or "").strip() or None
        samples.append({
            "sample_id": f"explanation-{topic_id}",
            "kind": "explanation",
            "topic_id": topic_id,
            "topic_name": topic_name,
            "source": "local_fallback_bank",
            "content": _format_local_explanation_sample(topic_id, row),
            "metadata": {"question_text": row.get("question_text")},
        })
        samples.append({
            "sample_id": f"practice-{topic_id}",
            "kind": "practice",
            "topic_id": topic_id,
            "topic_name": topic_name,
            "source": "local_fallback_bank",
            "content": str(row.get("question_text") or ""),
            "metadata": {
                "type": row.get("type"),
                "option_count": len(row.get("options") or []) if isinstance(row.get("options"), list) else 0,
                "has_correct_answer": bool(row.get("correct_answer")),
                "has_typical_mistakes": bool(row.get("typical_mistakes")),
            },
        })
    return samples


def _practice_sample_issues(sample: Mapping[str, object]) -> list[str]:
    metadata = sample.get("metadata") if isinstance(sample.get("metadata"), Mapping) else {}
    issues: list[str] = []
    if not str(sample.get("content") or "").strip():
        issues.append("missing_practice_text")
    if metadata.get("type") != "single":
        issues.append("unsupported_practice_type")
    if int(metadata.get("option_count") or 0) < 2:
        issues.append("missing_options")
    if not metadata.get("has_correct_answer"):
        issues.append("missing_correct_answer")
    if not metadata.get("has_typical_mistakes"):
        issues.append("missing_typical_mistakes")
    return issues


def build_sample_quality_matrix(samples: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """Summarize captured explanation/practice samples into per-topic quality rows."""
    by_topic: dict[int, dict[str, object]] = {}
    for sample in samples:
        raw_topic_id = sample.get("topic_id")
        if not isinstance(raw_topic_id, int):
            continue
        row = by_topic.setdefault(raw_topic_id, {
            "topic_id": raw_topic_id,
            "source": sample.get("source") or "unknown",
            "explanation_status": "missing",
            "practice_status": "missing",
            "issue_count": 0,
            "issues": [],
        })
        kind = sample.get("kind")
        issues: list[str] = []
        if kind == "explanation":
            report = audit_explanation_samples([sample])
            issues = [issue.code for issue in report.issues]
            row["explanation_status"] = "pass" if not issues else "fail"
        elif kind == "practice":
            issues = _practice_sample_issues(sample)
            row["practice_status"] = "pass" if not issues else "fail"
        elif kind == "missing":
            issues = ["missing_topic"]
            row["explanation_status"] = "missing"
            row["practice_status"] = "missing"
        if issues:
            current = row.get("issues")
            if isinstance(current, list):
                current.extend(issues)
            row["issue_count"] = int(row.get("issue_count") or 0) + len(issues)
    return [by_topic[topic_id] for topic_id in sorted(by_topic)]


def format_sample_quality_matrix_markdown(rows: Sequence[Mapping[str, object]]) -> str:
    """Render a safe Markdown matrix without hidden answers or raw sample content."""
    lines = [
        "# Math Quality Sample Matrix",
        "",
        "| Topic ID | Source | Explanation | Practice | Issues |",
        "|---:|---|---|---|---:|",
    ]
    for row in rows:
        lines.append(
            "| {topic_id} | {source} | {explanation_status} | {practice_status} | {issue_count} |".format(
                topic_id=row.get("topic_id"),
                source=row.get("source"),
                explanation_status=row.get("explanation_status"),
                practice_status=row.get("practice_status"),
                issue_count=row.get("issue_count"),
            )
        )
    return "\n".join(lines) + "\n"


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
    parser.add_argument("--explanation-samples", help="Path to JSON array of captured explain outputs")
    parser.add_argument("--capture-local-samples", action="store_true", help="Emit local fallback-bank explanation/practice samples")
    parser.add_argument("--sample-matrix", action="store_true", help="Emit Markdown matrix for local captured samples")
    args = parser.parse_args()
    if args.capture_local_samples or args.sample_matrix:
        samples = build_local_sample_capture(topic_ids=select_default_sample_topics() if args.sample_only else None)
        if args.sample_matrix:
            print(format_sample_quality_matrix_markdown(build_sample_quality_matrix(samples)))
        else:
            print(json.dumps(samples, ensure_ascii=False, indent=2 if args.json else None))
        return 0
    if args.explanation_samples:
        report = audit_explanation_samples(load_explanation_samples(args.explanation_samples))
    else:
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
