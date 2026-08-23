"""Read-only preflight validation for PostgreSQL backup artifacts.

This module never connects to production, SMB, Docker, or a database. It only
checks a local compressed dump before a separate restore drill is allowed.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

_MIN_BACKUP_BYTES = 100
_SQL_SIGNATURES = (b"postgresql database dump", b"create table", b"-- dump completed")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_backup_artifact(path: Path, *, checksum_path: Path | None = None) -> dict[str, Any]:
    """Validate one local `.sql.gz` artifact without mutating anything."""
    blockers: list[str] = []
    result: dict[str, Any] = {
        "path": str(path),
        "valid": False,
        "size_bytes": 0,
        "checksum_verified": False,
        "sql_signature_found": False,
        "blockers": blockers,
        "production_mutation": False,
        "read_only": True,
    }
    if not path.is_file():
        blockers.append("file_missing")
        return result

    result["size_bytes"] = path.stat().st_size
    if result["size_bytes"] < _MIN_BACKUP_BYTES:
        blockers.append("file_too_small")

    try:
        with gzip.open(path, "rb") as handle:
            sql_head = handle.read(1024 * 1024).lower()
    except (OSError, EOFError):
        sql_head = b""
        blockers.append("invalid_gzip")

    if not any(signature in sql_head for signature in _SQL_SIGNATURES):
        blockers.append("sql_signature_missing")
    else:
        result["sql_signature_found"] = True

    if checksum_path is not None:
        if not checksum_path.is_file():
            blockers.append("checksum_file_missing")
        else:
            expected = checksum_path.read_text(encoding="utf-8").split()[0].lower()
            actual = _sha256(path)
            if expected == actual:
                result["checksum_verified"] = True
            else:
                blockers.append("checksum_mismatch")

    result["valid"] = not blockers
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--checksum", type=Path)
    args = parser.parse_args()
    result = validate_backup_artifact(args.backup, checksum_path=args.checksum)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
