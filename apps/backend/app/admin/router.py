"""Роутер админ-кабинета: пользователи, audit log.

Sprint 1.1: все endpoints защищены require_admin() (RBAC-middleware).
Сохранены сообщения об ошибках для обратной совместимости с тестами.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.admin import schemas, service
from app.common.deps import Role, User, require_admin
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/audit-log", response_model=list[schemas.AuditLogOut])
def list_audit(
    user_id: int | None = None,
    action: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Audit log (только для admin). Поддерживает фильтры: action, user_id, since, until."""
    since_dt = None
    until_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(400, f"Некорректный since: {since}")
    if until:
        try:
            until_dt = datetime.fromisoformat(until.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(400, f"Некорректный until: {until}")

    return service.list_logs(
        db, user_id, action, since_dt, until_dt, min(limit, 500), max(offset, 0)
    )


@router.get("/users")
def list_users(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Список пользователей (только для admin)."""
    rows = db.scalars(
        select(User).order_by(User.id).limit(min(limit, 500)).offset(max(offset, 0))
    ).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "display_name": u.display_name,
            "role": u.role.value,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in rows
    ]


@router.post("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Деактивация пользователя (admin). Записывается в audit log."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "Пользователь не найден")
    if target.id == current.id:
        raise HTTPException(400, "Нельзя деактивировать себя")

    target.is_active = False
    service.record(
        db,
        user=current,
        action="user.deactivate",
        entity="user",
        entity_id=str(target.id),
        details={"email": target.email},
    )
    db.commit()
    return {"ok": True}


@router.get("/stats")
def admin_stats(
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Сводная статистика для админа."""
    total_users = db.scalar(select(func.count(User.id))) or 0
    active_users = db.scalar(
        select(func.count(User.id)).where(User.is_active.is_(True))
    ) or 0

    by_role = {}
    for role in Role:
        cnt = db.scalar(
            select(func.count(User.id)).where(User.role == role)
        ) or 0
        by_role[role.value] = cnt

    return {
        "total_users": int(total_users),
        "active_users": int(active_users),
        "by_role": by_role,
    }


@router.post("/diagnostics/expire-stale")
def expire_diagnostics(
    ttl_hours: int = 24,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Завершает in-progress diagnostic сессии старше ttl часов (по умолчанию 24)."""
    from app.diagnostics import service as diag_service

    count = diag_service.expire_stale_diagnostic_sessions(db, ttl_hours)
    service.record(
        db,
        user=current,
        action="diagnostics.expire",
        entity="diagnostic_sessions",
        details={"ttl_hours": ttl_hours, "expired_count": count},
    )
    db.commit()
    return {"ok": True, "expired_count": count}


@router.post("/notifications/test")
def test_notification(
    email: str = "admin@example.com",
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Тестовая отправка email (только для admin). Возвращает статус SMTP."""
    from app.notifications import service as notif_service

    async def _send():
        return await notif_service.send_email(
            db,
            user_id=current.id,
            to_email=email,
            subject="AI-репетитор: тестовое уведомление",
            body=(
                f"Это тестовое письмо от AI-репетитора.\n\n"
                f"Отправлено: {current.email}\n"
                f"Получатель: {email}\n"
                f"Время: {datetime.now(timezone.utc).isoformat()}\n"
            ),
        )

    try:
        rec = asyncio.run(_send())
    except Exception as e:
        raise HTTPException(500, f"Send error: {e}")

    service.record(
        db,
        user=current,
        action="notification.test",
        entity="email",
        entity_id=str(rec.id),
        details={"status": rec.status, "to": email},
    )
    db.commit()

    return {
        "ok": rec.status in ("sent", "dry_run"),
        "status": rec.status,
        "error": rec.error,
        "smtp_configured": bool(os.environ.get("SMTP_URL", "").strip()),
        "record_id": rec.id,
    }


# === Sprint 4.2: Audit log retention ===

@router.post("/audit-log/purge")
def purge_audit_log(
    ttl_days: int = 90,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Удаляет audit_logs старше ttl_days дней.

    По умолчанию 90 дней. Действие записывается в audit log.
    """
    deleted = service.purge_old_logs(db, ttl_days)
    service.record(
        db,
        user=current,
        action="audit.purge",
        entity="audit_logs",
        details={"ttl_days": ttl_days, "deleted_count": deleted},
    )
    db.commit()
    return {"ok": True, "deleted_count": deleted, "ttl_days": ttl_days}


# === Sprint 3.6.3: AI kill switch ===

@router.get("/ai-kill-switch")
def get_ai_kill_switch(
    current: User = Depends(require_admin()),
):
    """Возвращает список user_id для которых AI отключён.

    Sprint 3.6.3: emergency stop AI для user (ребёнок в AI-loop).
    """
    from app.config import get_settings
    s = get_settings()
    return {
        "user_ids": sorted(s.ai_kill_switch_user_id_set),
        "raw": s.ai_kill_switch_user_ids,
    }


@router.post("/ai-kill-switch/{user_id}")
def add_ai_kill_switch(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Добавляет user_id в AI kill switch. После этого AI endpoints
    для этого user возвращают 503 (даже если rate-limit не превышен).

    Sprint 3.6.3: emergency stop AI для user.
    """
    from app.config import get_settings
    s = get_settings()
    current_ids = s.ai_kill_switch_user_id_set
    if user_id in current_ids:
        return {"ok": True, "user_id": user_id, "already_killed": True}
    new_ids = sorted(current_ids | {user_id})
    s.ai_kill_switch_user_ids = ",".join(str(x) for x in new_ids)
    # NOTE: pydantic-settings Settings с @lru_cache возвращает singleton;
    # in-memory update работает до перезапуска backend.
    # Для persistent — нужно записать в .env файл (TODO Sprint 3.7+).
    service.record(
        db,
        user=current,
        action="ai.kill_switch.add",
        entity="users",
        details={"user_id": user_id, "all_killed": new_ids},
    )
    db.commit()
    return {"ok": True, "user_id": user_id, "all_killed": new_ids}


@router.delete("/ai-kill-switch/{user_id}")
def remove_ai_kill_switch(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Убирает user_id из AI kill switch. AI снова работает.

    Sprint 3.6.3: восстановление после emergency stop.
    """
    from app.config import get_settings
    s = get_settings()
    current_ids = s.ai_kill_switch_user_id_set
    if user_id not in current_ids:
        return {"ok": True, "user_id": user_id, "not_killed": True}
    new_ids = sorted(current_ids - {user_id})
    s.ai_kill_switch_user_ids = ",".join(str(x) for x in new_ids)
    service.record(
        db,
        user=current,
        action="ai.kill_switch.remove",
        entity="users",
        details={"user_id": user_id, "all_killed": new_ids},
    )
    db.commit()
    return {"ok": True, "user_id": user_id, "all_killed": new_ids}
