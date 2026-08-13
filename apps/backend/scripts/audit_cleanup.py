"""Prune audit logs older than configured retention window.

Run only after backup in production.
"""
from __future__ import annotations

import os
import sys

from app.admin.service import prune_logs_older_than
from app.config import get_settings
from app.db.session import SessionLocal


def main() -> int:
    settings = get_settings()
    days = int(os.environ.get("AUDIT_RETENTION_DAYS", settings.audit_retention_days))
    with SessionLocal() as db:
        deleted = prune_logs_older_than(db, retention_days=days)
    print(f"audit_cleanup: deleted={deleted} retention_days={days}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
