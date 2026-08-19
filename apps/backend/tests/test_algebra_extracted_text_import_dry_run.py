from __future__ import annotations

from scripts.algebra_exact_asset_fetch_probe import run_fetch_probe
from scripts.algebra_extracted_text_import_dry_run import build_extracted_text_import_manifest
from scripts.rag_metadata_audit import audit_rows, summarize_audit


def test_extracted_text_import_manifest_uses_passed_probe_rows() -> None:
    probe = run_fetch_probe(
        topic_ids=[37],
        source_text_by_url={
            "https://im.kendallhunt.com/HS/students/1/2/index.html": "Alg1.2 Linear Equations, Inequalities, and Systems. This unit includes writing equations, equivalent equations, and systems of linear equations by substitution and elimination.",
        },
    )
    manifest = build_extracted_text_import_manifest(probe_manifest=probe)

    assert manifest["mode"] == "extracted_text_import_dry_run_only"
    assert manifest["topic_count"] == 1
    assert len(manifest["materials"]) == 1
    assert len(manifest["chunks"]) == 1
    assert manifest["materials"][0]["content"].startswith("Alg1.2 Linear Equations")
    assert manifest["production_mutation"] is False
    assert manifest["promotion_allowed"] is False


def test_extracted_text_import_manifest_ignores_failed_probe_rows() -> None:
    probe = {
        "rows": [
            {"topic_id": 37, "status": "fail", "asset_url": "x", "source_section": "Unit 2", "source_key": "im_first_edition", "text_excerpt": ""}
        ]
    }

    manifest = build_extracted_text_import_manifest(probe_manifest=probe)

    assert manifest["topic_count"] == 0
    assert manifest["materials"] == []
    assert manifest["chunks"] == []


def test_extracted_text_import_manifest_passes_metadata_audit() -> None:
    probe = run_fetch_probe(
        topic_ids=[37],
        source_text_by_url={
            "https://im.kendallhunt.com/HS/students/1/2/index.html": "Alg1.2 Linear Equations, Inequalities, and Systems. This unit includes writing equations, equivalent equations, and systems of linear equations by substitution and elimination.",
        },
    )
    manifest = build_extracted_text_import_manifest(probe_manifest=probe)
    summary = summarize_audit(audit_rows(manifest["audit_rows"], expected_subject_code="algebra"))

    assert summary["rows_checked"] == 1
    assert summary["bad_rows"] == 0
