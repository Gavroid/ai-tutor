from __future__ import annotations

import csv
from pathlib import Path

from app.subjects.textbook_manifest_policy import (
    evaluate_textbook_manifest_row,
    validate_textbook_manifest,
)

REPO_ROOT = Path("/root/workspace/ai-tutor")
MANIFEST = REPO_ROOT / "data/textbooks/7-class/textbook-manifest.csv"


def _rows() -> list[dict[str, str]]:
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_unresolved_license_is_fail_closed_even_if_persisted_status_lies() -> None:
    row = {
        "license_decision": "needs_review",
        "status": "mvp_ready",
        "import_status": "ready",
        "rag_status": "ready",
    }

    result = evaluate_textbook_manifest_row(row)

    assert result["license_ready"] is False
    assert result["manifest_ready"] is False
    assert result["import_allowed"] is False
    assert result["rag_allowed"] is False
    assert result["pilot_allowed"] is False
    assert result["blocked_reason"] == "license_needs_review"


def test_current_textbook_manifest_is_entirely_blocked_until_license_review() -> None:
    rows = _rows()
    report = validate_textbook_manifest(rows)

    assert report["row_count"] == 20
    assert report["blocked_license_count"] == 20
    assert report["pilot_allowed"] is False
    assert report["production_mutation"] is False
    assert report["db_write"] is False
    assert report["rag_write"] is False
    assert all(item["pilot_allowed"] is False for item in report["rows"])


def test_explicit_open_license_is_eligible_but_not_automatically_promoted() -> None:
    row = {
        "license_decision": "cc_by",
        "status": "preview",
        "import_status": "not_started",
        "rag_status": "not_started",
    }

    result = evaluate_textbook_manifest_row(row)

    assert result["license_ready"] is True
    assert result["manifest_ready"] is False
    assert result["import_allowed"] is False
    assert result["rag_allowed"] is False
    assert result["pilot_allowed"] is False
    assert result["blocked_reason"] is None
