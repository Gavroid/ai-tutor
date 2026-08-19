"""Fail-closed Algebra staging/production import execution plan gate.

This checker decides whether it is safe to plan an Algebra source/RAG import into
staging or production. It performs no import and never mutates production.
"""
from __future__ import annotations

import argparse
import json
from typing import Literal

TargetEnv = Literal["local", "staging", "production"]
_ALLOWED_TARGETS = {"staging", "production"}
_REQUIRED_TOPIC_COUNT = 19


def evaluate_algebra_import_execution_plan(
    *,
    target_env: str,
    route_topic_count: int,
    source_topic_count: int,
    practice_topic_count: int,
    metadata_bad_rows: int,
    backup_verified: bool,
    offsite_verified: bool,
    target_tree_clean: bool,
    branch_aligned: bool,
    head_aligned: bool,
    smoke_plan_defined: bool,
    required_topic_count: int = _REQUIRED_TOPIC_COUNT,
) -> dict[str, object]:
    """Evaluate whether an Algebra import may be planned for staging/production."""
    blockers: list[str] = []
    if target_env not in _ALLOWED_TARGETS:
        blockers.append("target_not_staging_or_production")
    if route_topic_count != required_topic_count:
        blockers.append("route_coverage_incomplete")
    if source_topic_count != required_topic_count:
        blockers.append("source_coverage_incomplete")
    if practice_topic_count != required_topic_count:
        blockers.append("practice_coverage_incomplete")
    if metadata_bad_rows != 0:
        blockers.append("metadata_audit_failed")
    if not backup_verified:
        blockers.append("backup_not_verified")
    if not offsite_verified:
        blockers.append("offsite_not_verified")
    if not target_tree_clean:
        blockers.append("target_tree_dirty")
    if not branch_aligned:
        blockers.append("target_branch_mismatch")
    if not head_aligned:
        blockers.append("target_head_mismatch")
    if not smoke_plan_defined:
        blockers.append("smoke_plan_missing")

    import_allowed = not blockers
    if import_allowed and target_env == "staging":
        decision = "ready_for_staging_import_plan"
    elif import_allowed and target_env == "production":
        decision = "ready_for_production_import_plan"
    else:
        decision = "block_import"

    return {
        "subject": "algebra",
        "target_env": target_env,
        "decision": decision,
        "import_allowed": import_allowed,
        "promotion_allowed": False,
        "blockers": blockers,
        "required_topic_count": required_topic_count,
        "route_topic_count": route_topic_count,
        "source_topic_count": source_topic_count,
        "practice_topic_count": practice_topic_count,
        "metadata_bad_rows": metadata_bad_rows,
        "backup_verified": backup_verified,
        "offsite_verified": offsite_verified,
        "target_tree_clean": target_tree_clean,
        "branch_aligned": branch_aligned,
        "head_aligned": head_aligned,
        "smoke_plan_defined": smoke_plan_defined,
        "production_mutation": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Algebra import execution safety gate")
    parser.add_argument("--target-env", required=True, choices=["local", "staging", "production"])
    parser.add_argument("--route-topic-count", type=int, required=True)
    parser.add_argument("--source-topic-count", type=int, required=True)
    parser.add_argument("--practice-topic-count", type=int, required=True)
    parser.add_argument("--metadata-bad-rows", type=int, required=True)
    parser.add_argument("--backup-verified", action="store_true")
    parser.add_argument("--offsite-verified", action="store_true")
    parser.add_argument("--target-tree-clean", action="store_true")
    parser.add_argument("--branch-aligned", action="store_true")
    parser.add_argument("--head-aligned", action="store_true")
    parser.add_argument("--smoke-plan-defined", action="store_true")
    args = parser.parse_args()
    result = evaluate_algebra_import_execution_plan(
        target_env=args.target_env,
        route_topic_count=args.route_topic_count,
        source_topic_count=args.source_topic_count,
        practice_topic_count=args.practice_topic_count,
        metadata_bad_rows=args.metadata_bad_rows,
        backup_verified=args.backup_verified,
        offsite_verified=args.offsite_verified,
        target_tree_clean=args.target_tree_clean,
        branch_aligned=args.branch_aligned,
        head_aligned=args.head_aligned,
        smoke_plan_defined=args.smoke_plan_defined,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["import_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
