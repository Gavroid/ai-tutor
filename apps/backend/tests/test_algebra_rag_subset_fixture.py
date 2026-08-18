from __future__ import annotations

from scripts.algebra_rag_subset_fixture import build_subset_fixture, build_subset_manifest
from scripts.rag_metadata_audit import audit_rows, summarize_audit


def test_algebra_subset_fixture_builds_topic_scoped_rows_without_mutation() -> None:
    rows = build_subset_fixture(topic_ids=[34, 37, 41])

    assert [row["material_topic_id"] for row in rows] == [34, 37, 41]
    assert all(row["material_subject_code"] == "algebra" for row in rows)
    assert all(row["production_mutation"] is False for row in rows)
    assert all(row["db_import"] is False for row in rows)
    assert all(row["rag_chunk_creation"] is False for row in rows)


def test_algebra_subset_fixture_passes_rag_metadata_audit() -> None:
    rows = build_subset_fixture(topic_ids=[34, 37, 41])

    findings = audit_rows(rows, expected_subject_code="algebra")
    summary = summarize_audit(findings)

    assert summary["rows_checked"] == 3
    assert summary["ok_rows"] == 3
    assert summary["bad_rows"] == 0


def test_algebra_subset_manifest_keeps_algebra_preview_not_ready() -> None:
    manifest = build_subset_manifest(topic_ids=[34, 37, 41])

    assert manifest["mode"] == "local_subset_fixture_only"
    assert manifest["subject"] == "algebra"
    assert manifest["topic_count"] == 3
    assert manifest["production_mutation"] is False
    assert manifest["db_import"] is False
    assert manifest["rag_chunk_creation"] is False
    assert manifest["readiness_decision"] == "keep_preview_until_real_import_and_audit"
