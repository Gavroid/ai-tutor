from typing import Any, cast

from app.algebra_plan import ALGEBRA_TOPIC_PLAN
from scripts.algebra_source_import_dry_run import build_manifest, build_algebra_source_mappings


def test_algebra_source_dry_run_covers_every_route_topic_once():
    manifest = build_manifest()
    mapped_topic_ids = [row["topic_id"] for row in cast(list[dict[str, Any]], manifest["mappings"])]

    assert manifest["mode"] == "local_dry_run_manifest_only"
    assert manifest["production_mutation"] is False
    assert manifest["db_import"] is False
    assert manifest["rag_chunk_creation"] is False
    assert sorted(mapped_topic_ids) == sorted(row.topic_id for row in ALGEBRA_TOPIC_PLAN)
    assert len(mapped_topic_ids) == len(set(mapped_topic_ids)) == 19


def test_algebra_source_dry_run_uses_only_policy_approved_sources():
    rows = build_algebra_source_mappings()

    assert {row.source_key for row in rows} == {"im_first_edition", "wallace_algebra"}
    assert all(row.license in {"CC BY 4.0", "CC BY 3.0"} for row in rows)
    assert all(row.decision in {"approved_for_dry_run", "secondary_support"} for row in rows)
    assert all("CK-12" not in row.source_title for row in rows)
    assert all("Khan" not in row.source_title for row in rows)
    assert all("ND" not in row.license for row in rows)


def test_algebra_source_dry_run_manifest_has_import_metadata():
    rows = build_algebra_source_mappings()

    for row in rows:
        assert row.source_url.startswith(("https://im.kendallhunt.com/", "http://www.wallace.ccfaculty.org/"))
        assert row.source_section
        assert row.attribution
        assert row.import_notes


def test_algebra_source_dry_run_has_primary_and_secondary_coverage():
    manifest = build_manifest()

    source_counts = cast(dict[str, int], manifest["source_counts"])
    assert source_counts["im_first_edition"] >= 6
    assert source_counts["wallace_algebra"] >= 6
