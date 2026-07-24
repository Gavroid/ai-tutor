"""Sprint 34 — Session pause router.

T1D-friendly safety: записывает pause events от ребёнка.
НЕ отправляет в Telegram автоматически.
НЕ интерпретирует glucose data.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.common.deps import User, get_current_user
from app.db.session import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


PauseReason = Literal["break", "hypo", "hyper", "other"]


class PauseIn(BaseModel):
    """Sprint 34: pause event."""
    reason: PauseReason = Field(description="break | hypo | hyper | other")
    topic_id: int | None = Field(default=None)


class PauseOut(BaseModel):
    """Sprint 34: pause response."""
    id: int
    started_at: str
    reason: str


class ResumeOut(BaseModel):
    """Sprint 34: resume response."""
    paused_seconds: int
    reason: str


@router.post("/pause", response_model=PauseOut, status_code=201)
def create_pause(
    payload: PauseIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Sprint 34: записать session pause для current user.

    - reason: break (отойду) | hypo (низкий сахар) | hyper (высокий) | other
    - topic_id: optional, какой topic был активен.
    - Streak НЕ ломается (T1D-friendly).

    Sprint 34 fix: используем ORM (Session) вместо raw SQL — работает
    с in-memory SQLite.
    """
    from app.sessions.models import SessionPause

    pause = SessionPause(
        user_id=current.id,
        topic_id=payload.topic_id,
        reason=payload.reason,
    )
    db.add(pause)
    db.commit()
    db.refresh(pause)

    return PauseOut(
        id=pause.id,
        started_at=pause.started_at.isoformat() if pause.started_at else "",
        reason=pause.reason,
    )


@router.post("/resume", response_model=ResumeOut)
def resume_pause(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Sprint 34: возобновить последнюю незавершённую pause.

    Возвращает paused_seconds (для UI "Ты был на паузе X мин").

    Sprint 34 fix: ORM вместо raw SQL.
    """
    from app.sessions.models import SessionPause

    pause = (
        db.query(SessionPause)
        .filter(SessionPause.user_id == current.id, SessionPause.ended_at.is_(None))
        .order_by(SessionPause.started_at.desc())
        .first()
    )
    if pause is None:
        raise HTTPException(404, "No active pause")

    pause.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pause)

    started, ended = pause.started_at, pause.ended_at
    paused_seconds = int((ended - started).total_seconds())

    return ResumeOut(
        paused_seconds=paused_seconds,
        reason=pause.reason,
    )


@router.get("/pauses/recent", response_model=list[PauseOut])
def list_recent_pauses(
    limit: int = 20,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Sprint 34: последние pauses (для parent dashboard)."""
    if limit < 1 or limit > 100:
        raise HTTPException(400, "limit must be 1..100")

    from app.sessions.models import SessionPause

    pauses = (
        db.query(SessionPause)
        .filter(SessionPause.user_id == current.id)
        .order_by(SessionPause.started_at.desc())
        .limit(limit)
        .all()
    )

    return [
        PauseOut(
            id=p.id,
            started_at=p.started_at.isoformat() if p.started_at else "",
            reason=p.reason,
        )
        for p in pauses
    ]


# Local imports для type hints
from fastapi import Depends as _Depends  # noqa: E402

def get_db():
    """Пустая функция — реальная session через SessionLocal."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()