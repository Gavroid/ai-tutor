from __future__ import annotations

from scripts.algebra_local_import_dry_run import build_local_import_manifest
from scripts.rag_metadata_audit import audit_rows, summarize_audit


def test_local_import_dry_run_builds_materials_and_chunks_for_subset() -> None:
    manifest = build_local_import_manifest(topic_ids=[34, 37, 41])

    assert manifest["mode"] == "local_import_dry_run_only"
    assert manifest["production_mutation"] is False
    assert manifest["db_write"] is False
    assert manifest["rag_write"] is False
    assert manifest["topic_count"] == 3
    assert len(manifest["materials"]) == 3
    assert len(manifest["chunks"]) == 3
    assert {row["topic_id"] for row in manifest["materials"]} == {34, 37, 41}


def test_local_import_dry_run_chunks_pass_metadata_audit() -> None:
    manifest = build_local_import_manifest(topic_ids=[34, 37, 41])
    findings = audit_rows(manifest["audit_rows"], expected_subject_code="algebra")
    summary = summarize_audit(findings)

    assert summary["rows_checked"] == 3
    assert summary["bad_rows"] == 0
    assert summary["ok_rows"] == 3


def test_local_import_dry_run_keeps_preview_decision() -> None:
    manifest = build_local_import_manifest(topic_ids=[34, 37, 41])

    assert manifest["readiness_decision"] == "keep_preview_local_dry_run_only"
    assert manifest["promotion_allowed"] is False
