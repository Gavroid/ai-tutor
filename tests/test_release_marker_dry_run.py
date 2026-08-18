from __future__ import annotations

from scripts.release_marker_dry_run import evaluate_marker_state


def test_marker_advancement_blocked_when_production_tree_dirty() -> None:
    result = evaluate_marker_state(
        local_head="b7ffe89",
        production_marker="6e698a0",
        production_head="cb99f2b",
        production_branch="master",
        production_dirty_paths=["apps/backend/app/ai/service.py"],
        intended_branch="mvp-rescue",
    )

    assert result["decision"] == "blocked"
    assert result["can_advance_marker"] is False
    assert "production_tree_dirty" in result["blockers"]
    assert "production_branch_mismatch" in result["blockers"]
    assert "production_head_mismatch" in result["blockers"]
    assert result["recommended_mode"] == "targeted_deploy"


def test_marker_advancement_allowed_when_clean_and_aligned() -> None:
    result = evaluate_marker_state(
        local_head="abc1234",
        production_marker="old0000",
        production_head="abc1234",
        production_branch="mvp-rescue",
        production_dirty_paths=[],
        intended_branch="mvp-rescue",
    )

    assert result["decision"] == "ready_for_marker_advance"
    assert result["can_advance_marker"] is True
    assert result["blockers"] == []
    assert result["target_marker"] == "abc1234"


def test_marker_advancement_noop_when_marker_already_current() -> None:
    result = evaluate_marker_state(
        local_head="abc1234",
        production_marker="abc1234",
        production_head="abc1234",
        production_branch="mvp-rescue",
        production_dirty_paths=[],
        intended_branch="mvp-rescue",
    )

    assert result["decision"] == "already_current"
    assert result["can_advance_marker"] is False
    assert result["blockers"] == []
