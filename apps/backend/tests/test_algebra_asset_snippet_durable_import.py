from __future__ import annotations

from scripts.algebra_asset_snippet_durable_import import (
    cleanup_asset_snippet_import_target,
    read_asset_snippet_audit_rows,
    run_asset_snippet_import_target,
)
from scripts.algebra_local_readiness_snapshot import build_local_readiness_snapshot
from scripts.rag_metadata_audit import audit_rows, summarize_audit


def test_asset_snippet_durable_import_writes_rows_and_audits(tmp_path) -> None:
    db_path = tmp_path / "asset-snippet.sqlite3"

    result = run_asset_snippet_import_target(db_path=db_path)

    assert result["mode"] == "asset_snippet_durable_local_import_target"
    assert result["topic_count"] == 19
    assert result["material_count"] == 19
    assert result["chunk_count"] == 19
    assert result["metadata_audit"]["bad_rows"] == 0
    assert result["promotion_allowed"] is False


def test_asset_snippet_durable_rows_feed_readiness_snapshot(tmp_path) -> None:
    db_path = tmp_path / "asset-snippet.sqlite3"
    run_asset_snippet_import_target(db_path=db_path)

    rows = read_asset_snippet_audit_rows(db_path=db_path)
    summary = summarize_audit(audit_rows(rows, expected_subject_code="algebra"))
    snapshot = build_local_readiness_snapshot(db_path=db_path)

    assert summary["rows_checked"] == 19
    assert summary["bad_rows"] == 0
    assert snapshot["source_topic_count"] == 19
    assert snapshot["mvp_status"] == "preview"
    assert snapshot["promotion_allowed"] is False


def test_asset_snippet_durable_cleanup_removes_rows(tmp_path) -> None:
    db_path = tmp_path / "asset-snippet.sqlite3"
    run_asset_snippet_import_target(db_path=db_path)

    cleanup = cleanup_asset_snippet_import_target(db_path=db_path)

    assert cleanup == {"materials_deleted": 19, "chunks_deleted": 19, "material_count_after": 0, "chunk_count_after": 0}
