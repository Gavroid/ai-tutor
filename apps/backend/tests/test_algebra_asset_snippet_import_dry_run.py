from __future__ import annotations

from scripts.algebra_asset_snippet_import_dry_run import build_asset_snippet_import_manifest
from scripts.rag_metadata_audit import audit_rows, summarize_audit


def test_asset_snippet_import_manifest_builds_rows_from_exact_snippets() -> None:
    manifest = build_asset_snippet_import_manifest()

    assert manifest["mode"] == "asset_snippet_import_dry_run_only"
    assert manifest["topic_count"] == 19
    assert len(manifest["materials"]) == 19
    assert len(manifest["chunks"]) == 19
    assert all(row["source_url"] for row in manifest["materials"])
    assert all(row["source_section"] for row in manifest["materials"])
    assert all(chunk["text"] for chunk in manifest["chunks"])
    assert manifest["production_mutation"] is False
    assert manifest["db_write"] is False
    assert manifest["rag_write"] is False


def test_asset_snippet_import_manifest_passes_rag_metadata_audit() -> None:
    manifest = build_asset_snippet_import_manifest()
    summary = summarize_audit(audit_rows(manifest["audit_rows"], expected_subject_code="algebra"))

    assert summary["rows_checked"] == 19
    assert summary["ok_rows"] == 19
    assert summary["bad_rows"] == 0


def test_asset_snippet_import_manifest_keeps_preview_decision() -> None:
    manifest = build_asset_snippet_import_manifest()

    assert manifest["promotion_allowed"] is False
    assert manifest["readiness_decision"] == "keep_preview_asset_snippet_dry_run_only"
