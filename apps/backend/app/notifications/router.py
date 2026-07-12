"""Роутер уведомлений."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.db.session import get_db
from app.notifications import schemas, service
from app.users import models as user_models

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("", response_model=list[schemas.NotificationOut])
def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    return service.list_user_notifications(db, current.id, unread_only, min(limit, 200))


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    ok = service.mark_as_read(db, current.id, notification_id)
    if not ok:
        raise HTTPException(404, "Уведомление не найдено")
    return {"ok": True}


@router.post("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    """Пометить все свои уведомления как прочитанные."""
    from app.notifications import models as n_models
    from sqlalchemy import update

    db.execute(
        update(n_models.Notification)
        .where(
            n_models.Notification.user_id == current.id,
            n_models.Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    db.commit()
    return {"ok": True}