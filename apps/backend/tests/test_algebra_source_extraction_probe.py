from __future__ import annotations

from scripts.algebra_source_extraction_probe import (
    build_probe_rows,
    evaluate_probe_text,
    summarize_probe_rows,
)


def test_evaluate_probe_text_accepts_section_and_keywords() -> None:
    result = evaluate_probe_text(
        source_key="im_first_edition",
        source_section="Unit 2 Linear Equations, Inequalities, and Systems",
        text="Unit 2 Linear Equations, Inequalities, and Systems has lessons about equations, graphs, and systems.",
        required_terms=["Unit 2", "equations", "systems"],
    )

    assert result["status"] == "pass"
    assert result["matched_terms"] == ["Unit 2", "equations", "systems"]
    assert result["missing_terms"] == []


def test_evaluate_probe_text_fails_closed_on_missing_terms() -> None:
    result = evaluate_probe_text(
        source_key="wallace_algebra",
        source_section="5.1 Exponent Properties",
        text="This page discusses linear equations only.",
        required_terms=["Exponent", "Properties"],
    )

    assert result["status"] == "fail"
    assert result["missing_terms"] == ["Exponent", "Properties"]


def test_build_probe_rows_uses_manifest_and_records_no_mutation_flags() -> None:
    rows = build_probe_rows(
        fetched_text_by_source={
            "im_first_edition": "Unit 2 Linear Equations, Inequalities, and Systems Unit 4 Functions",
            "wallace_algebra": "0.3 Order of Operations 5.1 Exponent Properties 5.4 Introduction to Polynomials",
        },
        topic_ids=[34, 37, 38, 41],
    )

    assert [row["topic_id"] for row in rows] == [34, 37, 38, 41]
    assert all(row["production_mutation"] is False for row in rows)
    assert all(row["db_import"] is False for row in rows)
    assert all(row["rag_chunk_creation"] is False for row in rows)


def test_summarize_probe_rows_counts_pass_fail_and_sources() -> None:
    rows = [
        {"status": "pass", "source_key": "im_first_edition"},
        {"status": "fail", "source_key": "wallace_algebra"},
        {"status": "pass", "source_key": "im_first_edition"},
    ]

    summary = summarize_probe_rows(rows)

    assert summary == {
        "topic_count": 3,
        "pass_count": 2,
        "fail_count": 1,
        "source_counts": {"im_first_edition": 2, "wallace_algebra": 1},
    }
