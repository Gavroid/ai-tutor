from __future__ import annotations

from scripts.algebra_exact_asset_fetch_probe import (
    build_probe_plan,
    evaluate_extracted_text,
    summarize_probe_rows,
)


def test_build_probe_plan_selects_exact_asset_topics() -> None:
    rows = build_probe_plan(topic_ids=[34, 37])

    assert [row["topic_id"] for row in rows] == [34, 37]
    assert rows[0]["asset_url"].endswith("0.3%20Order%20of%20Operations.pdf")
    assert rows[1]["asset_url"].endswith("/1/2/index.html")


def test_evaluate_extracted_text_passes_with_required_terms() -> None:
    result = evaluate_extracted_text(
        topic_id=34,
        asset_url="http://www.wallace.ccfaculty.org/book/0.3%20Order%20of%20Operations.pdf",
        source_section="0.3 Order of Operations",
        text="Order of Operations tells students how to evaluate arithmetic expressions step by step before comparing answers in a practice problem.",
    )

    assert result["status"] == "pass"
    assert result["missing_terms"] == []


def test_evaluate_extracted_text_fails_closed_when_too_short_or_missing_terms() -> None:
    result = evaluate_extracted_text(
        topic_id=41,
        asset_url="http://www.wallace.ccfaculty.org/book/5.1%20Exponents.pdf",
        source_section="5.1 Exponent Properties",
        text="linear equations only",
    )

    assert result["status"] == "fail"
    assert "text_too_short" in result["problems"]
    assert "Exponent" in result["missing_terms"]


def test_summarize_probe_rows_counts_pass_fail() -> None:
    summary = summarize_probe_rows(
        [
            {"status": "pass", "source_key": "wallace_algebra"},
            {"status": "fail", "source_key": "im_first_edition"},
        ]
    )

    assert summary == {
        "asset_count": 2,
        "pass_count": 1,
        "fail_count": 1,
        "source_counts": {"im_first_edition": 1, "wallace_algebra": 1},
    }


def test_extract_text_from_partial_html_keeps_unit_terms(tmp_path) -> None:
    from scripts.algebra_exact_asset_fetch_probe import _extract_text

    path = tmp_path / "partial.html"
    path.write_text(
        "<html><body><h1>Unit 2</h1><p>Linear Equations, Inequalities, and Systems</p></body></html>", encoding="utf-8"
    )

    extracted = _extract_text(path)

    assert "Unit 2" in extracted
    assert "Linear Equations" in extracted
    assert "Systems" in extracted


def test_run_fetch_probe_can_use_source_text_override_for_flaky_html() -> None:
    from scripts.algebra_exact_asset_fetch_probe import run_fetch_probe

    result = run_fetch_probe(
        topic_ids=[37],
        source_text_by_url={
            "https://im.kendallhunt.com/HS/students/1/2/index.html": "Alg1.2 Linear Equations, Inequalities, and Systems Unit 2. This unit covers writing and modeling equations, manipulating equations, and systems of linear equations.",
        },
    )

    assert result["summary"]["asset_count"] == 1
    assert result["summary"]["pass_count"] == 1
    assert result["summary"]["fail_count"] == 0
    assert result["rows"][0]["extraction_source"] == "provided_text_override"
