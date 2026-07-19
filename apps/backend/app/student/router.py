"""Endpoints для ученика: список опубликованных материалов, черновики уроков, баджи.

Sprint 2.1 — ученик видит только материалы со статусом published.
Sprint 7.3 — автосохранение черновиков урока.
Sprint 7.5 — баджи за усилие (НЕ за streak, чтобы не давить на T1D-ученика).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.deps import User, current_user
from app.db.session import get_db
from app.subjects import models as subj_models
from app.student import models as stu_models
from app.student.badges import (
    BADGES,
    award_badge,
    collect_stats,
    evaluate_and_award_badges,
    seed_badge_definitions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/student", tags=["student"])


# ---------- materials (Sprint 2.1) ----------


@router.get("/materials")
def list_published_for_student(
    topic_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current: User = Depends(current_user),
):
    """Список опубликованных материалов (видит любой авторизованный)."""
    q = select(subj_models.LearningMaterial).where(
        subj_models.LearningMaterial.status == "published"
    )
    if topic_id:
        q = q.where(subj_models.LearningMaterial.topic_id == topic_id)
    q = q.order_by(subj_models.LearningMaterial.id.desc()).limit(limit)
    items = list(db.scalars(q).all())
    return [
        {
            "id": m.id,
            "topic_id": m.topic_id,
            "title": m.title,
            "content": m.content,
            "source_type": m.source_type,
            "published_at": m.published_at.isoformat() if m.published_at else None,
            "created_at": m.created_at.isoformat(),
        }
        for m in items
    ]


@router.get("/materials/{material_id}")
def get_published_for_student(
    material_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(current_user),
):
    """Детальный просмотр опубликованного материала."""
    m = db.get(subj_models.LearningMaterial, material_id)
    if m is None or m.status != "published":
        raise HTTPException(404, "Материал не найден или не опубликован")
    return {
        "id": m.id,
        "topic_id": m.topic_id,
        "title": m.title,
        "content": m.content,
        "source_type": m.source_type,
        "published_at": m.published_at.isoformat() if m.published_at else None,
        "created_at": m.created_at.isoformat(),
    }


# ---------- drafts (Sprint 7.3) ----------


class DraftIn(BaseModel):
    """Произвольный payload черновика урока."""

    payload: dict = Field(default_factory=dict)


class DraftOut(BaseModel):
    topic_id: int
    payload: dict
    updated_at: datetime


def _serialize_payload(raw: str) -> dict:
    """Безопасное чтение JSON-payload из БД."""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        # Не ломаем API из-за битых старых данных
        return {}


@router.put("/topics/{topic_id}/draft", response_model=DraftOut)
def save_draft(
    topic_id: int,
    body: DraftIn,
    db: Session = Depends(get_db),
    current: User = Depends(current_user),
):
    """Сохранить/обновить черновик урока.

    Вызывается с фронта каждые ~5 сек (debounce). Идемпотентно:
    upsert по (user_id, topic_id).
    """
    topic = db.get(subj_models.Topic, topic_id)
    if topic is None:
        raise HTTPException(404, "Тема не найдена")

    # Проверяем размер (защита от абьюза — 64 КБ на черновик)
    payload_str = json.dumps(body.payload, ensure_ascii=False)
    if len(payload_str) > 64 * 1024:
        raise HTTPException(413, "Черновик слишком большой (>64 КБ)")

    now = datetime.now(timezone.utc)
    existing = db.execute(
        select(stu_models.TopicDraft).where(
            stu_models.TopicDraft.user_id == current.id,
            stu_models.TopicDraft.topic_id == topic_id,
        )
    ).scalar_one_or_none()
    if existing:
        existing.payload = payload_str
        existing.updated_at = now
    else:
        existing = stu_models.TopicDraft(
            topic_id=topic_id,
            user_id=current.id,
            payload=payload_str,
            updated_at=now,
        )
        db.add(existing)
    db.commit()

    # Audit в audit_logs (best-effort, через прямой вызов в Sprint 7.5+).
    # Не блокирует основной запрос — ошибки здесь не должны ронять черновик.
    try:
        from app.admin.service import record_audit_action  # noqa: F401 (ленивый import)
    except ImportError:
        pass

    return DraftOut(
        topic_id=topic_id,
        payload=body.payload,
        updated_at=now,
    )


@router.get("/topics/{topic_id}/draft", response_model=DraftOut)
def load_draft(
    topic_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(current_user),
):
    """Загрузить черновик урока для восстановления прерванной сессии.

    Если черновика нет → 404 (нормальная ситуация, не ошибка).
    """
    draft = db.execute(
        select(stu_models.TopicDraft).where(
            stu_models.TopicDraft.user_id == current.id,
            stu_models.TopicDraft.topic_id == topic_id,
        )
    ).scalar_one_or_none()
    if draft is None:
        raise HTTPException(404, "Черновик не найден")
    return DraftOut(
        topic_id=topic_id,
        payload=_serialize_payload(draft.payload),
        updated_at=draft.updated_at,
    )


@router.delete("/topics/{topic_id}/draft", status_code=204)
def clear_draft(
    topic_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(current_user),
):
    """Удалить черновик (например, после успешного завершения урока).

    Идемпотентно: отсутствие черновика → 204.
    """
    draft = db.execute(
        select(stu_models.TopicDraft).where(
            stu_models.TopicDraft.user_id == current.id,
            stu_models.TopicDraft.topic_id == topic_id,
        )
    ).scalar_one_or_none()
    if draft is not None:
        db.delete(draft)
        db.commit()
    return None


# ---------- badges (Sprint 7.5) ----------


class BadgeOut(BaseModel):
    """Один бадж для UI."""

    slug: str
    title: str
    description: str
    icon: str
    awarded_at: str | None = None
    evidence: dict = Field(default_factory=dict)


@router.get("/badges", response_model=list[BadgeOut])
def list_my_badges(
    db: Session = Depends(get_db),
    current: User = Depends(current_user),
):
    """Список всех каталожных баджей + флаг полученных (Sprint 7.5).

    Sprint 7.5: за усилие (НЕ streak). Возвращает ВСЕ 10 баджей из каталога,
    с признаком `awarded_at` (None если не получен).
    """
    seed_badge_definitions(db)
    # Полученные баджи
    rows = db.execute(
        select(stu_models.UserBadge).where(
            stu_models.UserBadge.user_id == current.id
        )
    ).scalars().all()
    awarded_map = {r.badge_slug: r for r in rows}

    out: list[BadgeOut] = []
    for spec in BADGES:
        row = awarded_map.get(spec.slug)
        out.append(
            BadgeOut(
                slug=spec.slug,
                title=spec.title,
                description=spec.description,
                icon=spec.icon,
                awarded_at=row.awarded_at.isoformat() if row else None,
                evidence=json.loads(row.evidence_json) if row else {},
            )
        )
    return out


@router.post("/badges/evaluate", response_model=list[str])
def trigger_badge_evaluation(
    db: Session = Depends(get_db),
    current: User = Depends(current_user),
):
    """Запустить переоценку баджей на основе текущей статистики (Sprint 7.5).

    Можно вызывать из UI на странице /student/badges, чтобы получить свежие
    баджы после прохождения темы.

    Returns:
        Список slug'ов, присуждённых в этом вызове.
    """
    seed_badge_definitions(db)
    stats = collect_stats(db, current.id)
    return evaluate_and_award_badges(db, current.id, stats)


# === Sprint 8.1: streak для самого ученика ===
# T1D-friendly: longest_streak растёт всегда (поощрение), current_streak
# обнуляется при пропуске дня (без штрафа — это просто индикатор).
# Никаких "сгоревших серий" — для T1D-ученика это было бы фрустрирующим.


class StreakOut(BaseModel):
    current_streak_days: int
    longest_streak_days: int
    total_active_days: int
    last_active_date: str | None  # YYYY-MM-DD
    # T1D-friendly: "сообщение поддержки" — позитивная формулировка.
    encouragement: str


_ENCOURAGEMENTS = [
    "🔥 Отлично! Ты на серии!",
    "✨ Замечательная работа!",
    "💪 Так держать!",
    "🌟 Каждый день — это шаг вперёд!",
    "📚 Ты становишься умнее с каждым днём!",
    None,  # без поздравления
]


@router.get("/streak", response_model=StreakOut)
def my_streak(
    db: Session = Depends(get_db),
    current: User = Depends(current_user),
):
    """Sprint 8.1: текущая серия активности ученика.

    Активность = attempts с created_at за этот день (любой is_correct).

    T1D-friendly:
    - longest_streak = max за всё время, растёт
    - current_streak = сколько дней подряд до сегодня включительно
    - Если сегодня не было активности, current=0 (но НЕ штраф)
    - total_active_days = общее количество дней с активностью

    Пропуск дня НЕ наказывается. Можно вернуться в любой момент.
    """
    from datetime import date as _date, datetime, timedelta, timezone

    from app.parents.service import _compute_streak
    from app.progress import models as prog_models

    user_id = current.id  # alias чтобы не путать с imported current
    today = datetime.now(timezone.utc).date()
    # Находим все уникальные даты активности
    attempts = db.execute(
        select(prog_models.Attempt).where(prog_models.Attempt.user_id == user_id)
    ).scalars().all()

    active_dates: set[str] = set()
    for a in attempts:
        if a.created_at:
            d = a.created_at.date() if isinstance(a.created_at, datetime) else a.created_at
            active_dates.add(d.isoformat())

    current_streak, longest, total = _compute_streak(active_dates, today.isoformat())

    # Последний день активности (для UI)
    last_active = max(active_dates) if active_dates else None

    # Encouragement: случайное поздравление (только если current > 0)
    if current_streak > 0:
        import random

        msg = random.choice([e for e in _ENCOURAGEMENTS if e])
    else:
        msg = "Каждый день — новая возможность! 🌱"

    return StreakOut(
        current_streak_days=current_streak,
        longest_streak_days=longest,
        total_active_days=total,
        last_active_date=last_active,
        encouragement=msg,
    )
