from __future__ import annotations

from scripts.geometry_internal_source_manifest import build_geometry_internal_source_manifest
from scripts.geometry_production_import import build_geometry_import_plan, execute_geometry_import_plan


def test_build_geometry_import_plan_uses_internal_source_rows() -> None:
    manifest = build_geometry_internal_source_manifest()

    plan = build_geometry_import_plan(manifest=manifest, target_env="staging", dry_run=True)

    assert plan["subject"] == "geometry"
    assert plan["target_env"] == "staging"
    assert plan["dry_run"] is True
    assert plan["material_count"] == 13
    assert plan["chunk_count"] == 13
    assert plan["metadata_audit"]["bad_rows"] == 0
    assert plan["production_mutation"] is False
    assert plan["promotion_allowed"] is False


def test_execute_geometry_import_plan_dry_run_writes_no_rows(tmp_path) -> None:
    manifest = build_geometry_internal_source_manifest()

    result = execute_geometry_import_plan(
        manifest=manifest,
        target_env="staging",
        db_url=f"sqlite+pysqlite:///{tmp_path / 'target.sqlite3'}",
        dry_run=True,
    )

    assert result["decision"] == "dry_run_only"
    assert result["rows_written"] == 0
    assert result["production_mutation"] is False


def test_execute_geometry_import_plan_blocks_production_without_explicit_flag(tmp_path) -> None:
    result = execute_geometry_import_plan(
        manifest=build_geometry_internal_source_manifest(),
        target_env="production",
        db_url=f"sqlite+pysqlite:///{tmp_path / 'target.sqlite3'}",
        dry_run=False,
        allow_production=False,
    )

    assert result["decision"] == "block_import"
    assert result["rows_written"] == 0
    assert "allow_production_not_set" in result["blockers"]


def test_execute_geometry_import_plan_writes_to_staging_sqlite(tmp_path) -> None:
    manifest = build_geometry_internal_source_manifest()

    result = execute_geometry_import_plan(
        manifest=manifest,
        target_env="staging",
        db_url=f"sqlite+pysqlite:///{tmp_path / 'target.sqlite3'}",
        dry_run=False,
    )

    assert result["decision"] == "staging_import_executed"
    assert result["rows_written"] == 26
    assert result["material_count"] == 13
    assert result["chunk_count"] == 13
    assert result["production_mutation"] is False
    assert result["promotion_allowed"] is False
