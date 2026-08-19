"""Fail-closed Algebra promotion gate.

This helper evaluates whether Algebra may move beyond preview. It is deliberately
conservative: local rehearsal data never promotes readiness by itself.
"""
from __future__ import annotations

import argparse
import json
from typing import Literal

_ALLOWED_IMPORT_MODES = {"staging_import", "production_import"}
ImportMode = Literal[
    "durable_local_sqlite_import_target",
    "disposable_sqlite_import_rehearsal",
    "local_import_dry_run_only",
    "staging_import",
    "production_import",
]


def evaluate_algebra_promotion(
    *,
    route_topic_count: int,
    source_topic_count: int,
    practice_topic_count: int,
    metadata_bad_rows: int,
    import_mode: str,
    production_mutation: bool,
    smoke_passed: bool,
    required_topic_count: int = 19,
) -> dict[str, object]:
    """Evaluate Algebra promotion readiness with fail-closed blockers."""
    blockers: list[str] = []
    if route_topic_count != required_topic_count:
        blockers.append("route_coverage_incomplete")
    if source_topic_count != required_topic_count:
        blockers.append("source_coverage_incomplete")
    if practice_topic_count != required_topic_count:
        blockers.append("practice_coverage_incomplete")
    if metadata_bad_rows != 0:
        blockers.append("metadata_audit_failed")
    if import_mode not in _ALLOWED_IMPORT_MODES:
        blockers.append("import_not_production_or_staging")
    if import_mode == "production_import" and not production_mutation:
        blockers.append("production_import_not_executed")
    if not smoke_passed:
        blockers.append("smoke_not_passed")

    promotion_allowed = not blockers
    return {
        "subject": "algebra",
        "mvp_status": "mvp_ready_candidate" if promotion_allowed else "preview",
        "route_ready": route_topic_count == required_topic_count,
        "rag_ready": promotion_allowed,
        "practice_ready": practice_topic_count == required_topic_count,
        "promotion_allowed": promotion_allowed,
        "blockers": blockers,
        "required_topic_count": required_topic_count,
        "route_topic_count": route_topic_count,
        "source_topic_count": source_topic_count,
        "practice_topic_count": practice_topic_count,
        "metadata_bad_rows": metadata_bad_rows,
        "import_mode": import_mode,
        "production_mutation": production_mutation,
        "smoke_passed": smoke_passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Algebra promotion readiness")
    parser.add_argument("--route-topic-count", type=int, required=True)
    parser.add_argument("--source-topic-count", type=int, required=True)
    parser.add_argument("--practice-topic-count", type=int, required=True)
    parser.add_argument("--metadata-bad-rows", type=int, required=True)
    parser.add_argument("--import-mode", required=True)
    parser.add_argument("--production-mutation", action="store_true")
    parser.add_argument("--smoke-passed", action="store_true")
    args = parser.parse_args()
    result = evaluate_algebra_promotion(
        route_topic_count=args.route_topic_count,
        source_topic_count=args.source_topic_count,
        practice_topic_count=args.practice_topic_count,
        metadata_bad_rows=args.metadata_bad_rows,
        import_mode=args.import_mode,
        production_mutation=args.production_mutation,
        smoke_passed=args.smoke_passed,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["promotion_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
