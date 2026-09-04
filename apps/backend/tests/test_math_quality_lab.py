from __future__ import annotations

from scripts.math_fallback_seed import FALLBACKS
from scripts.math_quality_lab import (
    DEFAULT_SAMPLE_TOPIC_IDS,
    QualityIssue,
    audit_explanation_samples,
    audit_fallback_bank,
    audit_student_visible_text,
    build_local_sample_capture,
    build_quality_report,
    build_sample_quality_matrix,
    format_sample_quality_matrix_markdown,
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


def test_explanation_sample_audit_flags_short_raw_provider_output() -> None:
    report = audit_explanation_samples(
        [
            {
                "topic_id": 187,
                "topic_name": "Среднее арифметическое",
                "content": '{"answer": "42"} <think>hidden</think> AI не вернул JSON',
            }
        ]
    )

    assert report.topic_count == 1
    assert report.fail_count == 1
    issue_codes = {issue.code for issue in report.issues}
    assert "raw_json" in issue_codes
    assert "hidden_answer_leak" in issue_codes
    assert "reasoning_leak" in issue_codes
    assert "provider_artifact" in issue_codes
    assert "explanation_too_short" in issue_codes


def test_explanation_sample_audit_accepts_structured_child_readable_sample() -> None:
    content = (
        "**Среднее арифметическое** помогает найти обычное значение для нескольких чисел. "
        "Сначала сложи все числа, потом раздели сумму на количество чисел. "
        "### Пример\n"
        "Если оценки за три работы: 4, 5 и 3, сумма равна 12. Делим 12 на 3 и получаем 4. "
        "Это значит, что средняя оценка равна 4. "
        "### Частая ошибка\n"
        "Не дели сумму на случайное число: делить нужно именно на количество значений. "
        "### Проверь себя\n"
        "Почему для чисел 2, 6, 7 и 5 мы делим сумму на 4?"
    )

    report = audit_explanation_samples([{"topic_id": 187, "topic_name": "Среднее арифметическое", "content": content}])

    assert report.topic_count == 1
    assert report.pass_count == 1
    assert report.fail_count == 0
    assert report.issues == []


def test_build_local_sample_capture_emits_explanation_and_practice_samples() -> None:
    samples = build_local_sample_capture(topic_ids=[187, 188])

    kinds = {sample["kind"] for sample in samples}
    assert kinds == {"explanation", "practice"}
    assert len(samples) == 4
    assert {sample["topic_id"] for sample in samples} == {187, 188}
    assert all(sample["source"] == "local_fallback_bank" for sample in samples)
    assert all(sample["content"] for sample in samples)
    explanation_samples = [sample for sample in samples if sample["kind"] == "explanation"]
    report = audit_explanation_samples(explanation_samples)
    assert report.topic_count == 2
    assert report.fail_count == 0


def test_build_local_sample_capture_marks_missing_topic_without_crashing() -> None:
    samples = build_local_sample_capture(topic_ids=[999999])

    assert samples == [
        {
            "sample_id": "missing-999999",
            "kind": "missing",
            "topic_id": 999999,
            "topic_name": None,
            "source": "local_fallback_bank",
            "content": "",
            "metadata": {"error": "missing_topic"},
        }
    ]


def test_build_sample_quality_matrix_summarizes_capture_and_explanation_gate() -> None:
    samples = build_local_sample_capture(topic_ids=[187, 188])
    matrix = build_sample_quality_matrix(samples)

    assert [row["topic_id"] for row in matrix] == [187, 188]
    assert all(row["explanation_status"] == "pass" for row in matrix)
    assert all(row["practice_status"] == "pass" for row in matrix)
    assert all(row["source"] == "local_fallback_bank" for row in matrix)
    assert all(row["issue_count"] == 0 for row in matrix)


def test_format_sample_quality_matrix_markdown_is_readable_table() -> None:
    samples = build_local_sample_capture(topic_ids=[187])
    markdown = format_sample_quality_matrix_markdown(build_sample_quality_matrix(samples))

    assert markdown.startswith("# Math Quality Sample Matrix")
    assert "| Topic ID | Source | Explanation | Practice | Issues |" in markdown
    assert "| 187 | local_fallback_bank | pass | pass | 0 |" in markdown
    assert "correct_answer" not in markdown
