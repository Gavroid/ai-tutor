from __future__ import annotations

from scripts.algebra_durable_local_import_target import run_durable_import_target
from scripts.algebra_local_readiness_snapshot import build_local_readiness_snapshot


def test_local_readiness_snapshot_counts_durable_import_without_promotion(tmp_path) -> None:
    db_path = tmp_path / "algebra.sqlite3"
    run_durable_import_target(db_path=db_path)

    snapshot = build_local_readiness_snapshot(db_path=db_path, smoke_passed=False)

    assert snapshot["subject"] == "algebra"
    assert snapshot["route_topic_count"] == 19
    assert snapshot["source_topic_count"] == 19
    assert snapshot["practice_topic_count"] == 19
    assert snapshot["metadata_bad_rows"] == 0
    assert snapshot["mvp_status"] == "preview"
    assert snapshot["rag_ready"] is False
    assert snapshot["promotion_allowed"] is False
    assert "import_not_production_or_staging" in snapshot["blockers"]


def test_local_readiness_snapshot_missing_import_remains_preview(tmp_path) -> None:
    db_path = tmp_path / "empty.sqlite3"

    snapshot = build_local_readiness_snapshot(db_path=db_path, smoke_passed=False)

    assert snapshot["source_topic_count"] == 0
    assert snapshot["metadata_bad_rows"] == 0
    assert snapshot["mvp_status"] == "preview"
    assert snapshot["promotion_allowed"] is False
    assert "source_coverage_incomplete" in snapshot["blockers"]
