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
    entity: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Audit log (только для admin). Поддерживает фильтры:
    action, user_id, entity, since, until.
    """
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
        db,
        user_id=user_id,
        action=action,
        entity=entity,
        since=since_dt,
        until=until_dt,
        limit=min(limit, 500),
        offset=max(offset, 0),
    )


# === Sprint 10.4: total count для пагинации в audit log ===
@router.get("/audit-log/count")
def audit_log_count(
    user_id: int | None = None,
    action: str | None = None,
    entity: str | None = None,
    since: str | None = None,
    until: str | None = None,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Sprint 10.4: количество audit_log записей с теми же фильтрами что в audit-log.

    Используется админом для отображения пагинации.
    """
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

    total = service.count_logs(
        db, user_id, action, entity, since_dt, until_dt
    )
    return {"total": int(total)}


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


# === Sprint 9: engagement метрики ===
@router.get("/engagement")
def admin_engagement(
    days: int = 30,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Sprint 9: метрики engagement за последние N дней.

    Возвращает:
    - active_users: уникальных пользователей с активностью за период
    - total_sessions: количество сессий (по audit_log)
    - avg_session_duration_min: средняя длительность сессии
    - retention_d1, retention_d7: cohort retention (TODO Sprint 9.2)
    - top_subjects: топ-3 предмета по attempts
    - daily_active_users: DAU за последние 14 дней (для графика)
    """
    from datetime import datetime, timedelta, timezone

    from app.progress import models as prog_models
    from app.subjects import models as subj_models
    from sqlalchemy import func as sqlfunc

    days = max(1, min(days, 365))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # DAU за последние 14 дней (для графика)
    dau_14 = []
    for d in range(13, -1, -1):
        day_start = (datetime.now(timezone.utc) - timedelta(days=d)).date()
        day_end = day_start + timedelta(days=1)
        # attempts за этот день
        cnt = db.scalar(
            select(sqlfunc.count(sqlfunc.distinct(prog_models.Attempt.user_id))).where(
                prog_models.Attempt.created_at >= day_start,
                prog_models.Attempt.created_at < day_end,
            )
        ) or 0
        dau_14.append({"date": day_start.isoformat(), "active_users": int(cnt)})

    # Active users за период
    active_user_ids = (
        db.execute(
            select(sqlfunc.distinct(prog_models.Attempt.user_id)).where(
                prog_models.Attempt.created_at >= since
            )
        ).scalars().all()
    )
    active_users = len(active_user_ids)

    # Total attempts за период
    total_attempts = db.scalar(
        select(sqlfunc.count(prog_models.Attempt.id)).where(
            prog_models.Attempt.created_at >= since
        )
    ) or 0

    # Top subjects (по количеству уникальных учеников с progress по теме этого предмета).
    # Простой подсчёт через progress → topic → section → subject.
    top_subjects_rows = db.execute(
        select(
            subj_models.Subject.id,
            subj_models.Subject.name,
            sqlfunc.count(sqlfunc.distinct(prog_models.Progress.user_id)).label(
                "students"
            ),
        )
        .select_from(prog_models.Progress)
        .join(subj_models.Topic, prog_models.Progress.topic_id == subj_models.Topic.id)
        .join(subj_models.Section, subj_models.Topic.section_id == subj_models.Section.id)
        .join(subj_models.Subject, subj_models.Section.subject_id == subj_models.Subject.id)
        .group_by(subj_models.Subject.id, subj_models.Subject.name)
        .order_by(sqlfunc.count(sqlfunc.distinct(prog_models.Progress.user_id)).desc())
        .limit(3)
    ).all()

    top_subjects = [
        {"id": s[0], "name": s[1], "students": int(s[2])}
        for s in top_subjects_rows
    ]

    return {
        "period_days": days,
        "active_users": active_users,
        "total_attempts": int(total_attempts),
        "avg_attempts_per_active_user": (
            round(total_attempts / active_users, 1) if active_users else 0
        ),
        "dau_last_14_days": dau_14,
        "top_subjects": top_subjects,
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


# === Sprint 3.6.3: AI kill switch (persistent через Redis) ===

async def _read_kill_switch(redis) -> set[int]:
    """Читает kill switch из Redis (key='ai:kill_switch')."""
    try:
        raw = await redis.get("ai:kill_switch")
        if not raw:
            return set()
        return {int(x) for x in raw.decode() if x.isdigit()}
    except Exception:
        return set()


async def _write_kill_switch(redis, ids: set[int]) -> None:
    """Пишет kill switch в Redis."""
    try:
        await redis.set("ai:kill_switch", "".join(str(x) for x in sorted(ids)))
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("kill_switch write failed: %s", e)


async def _get_redis_for_admin():
    """Получить Redis instance (используем тот же что в rate_limit)."""
    try:
        import redis.asyncio as aioredis
        url = __import__("os").environ.get("REDIS_URL", "redis://redis:6379/0")
        return aioredis.from_url(url, decode_responses=False)
    except Exception:
        return None


@router.get("/ai-kill-switch")
async def get_ai_kill_switch(
    current: User = Depends(require_admin()),
):
    """Возвращает список user_id для которых AI отключён.

    Sprint 3.6.3: emergency stop AI для user (ребёнок в AI-loop).
    Persistent через Redis — работает в multi-worker uvicorn.
    """
    redis = await _get_redis_for_admin()
    if redis is None:
        return {"user_ids": [], "raw": "", "error": "redis_unavailable"}
    user_ids = await _read_kill_switch(redis)
    await redis.aclose()
    return {
        "user_ids": sorted(user_ids),
        "raw": ",".join(str(x) for x in sorted(user_ids)),
    }


@router.post("/ai-kill-switch/{user_id}")
async def add_ai_kill_switch(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Добавляет user_id в AI kill switch. После этого AI endpoints
    для этого user возвращают 503 (даже если rate-limit не превышен).

    Sprint 3.6.3: persistent через Redis — multi-worker safe.
    """
    redis = await _get_redis_for_admin()
    if redis is None:
        return {"ok": False, "error": "redis_unavailable"}
    current_ids = await _read_kill_switch(redis)
    if user_id in current_ids:
        await redis.aclose()
        return {"ok": True, "user_id": user_id, "already_killed": True}
    new_ids = current_ids | {user_id}
    await _write_kill_switch(redis, new_ids)
    await redis.aclose()
    service.record(
        db,
        user=current,
        action="ai.kill_switch.add",
        entity="users",
        details={"user_id": user_id, "all_killed": sorted(new_ids)},
    )
    db.commit()
    return {"ok": True, "user_id": user_id, "all_killed": sorted(new_ids)}


@router.delete("/ai-kill-switch/{user_id}")
async def remove_ai_kill_switch(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Убирает user_id из AI kill switch. AI снова работает.

    Sprint 3.6.3: восстановление после emergency stop.
    """
    redis = await _get_redis_for_admin()
    if redis is None:
        return {"ok": False, "error": "redis_unavailable"}
    current_ids = await _read_kill_switch(redis)
    if user_id not in current_ids:
        await redis.aclose()
        return {"ok": True, "user_id": user_id, "not_killed": True}
    new_ids = current_ids - {user_id}
    await _write_kill_switch(redis, new_ids)
    await redis.aclose()
    service.record(
        db,
        user=current,
        action="ai.kill_switch.remove",
        entity="users",
        details={"user_id": user_id, "all_killed": sorted(new_ids)},
    )
    db.commit()
    return {"ok": True, "user_id": user_id, "all_killed": sorted(new_ids)}
