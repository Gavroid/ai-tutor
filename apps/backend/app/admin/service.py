"""Сервис audit log: запись действий и просмотр для админов."""
from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin import models
from app.users import models as user_models


def record(
    db: Session,
    user: user_models.User | None,
    action: str,
    entity: str | None = None,
    entity_id: str | None = None,
    details: dict | None = None,
    request: Optional[Request] = None,
) -> models.AuditLog:
    """Записать событие audit log.

    Используется в middleware или вручную в роутерах при критичных операциях.

    IP берётся из:
    1. переданного request (приоритет)
    2. текущего contextvar (от middleware) — для случаев когда request не передали
    """
    # Если request не передан, берём из contextvar (set by middleware)
    if request is None:
        from app.admin.context import get_current_request

        request = get_current_request()

    ip = None
    if request is not None:
        try:
            ip = request.client.host if request.client else None
            # За прокси берём X-Forwarded-For
            xff = request.headers.get("x-forwarded-for")
            if xff:
                ip = xff.split(",")[0].strip()
        except Exception:
            ip = None
    entry = models.AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=json.dumps(details, ensure_ascii=False) if details else None,
        ip_address=ip,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_logs(
    db: Session,
    user_id: int | None = None,
    action: str | None = None,
    since: object | None = None,  # datetime | None
    until: object | None = None,  # datetime | None
    limit: int = 100,
    offset: int = 0,
) -> list[models.AuditLog]:
    """Список событий для админа с фильтром по дате."""
    q = select(models.AuditLog).order_by(models.AuditLog.created_at.desc()).limit(limit).offset(offset)
    if user_id is not None:
        q = q.where(models.AuditLog.user_id == user_id)
    if action is not None:
        q = q.where(models.AuditLog.action == action)
    if since is not None:
        # Нормализуем — БД может вернуть naive datetime
        since_v = since
        if since_v.tzinfo is None:
            from datetime import timezone

            since_v = since_v.replace(tzinfo=timezone.utc)
        q = q.where(models.AuditLog.created_at >= since_v)
    if until is not None:
        until_v = until
        if until_v.tzinfo is None:
            from datetime import timezone

            until_v = until_v.replace(tzinfo=timezone.utc)
        q = q.where(models.AuditLog.created_at <= until_v)
    return db.scalars(q).all()


# === Sprint 4.2: Audit log retention ===

def purge_old_logs(db: Session, ttl_days: int = 90) -> int:
    """Удаляет audit_logs старше ttl_days дней. Возвращает кол-во удалённых.

    Используется:
    - cron-задачей `audit_cleanup` (ежедневно)
    - admin endpoint /admin/audit-log/purge (ручная очистка)
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import delete

    cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
    result = db.execute(
        delete(models.AuditLog).where(models.AuditLog.created_at < cutoff)
    )
    db.commit()
    return int(result.rowcount or 0)