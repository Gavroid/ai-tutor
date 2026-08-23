"""Fail-closed policy for textbook manifest rows.

This module is read-only: it evaluates metadata and never changes files or
imports content. A row with unresolved rights cannot become pilot-ready.
"""
from __future__ import annotations

from typing import Any


LICENSE_READY_DECISIONS = {
    "approved",
    "approved_with_attribution",
    "public_domain",
    "cc_by",
    "cc_by_sa",
}

BLOCKED_LICENSE_DECISIONS = {"needs_review", "rejected"}


def evaluate_textbook_manifest_row(row: dict[str, Any]) -> dict[str, Any]:
    """Return canonical readiness for one textbook manifest row."""
    decision = str(row.get("license_decision") or "needs_review")
    status = str(row.get("status") or "preview")
    import_status = str(row.get("import_status") or "not_started")
    rag_status = str(row.get("rag_status") or "not_started")

    license_ready = decision in LICENSE_READY_DECISIONS
    blocked_reason = None if license_ready else f"license_{decision}"
    return {
        "license_ready": license_ready,
        "manifest_ready": license_ready and status != "preview",
        "import_allowed": license_ready and import_status == "ready",
        "rag_allowed": license_ready and rag_status == "ready",
        "pilot_allowed": False,
        "blocked_reason": blocked_reason,
    }


def validate_textbook_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize canonical manifest policy without mutating input rows."""
    evaluations = [evaluate_textbook_manifest_row(row) for row in rows]
    blocked = sum(1 for item in evaluations if not item["license_ready"])
    return {
        "row_count": len(rows),
        "blocked_license_count": blocked,
        "pilot_allowed": False,
        "production_mutation": False,
        "db_write": False,
        "rag_write": False,
        "rows": evaluations,
    }
