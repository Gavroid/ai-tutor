"""Offline validator for production subject-scope drift."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


def evaluate_subject_scope(
    rows: Iterable[dict[str, Any]], *, expected_pilot_codes: set[str]
) -> dict[str, Any]:
    """Compare public subject flags with the expected pilot allow-list."""
    rows_list = list(rows)
    pilot_codes = sorted(
        str(row.get("code"))
        for row in rows_list
        if row.get("pilot_visible") is True or row.get("promotion_allowed") is True
    )
    promotion_codes = sorted(
        str(row.get("code")) for row in rows_list if row.get("promotion_allowed") is True
    )
    expected = sorted(expected_pilot_codes)
    blockers: list[str] = []
    if pilot_codes != expected:
        blockers.append("unexpected_pilot_subjects")
    if promotion_codes != expected:
        blockers.append("unexpected_promotion_subjects")
    return {
        "decision": "aligned" if not blockers else "blocked",
        "can_release": not blockers,
        "expected_pilot_codes": expected,
        "pilot_codes": pilot_codes,
        "promotion_codes": promotion_codes,
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    rows = json.loads(args.snapshot.read_text(encoding="utf-8"))
    result = evaluate_subject_scope(rows, expected_pilot_codes={"math"})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["can_release"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
