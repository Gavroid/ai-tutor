"""Сервис audit log: запись действий и просмотр для админов."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Optional

from app.admin import models
from app.users import models as user_models
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session


def _compute_record_hash(
    user_id: int | None,
    action: str,
    entity: str | None,
    entity_id: str | None,
    details: str | None,
    ip_address: str | None,
    created_at_iso: str,
    previous_hash: str | None,
) -> str:
    """Sprint 45: SHA-256 hash от всех полей записи + previous_hash.

    Создаёт детерминированный hash, который меняется при любом изменении записи.
    Это позволяет detect tampering через verify_chain().
    """
    payload = json.dumps(
        {
            "user_id": user_id,
            "action": action,
            "entity": entity,
            "entity_id": entity_id,
            "details": details,
            "ip_address": ip_address,
            "created_at": created_at_iso,
            "previous_hash": previous_hash,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record(
    db: Session,
    user: user_models.User | None,
    action: str,
    entity: str | None = None,
    entity_id: str | None = None,
    details: dict | None = None,
    request: Optional[Request] = None,
) -> models.AuditLog:
    """Записать событие audit log с hash chain integrity (Sprint 45).

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

    details_json = json.dumps(details, ensure_ascii=False) if details else None

    # Sprint 45: получаем previous_hash (последняя запись по created_at).
    # Делаем в ОТДЕЛЬНОЙ транзакции чтобы не блокировать FOR UPDATE.
    prev_hash_row = db.execute(
        select(models.AuditLog.record_hash)
        .where(models.AuditLog.record_hash.is_not(None))
        .order_by(models.AuditLog.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    previous_hash = prev_hash_row

    # Создаём entry без hash (нужен created_at для compute).
    entry = models.AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=details_json,
        ip_address=ip,
        previous_hash=previous_hash,
    )
    db.add(entry)
    db.flush()  # нужен entry.id + entry.created_at

    # Sprint 45: вычисляем hash и сохраняем.
    created_at_iso = entry.created_at.isoformat() if entry.created_at else ""
    record_hash = _compute_record_hash(
        user_id=entry.user_id,
        action=entry.action,
        entity=entry.entity,
        entity_id=entry.entity_id,
        details=entry.details,
        ip_address=entry.ip_address,
        created_at_iso=created_at_iso,
        previous_hash=previous_hash,
    )
    entry.record_hash = record_hash

    db.commit()
    db.refresh(entry)
    return entry


def verify_chain(db: Session, limit: int = 1000) -> dict[str, Any]:
    """Sprint 45: проверить hash chain integrity.

    Возвращает:
    - verified: int — кол-во валидных записей
    - tampered: int — кол-во записей с невалидным hash
    - first_tampered_id: int | None — ID первой записи с невалидным hash
    - chain_broken_at: int | None — ID где previous_hash mismatch
    """
    rows = (
        db.execute(
            select(models.AuditLog)
            .where(models.AuditLog.record_hash.is_not(None))
            .order_by(models.AuditLog.id.asc())
            .limit(limit)
        )
        .scalars()
        .all()
    )

    verified = 0
    tampered = 0
    first_tampered_id = None
    chain_broken_at = None
    prev_hash = None

    for r in rows:
        # Проверяем chain
        if r.previous_hash != prev_hash:
            if chain_broken_at is None:
                chain_broken_at = r.id
                tampered += 1
                if first_tampered_id is None:
                    first_tampered_id = r.id
            continue

        # Проверяем hash записи
        created_at_iso = r.created_at.isoformat() if r.created_at else ""
        expected_hash = _compute_record_hash(
            user_id=r.user_id,
            action=r.action,
            entity=r.entity,
            entity_id=r.entity_id,
            details=r.details,
            ip_address=r.ip_address,
            created_at_iso=created_at_iso,
            previous_hash=r.previous_hash,
        )
        if expected_hash == r.record_hash:
            verified += 1
        else:
            tampered += 1
            if first_tampered_id is None:
                first_tampered_id = r.id

        prev_hash = r.record_hash

    return {
        "verified": verified,
        "tampered": tampered,
        "first_tampered_id": first_tampered_id,
        "chain_broken_at": chain_broken_at,
        "total_checked": len(rows),
    }


def list_logs(
    db: Session,
    user_id: int | None = None,
    action: str | None = None,
    entity: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[models.AuditLog]:
    """Список событий для админа с фильтром по дате.

    Sprint 10.4: добавлен фильтр по entity (audit.entity — например, "users",
    "exercises"). Фильтруются все параметры AND-логикой.
    """
    q = select(models.AuditLog).order_by(models.AuditLog.created_at.desc()).limit(limit).offset(offset)
    if user_id is not None:
        q = q.where(models.AuditLog.user_id == user_id)
    if action is not None:
        q = q.where(models.AuditLog.action == action)
    if entity is not None:
        q = q.where(models.AuditLog.entity == entity)
    if since is not None:
        # Нормализуем — БД может вернуть naive datetime
        since_v = since
        if since_v.tzinfo is None:
            from datetime import timezone

            since_v = since_v.replace(tzinfo=UTC)
        q = q.where(models.AuditLog.created_at >= since_v)
    if until is not None:
        until_v = until
        if until_v.tzinfo is None:
            from datetime import timezone

            until_v = until_v.replace(tzinfo=UTC)
        q = q.where(models.AuditLog.created_at <= until_v)
    return list(db.scalars(q).all())


def count_logs(
    db: Session,
    user_id: int | None = None,
    action: str | None = None,
    entity: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> int:
    """Sprint 10.4: total count для пагинации в audit log UI.

    Принимает те же фильтры что и list_logs (без limit/offset),
    возвращает количество подходящих записей.
    """
    from sqlalchemy import func as sqlfunc

    q = select(sqlfunc.count(models.AuditLog.id))
    if user_id is not None:
        q = q.where(models.AuditLog.user_id == user_id)
    if action is not None:
        q = q.where(models.AuditLog.action == action)
    if entity is not None:
        q = q.where(models.AuditLog.entity == entity)
    if since is not None:
        since_v = since
        if since_v.tzinfo is None:
            from datetime import timezone

            since_v = since_v.replace(tzinfo=UTC)
        q = q.where(models.AuditLog.created_at >= since_v)
    if until is not None:
        until_v = until
        if until_v.tzinfo is None:
            from datetime import timezone

            until_v = until_v.replace(tzinfo=UTC)
        q = q.where(models.AuditLog.created_at <= until_v)
    return db.scalar(q) or 0


# === Sprint 4.2: Audit log retention ===


def purge_old_logs(db: Session, ttl_days: int = 90) -> int:
    """Удаляет audit_logs старше ttl_days дней. Возвращает кол-во удалённых.

    Используется:
    - cron-задачей `audit_cleanup` (ежедневно)
    - admin endpoint /admin/audit-log/purge (ручная очистка)
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import delete

    cutoff = datetime.now(UTC) - timedelta(days=ttl_days)
    result = db.execute(delete(models.AuditLog).where(models.AuditLog.created_at < cutoff))
    db.commit()
    return int(result.rowcount or 0)


def _rehash_chain(db: Session) -> None:
    """Recompute audit hash chain from oldest to newest after retention pruning."""
    rows = (
        db.execute(select(models.AuditLog).order_by(models.AuditLog.created_at.asc(), models.AuditLog.id.asc()))
        .scalars()
        .all()
    )
    previous_hash = None
    for row in rows:
        row.previous_hash = previous_hash
        created_at_iso = row.created_at.isoformat() if row.created_at else ""
        row.record_hash = _compute_record_hash(
            user_id=row.user_id,
            action=row.action,
            entity=row.entity,
            entity_id=row.entity_id,
            details=row.details,
            ip_address=row.ip_address,
            created_at_iso=created_at_iso,
            previous_hash=previous_hash,
        )
        previous_hash = row.record_hash


def prune_logs_older_than(db: Session, retention_days: int, now: datetime | None = None) -> int:
    """Delete audit logs older than retention window and re-anchor hash chain.

    This is a maintenance primitive; production callers should run it only after
    backup. Rehashing is required because `previous_hash` points to deleted rows.
    """
    if retention_days <= 0:
        raise ValueError("retention_days must be positive")
    from datetime import datetime, timedelta, timezone

    current = now if now is not None else datetime.now(UTC)
    if getattr(current, "tzinfo", None) is None:
        current = current.replace(tzinfo=UTC)
    cutoff = current - timedelta(days=retention_days)

    old_rows = db.execute(select(models.AuditLog).where(models.AuditLog.created_at < cutoff)).scalars().all()
    deleted = len(old_rows)
    for row in old_rows:
        db.delete(row)
    if deleted:
        db.flush()
        _rehash_chain(db)
    db.commit()
    return deleted
