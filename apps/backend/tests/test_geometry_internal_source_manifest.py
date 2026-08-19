from __future__ import annotations

from scripts.geometry_internal_source_manifest import build_geometry_internal_source_manifest
from scripts.rag_metadata_audit import audit_rows, summarize_audit


def test_geometry_internal_source_manifest_covers_all_route_topics() -> None:
    manifest = build_geometry_internal_source_manifest()

    assert manifest["subject"] == "geometry"
    assert manifest["topic_count"] == 13
    assert len(manifest["materials"]) == 13
    assert len(manifest["chunks"]) == 13
    assert len(manifest["audit_rows"]) == 13
    assert manifest["production_mutation"] is False
    assert manifest["promotion_allowed"] is False


def test_geometry_internal_source_manifest_passes_metadata_audit() -> None:
    manifest = build_geometry_internal_source_manifest()
    summary = summarize_audit(audit_rows(manifest["audit_rows"], expected_subject_code="geometry"))

    assert summary["rows_checked"] == 13
    assert summary["bad_rows"] == 0
    assert summary["problems"] == {}


def test_geometry_internal_source_manifest_uses_owned_text_without_diagram_dependency() -> None:
    manifest = build_geometry_internal_source_manifest()

    for material in manifest["materials"]:
        assert material["source"] == "internal_geometry_notes"
        assert material["license"] == "Project-owned internal notes"
        assert "diagram" not in str(material["content"]).lower()
        assert "рисунок" not in str(material["content"]).lower()
        assert len(str(material["content"])) >= 240
