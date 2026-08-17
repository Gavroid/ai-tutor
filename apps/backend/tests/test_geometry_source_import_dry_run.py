from typing import Any, cast

from app.geometry_plan import GEOMETRY_TOPIC_PLAN
from scripts.geometry_source_import_dry_run import build_manifest, build_geometry_source_mappings


def test_geometry_source_dry_run_covers_every_route_topic_once():
    manifest = build_manifest()
    mapped_topic_ids = [row["topic_id"] for row in cast(list[dict[str, Any]], manifest["mappings"])]

    assert manifest["mode"] == "local_dry_run_manifest_only"
    assert manifest["production_mutation"] is False
    assert manifest["db_import"] is False
    assert manifest["rag_chunk_creation"] is False
    assert manifest["requires_diagram_review"] is True
    assert sorted(mapped_topic_ids) == sorted(row.topic_id for row in GEOMETRY_TOPIC_PLAN)
    assert len(mapped_topic_ids) == len(set(mapped_topic_ids)) == 13


def test_geometry_source_dry_run_uses_only_policy_screened_sources():
    rows = build_geometry_source_mappings()

    assert {row.source_key for row in rows} == {"im_geometry", "euclid_redux"}
    assert all(row.license in {"CC BY 4.0", "CC BY-SA"} for row in rows)
    assert all(row.decision in {"approved_for_dry_run", "conditional_secondary"} for row in rows)
    assert all("CK-12" not in row.source_title for row in rows)
    assert all("ND" not in row.license for row in rows)


def test_geometry_source_dry_run_requires_diagram_review_for_every_topic():
    rows = build_geometry_source_mappings()

    assert all(row.diagram_review_required is True for row in rows)
    assert all(row.source_section for row in rows)
    assert all(row.attribution for row in rows)
    assert all(row.import_notes for row in rows)


def test_geometry_source_dry_run_prefers_im_geometry_primary_source():
    manifest = build_manifest()
    source_counts = cast(dict[str, int], manifest["source_counts"])

    assert source_counts["im_geometry"] >= 9
    assert source_counts["euclid_redux"] <= 4
