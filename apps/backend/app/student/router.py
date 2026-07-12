"""Endpoints для ученика: список опубликованных материалов по теме.

Sprint 2.1 — ученик видит только материалы со статусом published.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.deps import User, current_user
from app.db.session import get_db
from app.subjects import models as subj_models

router = APIRouter(prefix="/api/v1/student/materials", tags=["student"])


@router.get("")
def list_published_for_student(
    topic_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current: User = Depends(current_user),
):
    """Список опубликованных материалов (видит любой авторизованный).

    Используется учеником в UI урока.
    """
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
            "content": m.content,  # JSON-строка с полной структурой
            "source_type": m.source_type,
            "published_at": m.published_at.isoformat() if m.published_at else None,
            "created_at": m.created_at.isoformat(),
        }
        for m in items
    ]


@router.get("/{material_id}")
def get_published_for_student(
    material_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(current_user),
):
    """Детальный просмотр опубликованного материала (только published)."""
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
