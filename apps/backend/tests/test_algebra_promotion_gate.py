from __future__ import annotations

from scripts.algebra_promotion_gate import evaluate_algebra_promotion


def test_promotion_gate_blocks_local_rehearsal_even_with_full_clean_audit() -> None:
    result = evaluate_algebra_promotion(
        route_topic_count=19,
        source_topic_count=19,
        practice_topic_count=19,
        metadata_bad_rows=0,
        import_mode="durable_local_sqlite_import_target",
        production_mutation=False,
        smoke_passed=False,
    )

    assert result["mvp_status"] == "preview"
    assert result["rag_ready"] is False
    assert result["promotion_allowed"] is False
    assert "import_not_production_or_staging" in result["blockers"]
    assert "smoke_not_passed" in result["blockers"]


def test_promotion_gate_allows_staging_or_production_only_when_all_gates_pass() -> None:
    result = evaluate_algebra_promotion(
        route_topic_count=19,
        source_topic_count=19,
        practice_topic_count=19,
        metadata_bad_rows=0,
        import_mode="staging_import",
        production_mutation=False,
        smoke_passed=True,
    )

    assert result["mvp_status"] == "mvp_ready_candidate"
    assert result["rag_ready"] is True
    assert result["promotion_allowed"] is True
    assert result["blockers"] == []


def test_promotion_gate_blocks_partial_coverage_and_bad_metadata() -> None:
    result = evaluate_algebra_promotion(
        route_topic_count=19,
        source_topic_count=18,
        practice_topic_count=19,
        metadata_bad_rows=2,
        import_mode="staging_import",
        production_mutation=False,
        smoke_passed=True,
    )

    assert result["mvp_status"] == "preview"
    assert result["rag_ready"] is False
    assert result["promotion_allowed"] is False
    assert "source_coverage_incomplete" in result["blockers"]
    assert "metadata_audit_failed" in result["blockers"]
