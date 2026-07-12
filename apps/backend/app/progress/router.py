"""Роутер прогресса."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.db.session import get_db
from app.progress import models, schemas, service
from app.users import models as user_models

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])


@router.get("", response_model=list[schemas.ProgressOut])
def my_progress(
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    return service.get_user_progress(db, current.id)


@router.get("/subjects/{subject_id}", response_model=list[schemas.TopicProgress])
def subject_progress(
    subject_id: int,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    return service.get_subject_progress(db, current.id, subject_id)


@router.get("/recommend-review", response_model=list[schemas.TopicProgress])
def recommend_review(
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    """Темы, которые стоит повторить (низкий mastery)."""
    return service.recommend_review(db, current.id)


@router.get("/mistakes", response_model=list[schemas.MistakeOut])
def my_mistakes(
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    return service.get_user_mistakes(db, current.id)


@router.post("/attempts", response_model=schemas.AttemptOut)
def record_attempt(
    payload: schemas.AttemptCreate,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    return service.record_attempt(db, current.id, payload)


# === Sprint 2.2: Spaced Repetition ===

@router.get("/due-for-review", response_model=list[schemas.ReviewItem])
def due_for_review(
    limit: int = 20,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    """Темы, которые нужно повторить сегодня (по SM-2).

    days_overdue > 0 — просрочено
    days_overdue = 0 — сегодня
    days_overdue < 0 — ещё рано (тоже включаем в выдачу)
    """
    return service.due_for_review(db, current.id, min(limit, 50))


@router.post("/review-result")
def review_result(
    payload: schemas.ReviewResultIn,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    """Отметить тему как повторённую, пересчитать SM-2 schedule.

    Возвращает обновлённый Progress.
    """
    from app.progress.schemas import ProgressOut

    prog = service.schedule_topic_for_review(
        db,
        current.id,
        payload.topic_id,
        quality=payload.quality,
        is_correct=payload.is_correct,
        hint_used=payload.hint_used,
    )
    return ProgressOut.model_validate(prog)