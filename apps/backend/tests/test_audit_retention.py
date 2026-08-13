from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.admin import service as audit_service
from app.admin.models import AuditLog
from app.db.session import Base, SessionLocal, engine


def _reset_db() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_prune_audit_logs_reanchors_hash_chain():
    _reset_db()
    now = datetime(2026, 8, 13, tzinfo=timezone.utc)
    db = SessionLocal()
    try:
        old_1 = audit_service.record(db, None, "old.one", entity="test")
        old_2 = audit_service.record(db, None, "old.two", entity="test")
        fresh = audit_service.record(db, None, "fresh.one", entity="test")

        old_1.created_at = now - timedelta(days=120)
        old_2.created_at = now - timedelta(days=91)
        fresh.created_at = now - timedelta(days=10)
        db.commit()

        deleted = audit_service.prune_logs_older_than(db, retention_days=90, now=now)

        remaining = db.query(AuditLog).order_by(AuditLog.created_at.asc()).all()
        assert deleted == 2
        assert [row.action for row in remaining] == ["fresh.one"]
        assert remaining[0].previous_hash is None
        assert remaining[0].record_hash is not None

        result = audit_service.verify_chain(db)
        assert result["tampered"] == 0
        assert result["verified"] == 1
    finally:
        db.close()
        _reset_db()
