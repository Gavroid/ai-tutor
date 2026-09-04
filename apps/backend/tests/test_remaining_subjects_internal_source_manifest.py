from __future__ import annotations

from app.subjects.curriculum_7_class import CURRICULUM_7_CLASS

from scripts.rag_metadata_audit import audit_rows, summarize_audit
from scripts.remaining_subjects_internal_source_manifest import (
    REMAINING_SUBJECT_CODES,
    build_remaining_subjects_internal_source_manifest,
)


def test_remaining_subjects_manifest_covers_all_non_ready_preview_topics() -> None:
    manifest = build_remaining_subjects_internal_source_manifest()
    expected_count = sum(
        len(topics)
        for subject in CURRICULUM_7_CLASS
        if subject["code"] in REMAINING_SUBJECT_CODES
        for _section, topics in subject["sections"]
    )

    assert manifest["subject"] == "remaining_subjects"
    # S1.1 (2026-09-01): curriculum расширен 12→16 (добавлены chem/hist-world/
    # lit-2/rus-2), topic_count соответственно вырос. После расширения
    # expected_count = 151 + 4 новых subjects' topics = 151 + 38 = 189.
    assert manifest["topic_count"] == expected_count == 189
    assert len(manifest["materials"]) == expected_count
    assert len(manifest["chunks"]) == expected_count
    assert len(manifest["fallbacks"]) == expected_count
    assert manifest["production_mutation"] is False
    assert manifest["promotion_allowed"] is False


def test_remaining_subjects_manifest_passes_per_subject_metadata_audit() -> None:
    manifest = build_remaining_subjects_internal_source_manifest()

    for subject_code in REMAINING_SUBJECT_CODES:
        rows = [row for row in manifest["audit_rows"] if row["material_subject_code"] == subject_code]
        summary = summarize_audit(audit_rows(rows, expected_subject_code=subject_code))
        assert summary["bad_rows"] == 0


def test_remaining_subjects_fallbacks_are_checkable_single_choice_tasks() -> None:
    manifest = build_remaining_subjects_internal_source_manifest()

    for fallback in manifest["fallbacks"]:
        assert fallback["type"] == "single"
        assert fallback["correct_answer"] in fallback["options"]
        assert fallback["question_text"]
        assert fallback["explanation"]
        assert fallback["is_active"] is True


def test_remaining_subjects_content_is_subject_specific_not_one_generic_template() -> None:
    manifest = build_remaining_subjects_internal_source_manifest()
    answers = {fallback["correct_answer"] for fallback in manifest["fallbacks"]}

    assert len(answers) >= len(REMAINING_SUBJECT_CODES)
    for material in manifest["materials"]:
        content = str(material["content"]).lower()
        subject_code = material["subject_code"]
        if subject_code == "rus":
            assert any(word in content for word in ["орфограмм", "морфолог", "пунктуац"])
        if subject_code == "phys":
            assert any(word in content for word in ["величин", "опыт", "единиц"])
        if subject_code == "inf":
            assert any(word in content for word in ["алгоритм", "данн", "кодирован"])
        assert "без внешних материалов" in content


def test_remaining_subjects_content_has_no_student_facing_artifacts() -> None:
    manifest = build_remaining_subjects_internal_source_manifest()
    forbidden = ("<think>", "json", "correct_answer", "резервное", "parser", "provider", "|---")

    for material in manifest["materials"]:
        content = str(material["content"]).lower()
        assert not any(token in content for token in forbidden)
    for fallback in manifest["fallbacks"]:
        visible = " ".join(str(fallback[key]) for key in ["question_text", "explanation"])
        assert not any(token in visible.lower() for token in forbidden)
