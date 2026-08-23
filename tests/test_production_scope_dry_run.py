from __future__ import annotations

from scripts.production_scope_dry_run import evaluate_subject_scope


def test_scope_dry_run_blocks_non_math_pilot_subjects() -> None:
    result = evaluate_subject_scope(
        [
            {"code": "math", "pilot_visible": True, "promotion_allowed": True},
            {"code": "algebra", "pilot_visible": True, "promotion_allowed": True},
        ],
        expected_pilot_codes={"math"},
    )

    assert result["decision"] == "blocked"
    assert result["can_release"] is False
    assert result["pilot_codes"] == ["algebra", "math"]
    assert "unexpected_pilot_subjects" in result["blockers"]


def test_scope_dry_run_allows_exact_math_only_response() -> None:
    result = evaluate_subject_scope(
        [{"code": "math", "pilot_visible": True, "promotion_allowed": True}],
        expected_pilot_codes={"math"},
    )

    assert result == {
        "decision": "aligned",
        "can_release": True,
        "expected_pilot_codes": ["math"],
        "pilot_codes": ["math"],
        "promotion_codes": ["math"],
        "blockers": [],
    }
