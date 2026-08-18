from __future__ import annotations

from scripts.math_fallback_seed import FALLBACKS
from scripts.math_quality_lab import (
    DEFAULT_SAMPLE_TOPIC_IDS,
    QualityIssue,
    audit_fallback_bank,
    audit_student_visible_text,
    build_quality_report,
    select_default_sample_topics,
)


def test_student_visible_text_audit_flags_raw_json_think_and_math_artifacts() -> None:
    issues = audit_student_visible_text(
        '```json\n{"correct_answer": "42"}\n``` <think>secret</think> $$ \\frac{1}{2}',
        field="explanation",
    )

    issue_codes = {issue.code for issue in issues}
    assert "raw_json" in issue_codes
    assert "hidden_answer_leak" in issue_codes
    assert "reasoning_leak" in issue_codes
    assert "broken_math_marker" in issue_codes
    assert "markdown_fence" in issue_codes


def test_student_visible_text_audit_accepts_child_readable_explanation() -> None:
    text = (
        "Чтобы найти среднее арифметическое, сложи все числа и раздели сумму "
        "на количество чисел. Например, для 4, 5 и 3 получаем (4 + 5 + 3) / 3 = 4."
    )

    assert audit_student_visible_text(text, field="explanation") == []


def test_student_visible_text_audit_flags_short_or_provider_words() -> None:
    issues = audit_student_visible_text("AI не вернул JSON", field="explanation")

    assert {issue.code for issue in issues} >= {"too_short", "provider_artifact"}


def test_default_sample_topics_are_stable_subset_of_math_fallback_bank() -> None:
    sample = select_default_sample_topics()

    assert sample == DEFAULT_SAMPLE_TOPIC_IDS
    assert sample[0] == min(FALLBACKS)
    assert sample[-1] == max(FALLBACKS)
    assert set(sample).issubset(FALLBACKS)
    assert len(sample) >= 8


def test_audit_fallback_bank_covers_every_math_topic_and_reports_no_issues() -> None:
    report = audit_fallback_bank(FALLBACKS)

    assert report.topic_count == 42
    assert report.pass_count == 42
    assert report.fail_count == 0
    assert report.issues == []


def test_build_quality_report_can_focus_on_sample_topics() -> None:
    report = build_quality_report(FALLBACKS, topic_ids=DEFAULT_SAMPLE_TOPIC_IDS)

    assert report.topic_count == len(DEFAULT_SAMPLE_TOPIC_IDS)
    assert report.pass_count == len(DEFAULT_SAMPLE_TOPIC_IDS)
    assert report.fail_count == 0
    assert all(row["topic_id"] in DEFAULT_SAMPLE_TOPIC_IDS for row in report.rows)


def test_quality_issue_serializes_to_plain_dict() -> None:
    issue = QualityIssue(topic_id=187, field="question_text", code="raw_json", detail="bad")

    assert issue.to_dict() == {
        "topic_id": 187,
        "field": "question_text",
        "code": "raw_json",
        "detail": "bad",
    }
