"""Local Algebra readiness snapshot from durable import rehearsal DB.

This is an endpoint-like readiness calculation for local/staging rehearsal data.
It deliberately routes through the fail-closed promotion gate, so local evidence
never promotes Algebra by itself.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from app.algebra_plan import ALGEBRA_TOPIC_PLAN
from scripts.algebra_durable_local_import_target import read_durable_audit_rows
from scripts.algebra_promotion_gate import evaluate_algebra_promotion
from scripts.rag_metadata_audit import audit_rows, summarize_audit

_REQUIRED_TOPIC_COUNT = len(ALGEBRA_TOPIC_PLAN)


def _source_topic_count(rows: list[dict[str, object]]) -> int:
    return len({int(cast(Any, row["material_topic_id"])) for row in rows})


def build_local_readiness_snapshot(*, db_path: Path, smoke_passed: bool = False) -> dict[str, object]:
    """Build fail-closed Algebra readiness snapshot from local durable import rows."""
    rows = read_durable_audit_rows(db_path=db_path)
    metadata_summary = summarize_audit(audit_rows(rows, expected_subject_code="algebra"))
    source_topic_count = _source_topic_count(rows) if rows else 0
    promotion = evaluate_algebra_promotion(
        route_topic_count=_REQUIRED_TOPIC_COUNT,
        source_topic_count=source_topic_count,
        practice_topic_count=_REQUIRED_TOPIC_COUNT,
        metadata_bad_rows=int(cast(Any, metadata_summary["bad_rows"])),
        import_mode="durable_local_sqlite_import_target",
        production_mutation=False,
        smoke_passed=smoke_passed,
        required_topic_count=_REQUIRED_TOPIC_COUNT,
    )
    return {
        "subject": "algebra",
        "source": "durable_local_sqlite_import_target",
        "db_path": str(db_path),
        "route_topic_count": _REQUIRED_TOPIC_COUNT,
        "source_topic_count": source_topic_count,
        "practice_topic_count": _REQUIRED_TOPIC_COUNT,
        "metadata_bad_rows": int(cast(Any, metadata_summary["bad_rows"])),
        "metadata_ok_rows": int(cast(Any, metadata_summary["ok_rows"])),
        "metadata_rows_checked": int(cast(Any, metadata_summary["rows_checked"])),
        **promotion,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Algebra local readiness snapshot")
    parser.add_argument("--db-path", default="/tmp/ai-tutor-algebra-local-import.sqlite3")
    parser.add_argument("--smoke-passed", action="store_true")
    args = parser.parse_args()
    snapshot = build_local_readiness_snapshot(db_path=Path(args.db_path), smoke_passed=args.smoke_passed)
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    return 0 if not snapshot["promotion_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
