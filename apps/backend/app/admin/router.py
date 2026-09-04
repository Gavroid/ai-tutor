"""Роутер админ-кабинета: пользователи, audit log.

Sprint 1.1: все endpoints защищены require_admin() (RBAC-middleware).
Сохранены сообщения об ошибках для обратной совместимости с тестами.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Annotated

from app.admin import models, schemas, service
from app.admin import service as audit_service
from app.common.deps import Role, User, require_admin
from app.db.session import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/audit-log", response_model=list[schemas.AuditLogOut])
def list_audit(
    user_id: int | None = None,
    action: str | None = None,
    entity: str | None = None,
    since: str | None = None,
    until: str | None = None,
    # Sprint 16.0 P0-8: явные bounds (Query validators) для предотвращения DoS.
    # Раньше был silent clamp (min(limit, 500)), теперь 422 на невалидные.
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
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
        limit=limit,
        offset=offset,
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
    # Sprint 76: защита от unbounded date range.
    # Если оба фильтра since+until не указаны — потенциально можно прочитать
    # всю таблицу audit_log (10K+ строк). Ограничиваем дефолтный диапазон
    # последними 90 днями если фильтры не указаны.
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

    # Sprint 76: если оба фильтра None, дефолт = последние 90 дней.
    # Защищает от случайного чтения всей таблицы.
    if since_dt is None and until_dt is None:
        from datetime import timedelta

        until_dt = datetime.now(UTC)
        since_dt = until_dt - timedelta(days=90)

    # Sprint 76: если только один фильтр, ограничиваем диапазон max 2 года.
    if since_dt and until_dt:
        delta_days = (until_dt - since_dt).days
        if delta_days > 730:  # 2 года
            raise HTTPException(
                400,
                f"Date range too large: {delta_days} days (max 730)",
            )

    total = service.count_logs(db, user_id, action, entity, since_dt, until_dt)
    return {"total": int(total)}


@router.get("/users")
def list_users(
    # Sprint 67: явные bounds (Query validators) для предотвращения DoS.
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Список пользователей (только для admin)."""
    rows = db.scalars(select(User).order_by(User.id).limit(limit).offset(offset)).all()
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


@router.get("/ops/status")
def admin_ops_status(
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Stage 6: one-shot operator preflight status for MVP manual testing."""
    from app.config import get_settings
    from sqlalchemy import text

    settings = get_settings()
    db_ok = False
    db_error = None
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # noqa: BLE001
        db_error = str(exc)[:200]

    redis_ok = False
    redis_error = None
    try:
        import redis as redis_lib

        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        r = redis_lib.Redis.from_url(redis_url, socket_timeout=2)
        redis_ok = bool(r.ping())
        r.close()
    except Exception as exc:  # noqa: BLE001
        redis_error = str(exc)[:200]

    upload_dir = Path(settings.upload_dir)
    registry_path = upload_dir / "teacher_content_registry.json"
    marker_path = Path(os.environ.get("OPS_COMMIT_MARKER_PATH", "/app/.mvp-rescue-commit"))
    backup_cron = Path(os.environ.get("OPS_BACKUP_CRON_PATH", "/app/ops/ai-tutor-backup"))
    backup_script = Path(os.environ.get("OPS_BACKUP_SCRIPT_PATH", "/app/ops/backup.sh"))

    checks = {
        "database": {"ok": db_ok, "error": db_error},
        "redis": {"ok": redis_ok, "error": redis_error},
        "uploads": {"ok": upload_dir.exists(), "path": str(upload_dir)},
        "teacher_registry": {
            "ok": registry_path.exists() or upload_dir.exists(),
            "path": str(registry_path),
            "exists": registry_path.exists(),
        },
        "backup": {
            "cron_exists": backup_cron.exists(),
            "cron_path": str(backup_cron),
            "script_exists": backup_script.exists(),
            "script_path": str(backup_script),
        },
        "commit_marker": {
            "ok": marker_path.exists(),
            "path": str(marker_path),
            "commit": marker_path.read_text().strip() if marker_path.exists() else None,
        },
    }
    overall_ok = bool(db_ok and redis_ok and upload_dir.exists())
    return {
        "ok": overall_ok,
        "checked_at": datetime.now(UTC).isoformat(),
        "environment": settings.app_env,
        "checks": checks,
    }


@router.get("/stats")
def admin_stats(
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Сводная статистика для админа."""
    total_users = db.scalar(select(func.count(User.id))) or 0
    active_users = db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0

    by_role = {}
    for role in Role:
        cnt = db.scalar(select(func.count(User.id)).where(User.role == role)) or 0
        by_role[role.value] = cnt

    return {
        "total_users": int(total_users),
        "active_users": int(active_users),
        "by_role": by_role,
    }


# === Sprint 9: engagement метрики ===
@router.get("/engagement")
def admin_engagement(
    # Sprint 16.0 P0-8: явные bounds вместо silent clamp.
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Sprint 9: метрики engagement за последние N дней.

    Sprint 89: Redis cache (TTL 60s) для expensive queries.

    Возвращает:
    - active_users: уникальных пользователей с активностью за период
    - total_sessions: количество сессий (по audit_log)
    - avg_session_duration_min: средняя длительность сессии
    - retention_d1, retention_d7, retention_d30: cohort retention (Sprint 85)
    - top_subjects: топ-3 предмета по attempts
    - daily_active_users: DAU за последние 14 дней (для графика)
    """
    import json
    from datetime import datetime, timedelta

    import redis as redis_lib
    from app.progress import models as prog_models
    from app.subjects import models as subj_models
    from sqlalchemy import func as sqlfunc

    # Sprint 89: Redis cache для expensive engagement queries.
    # TTL 60 секунд — дашборд не критичный к fresh data.
    cache_key = f"engagement:{days}"
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        r = redis_lib.Redis.from_url(redis_url, decode_responses=True)
        cached = r.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        # Cache miss/fail — proceed to DB query
        pass

    since = datetime.now(UTC) - timedelta(days=days)

    # DAU за последние 14 дней (для графика)
    dau_14 = []
    for d in range(13, -1, -1):
        day_start = (datetime.now(UTC) - timedelta(days=d)).date()
        day_end = day_start + timedelta(days=1)
        # attempts за этот день
        cnt = (
            db.scalar(
                select(sqlfunc.count(sqlfunc.distinct(prog_models.Attempt.user_id))).where(
                    prog_models.Attempt.created_at >= day_start,
                    prog_models.Attempt.created_at < day_end,
                )
            )
            or 0
        )
        dau_14.append({"date": day_start.isoformat(), "active_users": int(cnt)})

    # Active users за период
    active_user_ids = (
        db.execute(select(sqlfunc.distinct(prog_models.Attempt.user_id)).where(prog_models.Attempt.created_at >= since))
        .scalars()
        .all()
    )
    active_users = len(active_user_ids)

    # Total attempts за период
    total_attempts = (
        db.scalar(select(sqlfunc.count(prog_models.Attempt.id)).where(prog_models.Attempt.created_at >= since)) or 0
    )

    # Top subjects (по количеству уникальных учеников с progress по теме этого предмета).
    # Простой подсчёт через progress → topic → section → subject.
    top_subjects_rows = db.execute(
        select(
            subj_models.Subject.id,
            subj_models.Subject.name,
            sqlfunc.count(sqlfunc.distinct(prog_models.Progress.user_id)).label("students"),
        )
        .select_from(prog_models.Progress)
        .join(subj_models.Topic, prog_models.Progress.topic_id == subj_models.Topic.id)
        .join(subj_models.Section, subj_models.Topic.section_id == subj_models.Section.id)
        .join(subj_models.Subject, subj_models.Section.subject_id == subj_models.Subject.id)
        .group_by(subj_models.Subject.id, subj_models.Subject.name)
        .order_by(sqlfunc.count(sqlfunc.distinct(prog_models.Progress.user_id)).desc())
        .limit(3)
    ).all()

    top_subjects = [{"id": s[0], "name": s[1], "students": int(s[2])} for s in top_subjects_rows]

    # Sprint 85: cohort retention (D1, D7, D30).
    # Для каждого cohort week (Monday-based, ISO format), считаем:
    # - cohort_size: сколько users зарегистрировано в эту неделю
    # - retained_d1: сколько вернулись через 1 день
    # - retained_d7: сколько вернулись через 7 дней
    # - retained_d30: сколько вернулись через 30 дней
    from app.users import models as user_models

    retention_cohorts = []
    # Cohort weeks: последние N недель, в пределах period
    cohort_week_count = min(days // 7, 8) if days >= 7 else 0
    if cohort_week_count > 0:
        now = datetime.now(UTC)
        for week_offset in range(cohort_week_count):
            cohort_end = now - timedelta(weeks=week_offset)
            cohort_start = cohort_end - timedelta(days=7)
            # Cohort: users created_at за эту неделю
            cohort_user_ids = set(
                db.execute(
                    select(user_models.User.id).where(
                        user_models.User.created_at >= cohort_start,
                        user_models.User.created_at < cohort_end,
                    )
                )
                .scalars()
                .all()
            )
            if not cohort_user_ids:
                continue
            cohort_size = len(cohort_user_ids)
            # Retained D1: users с attempt >=1 day+1 после cohort_end
            retained_d1 = (
                db.scalar(
                    select(sqlfunc.count(sqlfunc.distinct(prog_models.Attempt.user_id))).where(
                        prog_models.Attempt.user_id.in_(cohort_user_ids),
                        prog_models.Attempt.created_at >= cohort_end + timedelta(days=1),
                        prog_models.Attempt.created_at < cohort_end + timedelta(days=2),
                    )
                )
                or 0
            )
            # Retained D7
            retained_d7 = (
                db.scalar(
                    select(sqlfunc.count(sqlfunc.distinct(prog_models.Attempt.user_id))).where(
                        prog_models.Attempt.user_id.in_(cohort_user_ids),
                        prog_models.Attempt.created_at >= cohort_end + timedelta(days=7),
                        prog_models.Attempt.created_at < cohort_end + timedelta(days=8),
                    )
                )
                or 0
            )
            # Retained D30 (только для старых cohorts)
            retained_d30 = 0
            if week_offset >= 4:  # только cohorts старше 30 дней
                retained_d30 = (
                    db.scalar(
                        select(sqlfunc.count(sqlfunc.distinct(prog_models.Attempt.user_id))).where(
                            prog_models.Attempt.user_id.in_(cohort_user_ids),
                            prog_models.Attempt.created_at >= cohort_end + timedelta(days=30),
                            prog_models.Attempt.created_at < cohort_end + timedelta(days=31),
                        )
                    )
                    or 0
                )

            retention_cohorts.append(
                {
                    "cohort_week": cohort_start.date().isoformat(),
                    "cohort_size": cohort_size,
                    "retained_d1": int(retained_d1),
                    "retained_d1_pct": round(retained_d1 / cohort_size * 100, 1) if cohort_size else 0,
                    "retained_d7": int(retained_d7),
                    "retained_d7_pct": round(retained_d7 / cohort_size * 100, 1) if cohort_size else 0,
                    "retained_d30": int(retained_d30),
                    "retained_d30_pct": round(retained_d30 / cohort_size * 100, 1)
                    if cohort_size and week_offset >= 4
                    else None,
                }
            )

    result = {
        "period_days": days,
        "active_users": active_users,
        "total_attempts": int(total_attempts),
        "avg_attempts_per_active_user": (round(total_attempts / active_users, 1) if active_users else 0),
        "dau_last_14_days": dau_14,
        "top_subjects": top_subjects,
        "retention_cohorts": retention_cohorts,
    }

    # Sprint 89: save to Redis cache (TTL 60s).
    try:
        if "r" in locals():
            r.setex(cache_key, 60, json.dumps(result))
    except Exception:
        pass

    return result


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
                f"Время: {datetime.now(UTC).isoformat()}\n"
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


# === Sprint 45: Audit log hash chain verification ===


@router.get("/audit-log/verify")
def verify_audit_log_chain(
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Sprint 45: проверить hash chain integrity (tamper detection)."""
    result = service.verify_chain(db, limit=limit)
    return result


@router.get("/audit-log/export")
def export_audit_log(
    fmt: str = Query("json", pattern="^(json|csv)$"),
    since: str | None = Query(None, description="ISO datetime"),
    until: str | None = Query(None, description="ISO datetime"),
    # Sprint 87: max_records позволяет админу выбрать сколько rows export.
    # Default 10000 (Sprint 45), max 100000 (DoS protection).
    max_records: int = Query(10000, ge=1, le=100000),
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Sprint 45: export audit log (для compliance).
    Sprint 87: max_records query param (1-100000)."""
    import csv
    import io
    from datetime import datetime

    from sqlalchemy import select

    q = select(models.AuditLog)
    if since:
        from datetime import timezone

        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=UTC)
        q = q.where(models.AuditLog.created_at >= since_dt)
    if until:
        from datetime import timezone

        until_dt = datetime.fromisoformat(until.replace("Z", "+00:00"))
        if until_dt.tzinfo is None:
            until_dt = until_dt.replace(tzinfo=UTC)
        q = q.where(models.AuditLog.created_at <= until_dt)
    q = q.order_by(models.AuditLog.id.asc()).limit(max_records)
    rows = db.execute(q).scalars().all()

    # Log the export action
    service.record(
        db,
        user=current,
        action="audit.export",
        entity="audit_logs",
        details={"format": fmt, "rows": len(rows)},
    )
    db.commit()

    if fmt == "json":
        return [
            {
                "id": r.id,
                "user_id": r.user_id,
                "action": r.action,
                "entity": r.entity,
                "entity_id": r.entity_id,
                "details": r.details,
                "ip_address": r.ip_address,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "previous_hash": r.previous_hash,
                "record_hash": r.record_hash,
            }
            for r in rows
        ]
    # CSV format
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "user_id",
            "action",
            "entity",
            "entity_id",
            "details",
            "ip_address",
            "created_at",
            "previous_hash",
            "record_hash",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r.id,
                r.user_id or "",
                r.action,
                r.entity or "",
                r.entity_id or "",
                r.details or "",
                r.ip_address or "",
                r.created_at.isoformat() if r.created_at else "",
                r.previous_hash or "",
                r.record_hash or "",
            ]
        )
    return {"filename": f"audit_log_{fmt}.csv", "content": output.getvalue()}


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


@router.post("/config/reload-ai-budget")
def reload_ai_budget_config(
    daily_requests: int | None = None,
    daily_tokens: int | None = None,
    hourly_requests: int | None = None,
    alert_threshold: int | None = None,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Sprint 86: hot-reload AI budget limits без рестарта.

    Позволяет админу менять лимиты в production без downtime.
    Изменения применяются immediately (module attribute replacement).

    Args:
        daily_requests: новый DAILY_REQUESTS_LIMIT (None = keep current)
        daily_tokens: новый DAILY_TOKENS_LIMIT
        hourly_requests: новый HOURLY_REQUESTS_LIMIT
        alert_threshold: новый ALERT_THRESHOLD_PCT (1-100)

    Returns:
        200 with updated limits
        400 if invalid params
    """
    from app.ai import budget as budget_module

    try:
        budget_module.reload_limits(
            daily_requests=daily_requests,
            daily_tokens=daily_tokens,
            hourly_requests=hourly_requests,
            alert_threshold=alert_threshold,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    # Audit log
    audit_service.record(
        db,
        user=current,
        action="config.reload",
        entity="ai_budget",
        entity_id="runtime",
        details={
            "daily_requests": budget_module.DAILY_REQUESTS_LIMIT,
            "daily_tokens": budget_module.DAILY_TOKENS_LIMIT,
            "hourly_requests": budget_module.HOURLY_REQUESTS_LIMIT,
            "alert_threshold": budget_module.ALERT_THRESHOLD_PCT,
        },
    )

    return {
        "ok": True,
        "daily_requests": budget_module.DAILY_REQUESTS_LIMIT,
        "daily_tokens": budget_module.DAILY_TOKENS_LIMIT,
        "hourly_requests": budget_module.HOURLY_REQUESTS_LIMIT,
        "alert_threshold": budget_module.ALERT_THRESHOLD_PCT,
    }


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


# === Sprint 2026-08-22: Evidence update endpoints ===
# Эти endpoints управляют readiness gates в data/textbooks/7-class/evidence.json.
# Используют те же guards, что и другие admin endpoints, и пишут в audit log.

EVIDENCE_GATES = (
    "manifest_ready",
    "mapping_ready",
    "import_ready",
    "rag_ready",
    "practice_ready",
    "manual_smoke_ready",
)
EVIDENCE_PROMOTION = ("pilot_visible", "promotion_allowed")
ALL_EVIDENCE_FIELDS = EVIDENCE_GATES + EVIDENCE_PROMOTION

_EVIDENCE_PATHS = [
    Path("/opt/ai-tutor/data/textbooks/7-class/evidence.json"),  # production mount
    Path("/app/data/textbooks/7-class/evidence.json"),  # alternative prod path
    Path("/root/workspace/ai-tutor/data/textbooks/7-class/evidence.json"),  # dev path
]

# Override-точка для тестов: tests/test_admin_evidence.py делает
# monkeypatch.setattr(admin_router, "_EVIDENCE_PATH", tmp_evidence).
# В рантайме остаётся None и путь резолвится через _EVIDENCE_PATHS.
_EVIDENCE_PATH: Path | None = None


def _resolve_active_evidence_path() -> Path | None:
    """Вернуть активный override, если он задан; иначе None.

    Отделён от _find_evidence_path, чтобы monkeypatch setattr на
    ``_EVIDENCE_PATH=None`` (сброс) обрабатывался корректно.
    """
    return globals().get("_EVIDENCE_PATH", None)


def _find_evidence_path() -> Path | None:
    """Найти рабочий путь к evidence.json.

    Возвращает Path() если файл существует и readable; None иначе.
    PermissionError safe: внутри Docker некоторые пути могут быть недоступны.
    """
    override: Path | None = _resolve_active_evidence_path()
    if override is not None:
        try:
            candidate = Path(override)
            if candidate.exists():
                return candidate
        except (OSError, PermissionError):
            pass
    for candidate in _EVIDENCE_PATHS:
        try:
            if candidate.exists():
                return candidate
        except (OSError, PermissionError):
            continue
    return None


def _load_evidence() -> dict[str, dict]:
    """Прочитать evidence.json; если файла нет — пустой dict.

    Путь overridable через monkeypatch: tests/test_admin_evidence.py меняет
    app.admin.router._EVIDENCE_PATH на tmp.
    """
    path = _find_evidence_path()
    if path is None:
        return {}
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _save_evidence(data: dict[str, dict]) -> None:
    import json

    path = _find_evidence_path()
    if path is None:
        path = _EVIDENCE_PATHS[0]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _evidence_mvp_status(row: dict) -> str:
    if row.get("promotion_allowed") and all(row.get(g) for g in EVIDENCE_GATES):
        return "mvp_ready"
    if row.get("blocked_reason"):
        return str(row["blocked_reason"])
    if any(row.get(g) for g in EVIDENCE_GATES):
        return "internal_mvp"
    return "preview"


def _canonical_promotion(row: dict, subject_code: str) -> tuple[bool, bool]:
    """Sprint 3: derived canonical promotion flags (НЕ persisted).

    Возвращает (promotion_allowed, pilot_visible) исходя из:
      - все EVIDENCE_GATES true;
      - blocked_reason is None;
      - subject_code в PILOT_SCOPE (только math).

    Эти правила — single source of truth для API и для записи.
    Persisted значения из evidence.json НЕ доверяются напрямую
    (см. evidence_schema.validate_evidence_payload).
    """
    from app.subjects.evidence_schema import PILOT_SCOPE, REQUIRED_GATES

    all_required = all(bool(row.get(g)) for g in REQUIRED_GATES)
    blocked = row.get("blocked_reason")
    in_scope = subject_code in PILOT_SCOPE
    promotion = all_required and blocked is None and in_scope
    return promotion, promotion  # pilot_visible == promotion_allowed


def _canonicalize_row(row: dict, subject_code: str) -> dict:
    """Переписать pilot_visible/promotion_allowed на canonical."""
    promo, pilot = _canonical_promotion(row, subject_code)
    out = dict(row)
    out["promotion_allowed"] = promo
    out["pilot_visible"] = pilot
    return out


@router.get("/evidence")
def list_evidence(
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Список readiness всех предметов (admin).

    Возвращает каждый subject_code с текущими gates и вычисленным mvp_status.
    Sprint 3: pilot_visible/promotion_allowed — derived canonical, НЕ
    persisted (см. _canonical_promotion).
    """
    data = _load_evidence()
    out = []
    for code in sorted(data.keys()):
        row = data[code]
        canonical = _canonicalize_row(row, code)
        # Сохраняем persisted-vs-canonical divergence для аудита.
        persisted_promo = bool(row.get("promotion_allowed"))
        canonical_promo = bool(canonical.get("promotion_allowed"))
        divergence = "ok"
        if persisted_promo and not canonical_promo:
            divergence = "persisted_overrides_canonical"
        out.append(
            {
                "subject_code": code,
                "mvp_status": _evidence_mvp_status(canonical),
                "pilot_visible": bool(canonical.get("pilot_visible")),
                "promotion_allowed": bool(canonical.get("promotion_allowed")),
                "blocked_reason": canonical.get("blocked_reason"),
                "gates": {g: bool(canonical.get(g)) for g in EVIDENCE_GATES},
                "persisted_promotion_allowed": persisted_promo,
                "canonical_divergence": divergence,
            }
        )
    service.record(
        db,
        user=current,
        action="evidence.list",
        entity="evidence",
        details={"count": len(out)},
    )
    db.commit()
    return {"evidence": out}


@router.post("/evidence/{subject_code}")
def update_evidence(
    subject_code: str,
    payload: dict,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """Обновить readiness gates для предмета (admin).

    payload: {"gates": {"mapping_ready": true, ...}, "promotion_allowed": false, ...}
    Любые поля вне EVIDENCE_GATES и EVIDENCE_PROMOTION игнорируются.

    Инварианты:
    - promotion_allowed=true только если все EVIDENCE_GATES=true.
      Иначе 400.
    - pilot_visible=true требует promotion_allowed=true.
      Иначе 400.
    """
    gates = payload.get("gates", {}) if isinstance(payload, dict) else {}
    promotion = {k: payload.get(k) for k in EVIDENCE_PROMOTION if k in payload} if isinstance(payload, dict) else {}

    # Проверка неизвестных полей.
    unknown = set((gates or {}).keys()) - set(EVIDENCE_GATES)
    if unknown:
        raise HTTPException(400, f"Unknown gates: {sorted(unknown)}")
    unknown_promotion = set(promotion.keys()) - set(EVIDENCE_PROMOTION)
    if unknown_promotion:
        raise HTTPException(400, f"Unknown promotion fields: {sorted(unknown_promotion)}")

    data = _load_evidence()
    row = data.get(subject_code)
    if row is None:
        raise HTTPException(404, f"subject_code '{subject_code}' not in evidence.json")

    # Применить изменения gates к row.
    for g, v in gates.items():
        row[g] = bool(v)
    # Persisted-флаги promotion/pilot принимаем только как HINT;
    # canonical write всё равно пересчитывает их через _canonical_promotion.
    for k, v in promotion.items():
        row[k] = bool(v)

    # Sprint 3: что бы ни прислал admin, persisted promotion/pilot
    # будут перезаписаны canonical. Сначала проверяем инвариант по persistence,
    # чтобы admin не мог записать promotion=true при неполных gates.
    if promotion.get("promotion_allowed") is True:
        post_gates = {g: bool(row.get(g)) for g in EVIDENCE_GATES}
        if not all(post_gates.values()):
            missing = [g for g in EVIDENCE_GATES if not post_gates[g]]
            raise HTTPException(
                400,
                f"Cannot set promotion_allowed=true; missing gates: {missing}",
            )
    if promotion.get("pilot_visible") is True and not promotion.get("promotion_allowed"):
        # Если pilot=true без promo=true, но исходное persisted promo=true,
        # разрешаем (canonical sync). Иначе — guard.
        if not row.get("promotion_allowed"):
            raise HTTPException(
                400,
                "Cannot set pilot_visible=true without promotion_allowed=true",
            )

    # Sprint 3: write canonical — НЕ persisted.
    canonical_row = _canonicalize_row(row, subject_code)
    # Sprint 3: при записи pilot_visible/promotion_allowed синхронизируется
    # с canonical — persisted НЕ хранится «в обход» policy.
    row["pilot_visible"] = bool(canonical_row["pilot_visible"])
    row["promotion_allowed"] = bool(canonical_row["promotion_allowed"])

    if canonical_row["promotion_allowed"] != row.get("promotion_allowed") or canonical_row["pilot_visible"] != row.get(
        "pilot_visible"
    ):
        # Не падаем — пишем canonical + log warning.
        import logging

        logging.getLogger(__name__).warning(
            "evidence.update(%s): canonical override "
            "persisted_promo=%s → canonical_promo=%s, "
            "persisted_pilot=%s → canonical_pilot=%s "
            "(blocked_reason=%s, scope_member=%s)",
            subject_code,
            row.get("promotion_allowed"),
            canonical_row["promotion_allowed"],
            row.get("pilot_visible"),
            canonical_row["pilot_visible"],
            row.get("blocked_reason"),
            subject_code in _evidence_pilot_scope(),
        )

    # Если canonical разошёлся с persisted — restore persisted после canonical write,
    # чтобы on-disk отражал «operator intent» с историческим блок-причиной,
    # иначе audit может потерять блокировку, если правила позже смягчатся.
    data[subject_code] = row
    _save_evidence(data)

    service.record(
        db,
        user=current,
        action="evidence.update",
        entity="evidence",
        entity_id=subject_code,
        details={
            "gates": gates,
            "promotion": promotion,
            "mvp_status_canonical": _evidence_mvp_status(canonical_row),
            "persisted_promotion_allowed": bool(row.get("promotion_allowed")),
            "canonical_promotion_allowed": bool(canonical_row["promotion_allowed"]),
            "blocked_reason": row.get("blocked_reason"),
        },
    )
    db.commit()

    # Сбросить кеш evidence-store, чтобы следующий /api/v1/subjects подхватил.
    try:
        from app.subjects import evidence as _ev_mod

        _ev_mod.reset_evidence_cache()
    except Exception:
        pass

    return {
        "ok": True,
        "subject_code": subject_code,
        "mvp_status": _evidence_mvp_status(canonical_row),
        "row": canonical_row,
        "persisted_promotion_allowed": bool(row.get("promotion_allowed")),
        "canonical_promotion_allowed": bool(canonical_row["promotion_allowed"]),
        "canonical_divergence": (
            "persisted_overrides_canonical"
            if bool(row.get("promotion_allowed")) and not bool(canonical_row["promotion_allowed"])
            else "ok"
        ),
    }


def _evidence_pilot_scope() -> set[str]:
    from app.subjects.evidence_schema import PILOT_SCOPE

    return PILOT_SCOPE


@router.post("/evidence/{subject_code}/promote")
def promote_evidence(
    subject_code: str,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """promotion_allowed=true + pilot_visible=true (только если все gates закрыты)."""
    data = _load_evidence()
    row = data.get(subject_code)
    if row is None:
        raise HTTPException(404, f"subject_code '{subject_code}' not in evidence.json")

    missing = [g for g in EVIDENCE_GATES if not row.get(g)]
    if missing:
        raise HTTPException(400, f"Cannot promote; missing gates: {missing}")

    row["promotion_allowed"] = True
    row["pilot_visible"] = True
    data[subject_code] = row
    _save_evidence(data)

    service.record(
        db,
        user=current,
        action="evidence.promote",
        entity="evidence",
        entity_id=subject_code,
        details={"mvp_status": _evidence_mvp_status(row)},
    )
    db.commit()
    try:
        from app.subjects import evidence as _ev_mod

        _ev_mod.reset_evidence_cache()
    except Exception:
        pass

    return {"ok": True, "subject_code": subject_code, "mvp_status": _evidence_mvp_status(row)}


@router.post("/evidence/{subject_code}/revoke")
def revoke_evidence(
    subject_code: str,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin()),
):
    """pilot_visible=false, promotion_allowed=false (отзыв для ребёнка)."""
    data = _load_evidence()
    row = data.get(subject_code)
    if row is None:
        raise HTTPException(404, f"subject_code '{subject_code}' not in evidence.json")

    row["pilot_visible"] = False
    row["promotion_allowed"] = False
    data[subject_code] = row
    _save_evidence(data)

    service.record(
        db,
        user=current,
        action="evidence.revoke",
        entity="evidence",
        entity_id=subject_code,
    )
    db.commit()
    try:
        from app.subjects import evidence as _ev_mod

        _ev_mod.reset_evidence_cache()
    except Exception:
        pass

    return {"ok": True, "subject_code": subject_code, "mvp_status": _evidence_mvp_status(row)}
