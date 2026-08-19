from __future__ import annotations

from scripts.algebra_durable_local_import_target import (
    cleanup_durable_import_target,
    read_durable_audit_rows,
    run_durable_import_target,
)
from scripts.rag_metadata_audit import audit_rows, summarize_audit


def test_durable_local_import_commits_rows_to_file_db(tmp_path) -> None:
    db_path = tmp_path / "algebra-import.sqlite3"

    result = run_durable_import_target(db_path=db_path, topic_ids=[34, 37, 41])

    assert result["mode"] == "durable_local_sqlite_import_target"
    assert result["db_path"] == str(db_path)
    assert result["topic_count"] == 3
    assert result["material_count"] == 3
    assert result["chunk_count"] == 3
    assert result["metadata_audit"]["bad_rows"] == 0
    assert result["production_mutation"] is False
    assert result["promotion_allowed"] is False
    assert db_path.exists()


def test_durable_local_import_rows_read_back_pass_metadata_audit(tmp_path) -> None:
    db_path = tmp_path / "algebra-import.sqlite3"
    run_durable_import_target(db_path=db_path)

    rows = read_durable_audit_rows(db_path=db_path)
    summary = summarize_audit(audit_rows(rows, expected_subject_code="algebra"))

    assert summary["rows_checked"] == 19
    assert summary["bad_rows"] == 0


def test_durable_local_import_cleanup_removes_rows_but_keeps_file(tmp_path) -> None:
    db_path = tmp_path / "algebra-import.sqlite3"
    run_durable_import_target(db_path=db_path, topic_ids=[34, 37, 41])

    cleanup = cleanup_durable_import_target(db_path=db_path)

    assert cleanup == {"materials_deleted": 3, "chunks_deleted": 3, "material_count_after": 0, "chunk_count_after": 0}
    assert db_path.exists()
