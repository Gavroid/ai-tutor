from __future__ import annotations

from scripts.algebra_import_execution_plan import evaluate_algebra_import_execution_plan


def test_import_execution_plan_blocks_local_target_even_with_clean_rows() -> None:
    result = evaluate_algebra_import_execution_plan(
        target_env="local",
        route_topic_count=19,
        source_topic_count=19,
        practice_topic_count=19,
        metadata_bad_rows=0,
        backup_verified=True,
        offsite_verified=True,
        target_tree_clean=True,
        branch_aligned=True,
        head_aligned=True,
        smoke_plan_defined=True,
    )

    assert result["decision"] == "block_import"
    assert result["import_allowed"] is False
    assert "target_not_staging_or_production" in result["blockers"]


def test_import_execution_plan_blocks_production_without_backup_offsite_and_smoke_plan() -> None:
    result = evaluate_algebra_import_execution_plan(
        target_env="production",
        route_topic_count=19,
        source_topic_count=19,
        practice_topic_count=19,
        metadata_bad_rows=0,
        backup_verified=False,
        offsite_verified=False,
        target_tree_clean=True,
        branch_aligned=True,
        head_aligned=True,
        smoke_plan_defined=False,
    )

    assert result["decision"] == "block_import"
    assert result["import_allowed"] is False
    assert "backup_not_verified" in result["blockers"]
    assert "offsite_not_verified" in result["blockers"]
    assert "smoke_plan_missing" in result["blockers"]


def test_import_execution_plan_blocks_dirty_or_misaligned_target() -> None:
    result = evaluate_algebra_import_execution_plan(
        target_env="production",
        route_topic_count=19,
        source_topic_count=19,
        practice_topic_count=19,
        metadata_bad_rows=0,
        backup_verified=True,
        offsite_verified=True,
        target_tree_clean=False,
        branch_aligned=False,
        head_aligned=False,
        smoke_plan_defined=True,
    )

    assert result["decision"] == "block_import"
    assert result["import_allowed"] is False
    assert "target_tree_dirty" in result["blockers"]
    assert "target_branch_mismatch" in result["blockers"]
    assert "target_head_mismatch" in result["blockers"]


def test_import_execution_plan_allows_staging_plan_when_all_gates_pass() -> None:
    result = evaluate_algebra_import_execution_plan(
        target_env="staging",
        route_topic_count=19,
        source_topic_count=19,
        practice_topic_count=19,
        metadata_bad_rows=0,
        backup_verified=True,
        offsite_verified=True,
        target_tree_clean=True,
        branch_aligned=True,
        head_aligned=True,
        smoke_plan_defined=True,
    )

    assert result["decision"] == "ready_for_staging_import_plan"
    assert result["import_allowed"] is True
    assert result["promotion_allowed"] is False
    assert result["blockers"] == []


def test_import_execution_plan_blocks_incomplete_coverage_and_bad_metadata() -> None:
    result = evaluate_algebra_import_execution_plan(
        target_env="staging",
        route_topic_count=19,
        source_topic_count=18,
        practice_topic_count=19,
        metadata_bad_rows=1,
        backup_verified=True,
        offsite_verified=True,
        target_tree_clean=True,
        branch_aligned=True,
        head_aligned=True,
        smoke_plan_defined=True,
    )

    assert result["decision"] == "block_import"
    assert result["import_allowed"] is False
    assert "source_coverage_incomplete" in result["blockers"]
    assert "metadata_audit_failed" in result["blockers"]
