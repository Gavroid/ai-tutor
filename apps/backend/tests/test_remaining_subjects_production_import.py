from __future__ import annotations

from scripts.remaining_subjects_internal_source_manifest import build_remaining_subjects_internal_source_manifest
from scripts.remaining_subjects_production_import import execute_remaining_subjects_import_plan


def test_remaining_subjects_import_dry_run_writes_no_rows(tmp_path) -> None:
    result = execute_remaining_subjects_import_plan(
        manifest=build_remaining_subjects_internal_source_manifest(),
        target_env="staging",
        db_url=f"sqlite+pysqlite:///{tmp_path / 'target.sqlite3'}",
        dry_run=True,
    )

    assert result["decision"] == "dry_run_only"
    assert result["rows_written"] == 0
    assert result["production_mutation"] is False


def test_remaining_subjects_import_blocks_production_without_explicit_flag(tmp_path) -> None:
    result = execute_remaining_subjects_import_plan(
        manifest=build_remaining_subjects_internal_source_manifest(),
        target_env="production",
        db_url=f"sqlite+pysqlite:///{tmp_path / 'target.sqlite3'}",
        dry_run=False,
        allow_production=False,
    )

    assert result["decision"] == "block_import"
    assert result["rows_written"] == 0
    assert "allow_production_not_set" in result["blockers"]


def test_remaining_subjects_import_writes_to_staging_sqlite(tmp_path) -> None:
    result = execute_remaining_subjects_import_plan(
        manifest=build_remaining_subjects_internal_source_manifest(),
        target_env="staging",
        db_url=f"sqlite+pysqlite:///{tmp_path / 'target.sqlite3'}",
        dry_run=False,
    )

    assert result["decision"] == "staging_import_executed"
    # S1.1 (2026-09-01): curriculum 12→16 (добавлены chem/hist-world/lit-2/
    # rus-2). Material/chunk count вырос с 151 до 189. rows_written = 189*2 = 378.
    assert result["material_count"] == 189
    assert result["chunk_count"] == 189
    assert result["rows_written"] == 378
    assert result["production_mutation"] is False
