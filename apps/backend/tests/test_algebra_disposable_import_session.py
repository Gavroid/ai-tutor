from __future__ import annotations

from scripts.algebra_disposable_import_session import run_disposable_import_rehearsal


def test_disposable_import_rehearsal_writes_then_rolls_back_rows() -> None:
    result = run_disposable_import_rehearsal(topic_ids=[34, 37, 41])

    assert result["mode"] == "disposable_sqlite_import_rehearsal"
    assert result["topic_count"] == 3
    assert result["material_count_before_rollback"] == 3
    assert result["chunk_count_before_rollback"] == 3
    assert result["material_count_after_rollback"] == 0
    assert result["chunk_count_after_rollback"] == 0
    assert result["metadata_audit"]["bad_rows"] == 0
    assert result["production_mutation"] is False
    assert result["promotion_allowed"] is False


def test_disposable_import_rehearsal_can_cover_all_19_topics() -> None:
    result = run_disposable_import_rehearsal()

    assert result["topic_count"] == 19
    assert result["material_count_before_rollback"] == 19
    assert result["chunk_count_before_rollback"] == 19
    assert result["material_count_after_rollback"] == 0
    assert result["chunk_count_after_rollback"] == 0
    assert result["metadata_audit"]["rows_checked"] == 19
    assert result["metadata_audit"]["bad_rows"] == 0
