from __future__ import annotations

from scripts.algebra_exact_asset_fetch_probe import run_fetch_probe
from scripts.algebra_extracted_text_durable_import import (
    cleanup_extracted_text_import_target,
    read_extracted_text_audit_rows,
    run_extracted_text_import_target,
)
from scripts.algebra_local_readiness_snapshot import build_local_readiness_snapshot
from scripts.rag_metadata_audit import audit_rows, summarize_audit

_SOURCE_TEXT_BY_URL = {
    "https://im.kendallhunt.com/HS/students/1/2/index.html": "Alg1.2 Linear Equations, Inequalities, and Systems. This unit includes writing equations, equivalent equations, systems of linear equations, substitution, and elimination.",
}


def test_extracted_text_durable_import_writes_probe_rows_and_audits(tmp_path) -> None:
    db_path = tmp_path / "algebra-extracted.sqlite3"
    probe = run_fetch_probe(topic_ids=[37], source_text_by_url=_SOURCE_TEXT_BY_URL)

    result = run_extracted_text_import_target(db_path=db_path, probe_manifest=probe)

    assert result["mode"] == "extracted_text_durable_local_import_target"
    assert result["topic_count"] == 1
    assert result["material_count"] == 1
    assert result["chunk_count"] == 1
    assert result["metadata_audit"]["bad_rows"] == 0
    assert result["production_mutation"] is False
    assert result["promotion_allowed"] is False


def test_extracted_text_durable_rows_feed_readiness_snapshot_without_promotion(tmp_path) -> None:
    db_path = tmp_path / "algebra-extracted.sqlite3"
    probe = run_fetch_probe(topic_ids=[37], source_text_by_url=_SOURCE_TEXT_BY_URL)
    run_extracted_text_import_target(db_path=db_path, probe_manifest=probe)

    rows = read_extracted_text_audit_rows(db_path=db_path)
    summary = summarize_audit(audit_rows(rows, expected_subject_code="algebra"))
    snapshot = build_local_readiness_snapshot(db_path=db_path)

    assert summary["rows_checked"] == 1
    assert summary["bad_rows"] == 0
    assert snapshot["source_topic_count"] == 1
    assert snapshot["mvp_status"] == "preview"
    assert snapshot["promotion_allowed"] is False
    assert "source_coverage_incomplete" in snapshot["blockers"]


def test_extracted_text_durable_cleanup_removes_rows(tmp_path) -> None:
    db_path = tmp_path / "algebra-extracted.sqlite3"
    probe = run_fetch_probe(topic_ids=[37], source_text_by_url=_SOURCE_TEXT_BY_URL)
    run_extracted_text_import_target(db_path=db_path, probe_manifest=probe)

    cleanup = cleanup_extracted_text_import_target(db_path=db_path)

    assert cleanup == {"materials_deleted": 1, "chunks_deleted": 1, "material_count_after": 0, "chunk_count_after": 0}
