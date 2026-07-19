"""Роутер прогресса."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
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


# === Sprint 8.2: рекомендация следующей темы ===
class NextTopicOut(BaseModel):
    """Sprint 8.2: рекомендация что делать дальше.

    Алгоритм:
    1. Если есть темы с mastery < 0.5 — повтори их (приоритет: самая слабая)
    2. Если все темы выше 0.5 — следующая тема в curriculum (по order_index)
    3. Если всё mastered — поздравление + мотивация
    """
    topic_id: int | None
    topic_name: str | None
    subject_id: int | None
    subject_name: str | None
    reason: str  # "weak_topic" | "next_in_curriculum" | "all_mastered"
    mastery_score: float | None  # текущий mastery (для слабых тем)
    encouragement: str


_NEXT_TOPIC_ENCOURAGEMENTS = [
    "Готов попробовать что-то новое? 🚀",
    "Ты справишься! 💪",
    "Давай посмотрим что дальше? 📚",
    "Следующая тема ждёт! ✨",
]


@router.get("/recommend-next", response_model=NextTopicOut)
def recommend_next(
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    """Sprint 8.2: рекомендация следующей темы (adaptive curriculum)."""
    import random

    from app.subjects import models as subj_models
    from app.progress import models as prog_models

    # 1. Сначала ищем слабые темы (< 0.5 mastery и хоть какие-то attempts)
    progress = db.execute(
        select(prog_models.Progress).where(prog_models.Progress.user_id == current.id)
    ).scalars().all()

    weak = [p for p in progress if 0 < p.mastery_score < 0.5]
    if weak:
        weakest = min(weak, key=lambda p: p.mastery_score)
        topic = db.get(subj_models.Topic, weakest.topic_id)
        if topic:
            subject = topic.section.subject
            return NextTopicOut(
                topic_id=topic.id,
                topic_name=topic.name,
                subject_id=subject.id,
                subject_name=subject.name,
                reason="weak_topic",
                mastery_score=weakest.mastery_score,
                encouragement=f"Повтори эту тему — всего {weakest.mastery_score * 100:.0f}% освоения. С фокусом обязательно получится! 💪",
            )

    # 2. Ищем тему, которая ещё не пройдена (mastery < 0.5 или нет attempts)
    all_topics = db.execute(
        select(subj_models.Topic).order_by(subj_models.Topic.section_id, subj_models.Topic.order_index)
    ).scalars().all()

    progress_by_topic = {p.topic_id: p for p in progress}
    seen_section_ids = set()

    for topic in all_topics:
        p = progress_by_topic.get(topic.id)
        # Нет attempts — следующая не пройденная
        if p is None or p.attempts_count == 0:
            # Пропускаем уже сделанные темы из этого section
            subject = topic.section.subject
            return NextTopicOut(
                topic_id=topic.id,
                topic_name=topic.name,
                subject_id=subject.id,
                subject_name=subject.name,
                reason="next_in_curriculum",
                mastery_score=None,
                encouragement=random.choice(_NEXT_TOPIC_ENCOURAGEMENTS),
            )

    # 3. Всё mastered!
    return NextTopicOut(
        topic_id=None,
        topic_name=None,
        subject_id=None,
        subject_name=None,
        reason="all_mastered",
        mastery_score=None,
        encouragement="🎉 Невероятно! Ты освоил(а) все доступные темы. Давай обсудим с родителем или учителем что изучать дальше!",
    )


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
    """Pilot Core Stage 1 — P1.2.1 + P1.2.5.

    P1.2.1: server-owned truth — `is_correct` и `score` вычисляются в
    `_server_validate_attempt` (см. progress/service.py). Client-supplied
    `is_correct=True, score=1.0` принимается ТОЛЬКО если она согласована
    с server-trusted exact match. Иначе — server-trust выигрывает.

    P1.2.5: legacy v1 endpoint остаётся работоспособным для совместимости
    с фронтом (миграция на /api/v2/exercises/{id}/answer в следующем этапе).
    Student-410 (как предлагалось ранее) отложен до стабилизации фронта.
    """
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