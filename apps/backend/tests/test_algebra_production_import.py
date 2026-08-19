from __future__ import annotations

from scripts.algebra_production_import import build_algebra_import_plan, execute_algebra_import_plan


def test_build_algebra_import_plan_uses_extracted_text_rows() -> None:
    manifest = {
        "materials": [
            {
                "id": 10001,
                "topic_id": 37,
                "subject_code": "algebra",
                "title": "Algebra source",
                "content": "Linear equations extracted text",
                "source": "im_first_edition",
                "source_url": "https://example.test/unit2",
                "source_section": "Unit 2",
                "license": "CC BY 4.0",
                "attribution": "Example",
                "status": "draft_extracted_text_local_only",
            }
        ],
        "chunks": [
            {
                "id": "algebra-extracted-37-1",
                "material_id": 10001,
                "hash": "hash37",
                "text": "Linear equations extracted text",
                "embedding_json": "[]",
                "metadata_json": '{"subject_code":"algebra","topic_id":37,"topic_name":"Linear equations","source_title":"Algebra source","source_section":"Unit 2","license":"CC BY 4.0","attribution":"Example"}',
            }
        ],
        "audit_rows": [
            {
                "chunk_id": "algebra-extracted-37-1",
                "material_id": 10001,
                "material_title": "Algebra source",
                "material_topic_id": 37,
                "material_subject_code": "algebra",
                "metadata_json": '{"subject_code":"algebra","topic_id":37,"topic_name":"Linear equations","source_title":"Algebra source","source_section":"Unit 2","license":"CC BY 4.0","attribution":"Example"}',
            }
        ],
    }

    plan = build_algebra_import_plan(manifest=manifest, target_env="staging", dry_run=True)

    assert plan["target_env"] == "staging"
    assert plan["dry_run"] is True
    assert plan["material_count"] == 1
    assert plan["chunk_count"] == 1
    assert plan["metadata_audit"]["bad_rows"] == 0
    assert plan["production_mutation"] is False
    assert plan["promotion_allowed"] is False


def test_execute_algebra_import_plan_dry_run_does_not_write_rows(tmp_path) -> None:
    manifest = {
        "materials": [
            {
                "id": 10001,
                "topic_id": 37,
                "subject_code": "algebra",
                "title": "Algebra source",
                "content": "Linear equations extracted text",
                "source": "im_first_edition",
                "source_url": "https://example.test/unit2",
                "source_section": "Unit 2",
                "license": "CC BY 4.0",
                "attribution": "Example",
                "status": "draft_extracted_text_local_only",
            }
        ],
        "chunks": [],
        "audit_rows": [],
    }

    result = execute_algebra_import_plan(manifest=manifest, target_env="staging", db_url=f"sqlite+pysqlite:///{tmp_path / 'target.sqlite3'}", dry_run=True)

    assert result["decision"] == "dry_run_only"
    assert result["rows_written"] == 0
    assert result["production_mutation"] is False


def test_execute_algebra_import_plan_blocks_production_without_explicit_flag(tmp_path) -> None:
    result = execute_algebra_import_plan(
        manifest={"materials": [], "chunks": [], "audit_rows": []},
        target_env="production",
        db_url=f"sqlite+pysqlite:///{tmp_path / 'target.sqlite3'}",
        dry_run=False,
        allow_production=False,
    )

    assert result["decision"] == "block_import"
    assert result["rows_written"] == 0
    assert "allow_production_not_set" in result["blockers"]


def test_execute_algebra_import_plan_writes_to_staging_sqlite(tmp_path) -> None:
    manifest = {
        "materials": [
            {
                "id": 10001,
                "topic_id": 37,
                "subject_code": "algebra",
                "title": "Algebra source",
                "content": "Linear equations extracted text",
                "source": "im_first_edition",
                "source_url": "https://example.test/unit2",
                "source_section": "Unit 2",
                "license": "CC BY 4.0",
                "attribution": "Example",
                "status": "draft_extracted_text_local_only",
            }
        ],
        "chunks": [
            {
                "id": "algebra-extracted-37-1",
                "material_id": 10001,
                "hash": "hash37",
                "text": "Linear equations extracted text",
                "embedding_json": "[]",
                "metadata_json": '{"subject_code":"algebra","topic_id":37,"topic_name":"Linear equations","source_title":"Algebra source","source_section":"Unit 2","license":"CC BY 4.0","attribution":"Example"}',
            }
        ],
        "audit_rows": [],
    }

    result = execute_algebra_import_plan(
        manifest=manifest,
        target_env="staging",
        db_url=f"sqlite+pysqlite:///{tmp_path / 'target.sqlite3'}",
        dry_run=False,
    )

    assert result["decision"] == "staging_import_executed"
    assert result["rows_written"] == 2
    assert result["material_count"] == 1
    assert result["chunk_count"] == 1
    assert result["production_mutation"] is False
    assert result["promotion_allowed"] is False


def test_execute_algebra_import_plan_reports_only_target_rows_when_db_has_existing_data(tmp_path) -> None:
    db_url = f"sqlite+pysqlite:///{tmp_path / 'target.sqlite3'}"
    existing = {
        "materials": [
            {
                "id": 20001,
                "topic_id": 1,
                "subject_code": "math",
                "title": "Existing math",
                "content": "Existing text",
                "source": "math",
                "source_url": "https://example.test/math",
                "source_section": "Math",
                "license": "CC BY 4.0",
                "attribution": "Example",
                "status": "draft",
            }
        ],
        "chunks": [],
        "audit_rows": [],
    }
    execute_algebra_import_plan(manifest=existing, target_env="staging", db_url=db_url, dry_run=False)

    manifest = {
        "materials": [
            {
                "id": 10001,
                "topic_id": 37,
                "subject_code": "algebra",
                "title": "Algebra source",
                "content": "Linear equations extracted text",
                "source": "im_first_edition",
                "source_url": "https://example.test/unit2",
                "source_section": "Unit 2",
                "license": "CC BY 4.0",
                "attribution": "Example",
                "status": "draft_extracted_text_local_only",
            }
        ],
        "chunks": [
            {
                "id": "algebra-extracted-37-1",
                "material_id": 10001,
                "hash": "hash37",
                "text": "Linear equations extracted text",
                "embedding_json": "[]",
                "metadata_json": '{"subject_code":"algebra","topic_id":37,"topic_name":"Linear equations","source_title":"Algebra source","source_section":"Unit 2","license":"CC BY 4.0","attribution":"Example"}',
            }
        ],
        "audit_rows": [],
    }

    result = execute_algebra_import_plan(manifest=manifest, target_env="staging", db_url=db_url, dry_run=False)

    assert result["material_count"] == 1
    assert result["chunk_count"] == 1
    assert result["rows_written"] == 2
