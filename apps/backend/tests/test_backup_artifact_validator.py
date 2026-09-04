from __future__ import annotations

import gzip
import hashlib
from pathlib import Path

from scripts.backup_artifact_validator import validate_backup_artifact


def _write_backup(
    tmp_path: Path, sql: bytes = b"-- PostgreSQL database dump\nCREATE TABLE users (id integer);\n"
) -> tuple[Path, Path]:
    backup = tmp_path / "db-20260823T120000Z.sql.gz"
    with gzip.open(backup, "wb") as handle:
        handle.write(sql)
    checksum = tmp_path / "db-20260823T120000Z.sql.gz.sha256"
    checksum.write_text(f"{hashlib.sha256(backup.read_bytes()).hexdigest()}  {backup.name}\n", encoding="utf-8")
    return backup, checksum


def test_valid_backup_artifact_passes_read_only_preflight(tmp_path: Path) -> None:
    backup, checksum = _write_backup(tmp_path)

    result = validate_backup_artifact(backup, checksum_path=checksum)

    assert result["valid"] is True
    assert result["size_bytes"] > 0
    assert result["checksum_verified"] is True
    assert result["sql_signature_found"] is True
    assert result["blockers"] == []
    assert result["production_mutation"] is False


def test_corrupted_checksum_blocks_backup(tmp_path: Path) -> None:
    backup, checksum = _write_backup(tmp_path)
    checksum.write_text("0" * 64 + "  " + backup.name + "\n", encoding="utf-8")

    result = validate_backup_artifact(backup, checksum_path=checksum)

    assert result["valid"] is False
    assert "checksum_mismatch" in result["blockers"]


def test_non_gzip_or_non_sql_artifact_blocks_backup(tmp_path: Path) -> None:
    backup = tmp_path / "not-a-backup.sql.gz"
    backup.write_bytes(b"not gzip")

    result = validate_backup_artifact(backup)

    assert result["valid"] is False
    assert "invalid_gzip" in result["blockers"]
    assert "sql_signature_missing" in result["blockers"]


def test_missing_backup_is_reported_without_throwing(tmp_path: Path) -> None:
    result = validate_backup_artifact(tmp_path / "missing.sql.gz")

    assert result["valid"] is False
    assert "file_missing" in result["blockers"]
    assert result["production_mutation"] is False
