"""Evaluate whether AI-Tutor production marker can be safely advanced.

This helper is intentionally offline/read-only. It does not connect to
production, mutate files, or run deploy commands.
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Sequence


def _normalize_sha(value: str) -> str:
    return value.strip()[:7]


def evaluate_marker_state(
    *,
    local_head: str,
    production_marker: str,
    production_head: str,
    production_branch: str,
    production_dirty_paths: Sequence[str],
    intended_branch: str = "mvp-rescue",
) -> dict[str, object]:
    """Return a marker advancement decision from read-only release state."""
    local = _normalize_sha(local_head)
    marker = _normalize_sha(production_marker)
    prod_head = _normalize_sha(production_head)
    prod_branch = production_branch.strip().removeprefix("## ").split("...")[0]
    dirty_paths = [path for path in production_dirty_paths if path.strip()]

    blockers: list[str] = []
    if dirty_paths:
        blockers.append("production_tree_dirty")
    if prod_branch != intended_branch:
        blockers.append("production_branch_mismatch")
    if prod_head != local:
        blockers.append("production_head_mismatch")

    if blockers:
        decision = "blocked"
        can_advance = False
        recommended_mode = "targeted_deploy"
    elif marker == local:
        decision = "already_current"
        can_advance = False
        recommended_mode = "full_release"
    else:
        decision = "ready_for_marker_advance"
        can_advance = True
        recommended_mode = "full_release"

    return {
        "decision": decision,
        "can_advance_marker": can_advance,
        "target_marker": local,
        "current_marker": marker,
        "production_head": prod_head,
        "production_branch": prod_branch,
        "intended_branch": intended_branch,
        "dirty_path_count": len(dirty_paths),
        "dirty_paths_sample": dirty_paths[:20],
        "blockers": blockers,
        "recommended_mode": recommended_mode,
        "required_before_mutation": [
            "production backup + offsite verification",
            "clean/aligned production branch",
            "passing /ready and /health",
            "post-deploy smoke before marker write",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-head", required=True)
    parser.add_argument("--production-marker", required=True)
    parser.add_argument("--production-head", required=True)
    parser.add_argument("--production-branch", required=True)
    parser.add_argument("--dirty-path", action="append", default=[])
    parser.add_argument("--intended-branch", default="mvp-rescue")
    args = parser.parse_args()

    result = evaluate_marker_state(
        local_head=args.local_head,
        production_marker=args.production_marker,
        production_head=args.production_head,
        production_branch=args.production_branch,
        production_dirty_paths=args.dirty_path,
        intended_branch=args.intended_branch,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["decision"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
