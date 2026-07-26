"""Роутер учебной структуры: список предметов, разделы, темы, материалы, задания.

Sprint 64: Redis caching для read-heavy endpoints (subjects/topics).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import (
    MATERIALS_TTL,
    SUBJECTS_TTL,
    TOPICS_TTL,
    TOPIC_TTL,
    cache_get,
    cache_set,
)
from app.db.session import get_db
from app.subjects import models, schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/subjects", tags=["subjects"])


@router.get("", response_model=list[schemas.SubjectOut])
def list_subjects(active_only: bool = True, db: Session = Depends(get_db)):
    # Sprint 64: cache (5 min TTL)
    cache_key = f"subjects:list:active={active_only}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    q = select(models.Subject).order_by(models.Subject.recommended_grade, models.Subject.name)
    if active_only:
        q = q.where(models.Subject.is_active.is_(True))
    results = db.scalars(q).all()

    # Cache as list of dicts (Pydantic serialization)
    results_dicts = [
        {
            "id": s.id,
            "code": s.code,
            "name": s.name,
            "description": getattr(s, "description", None),
            "recommended_grade": s.recommended_grade,
            "is_active": s.is_active,
        }
        for s in results
    ]
    cache_set(cache_key, results_dicts, ttl=SUBJECTS_TTL)
    return results


@router.get("/{subject_id}", response_model=schemas.SubjectOut)
def get_subject(subject_id: int, db: Session = Depends(get_db)):
    cache_key = f"subjects:id={subject_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    subj = db.get(models.Subject, subject_id)
    if subj is None:
        raise HTTPException(404, "Subject not found")
    return subj


@router.get("/{subject_id}/topics", response_model=list[schemas.TopicOut])
def list_subject_topics(subject_id: int, db: Session = Depends(get_db)):
    """Возвращает плоский список тем по всем разделам предмета (для навигации)."""
    # Sprint 64: cache
    cache_key = f"subjects:topics:subj={subject_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    rows = db.execute(
        select(models.Topic)
        .join(models.Section, models.Topic.section_id == models.Section.id)
        .where(models.Section.subject_id == subject_id)
        .order_by(models.Section.order_index, models.Topic.order_index)
    ).scalars().all()

    # Cache
    rows_dicts = [
        {
            "id": t.id,
            "section_id": t.section_id,
            "name": t.name,
            "description": getattr(t, "description", None),
            "order_index": t.order_index,
            "difficulty": getattr(t, "difficulty", None),
        }
        for t in rows
    ]
    cache_set(cache_key, rows_dicts, ttl=TOPICS_TTL)
    return rows


topics_router = APIRouter(prefix="/api/v1/topics", tags=["topics"])


@topics_router.get("/{topic_id}", response_model=schemas.TopicOut)
def get_topic(topic_id: int, db: Session = Depends(get_db)):
    cache_key = f"topics:id={topic_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    t = db.get(models.Topic, topic_id)
    if t is None:
        raise HTTPException(404, "Topic not found")
    return t


@topics_router.get("/{topic_id}/materials", response_model=list[schemas.MaterialOut])
def topic_materials(topic_id: int, db: Session = Depends(get_db)):
    # Sprint 64: cache (2 min TTL — materials могут меняться)
    cache_key = f"topics:materials:topic={topic_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    rows = db.scalars(
        select(models.LearningMaterial)
        .where(models.LearningMaterial.topic_id == topic_id)
        .order_by(models.LearningMaterial.id)
    ).all()

    rows_dicts = [
        {
            "id": m.id,
            "topic_id": m.topic_id,
            "title": m.title,
            "content": getattr(m, "content", None),
            "source_type": getattr(m, "source_type", None),
            "status": getattr(m, "status", None),
        }
        for m in rows
    ]
    cache_set(cache_key, rows_dicts, ttl=MATERIALS_TTL)
    return rows


@topics_router.get("/{topic_id}/questions", response_model=list[schemas.QuestionOut])
def topic_questions(topic_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(models.Question)
        .where(models.Question.topic_id == topic_id)
        .order_by(models.Question.difficulty, models.Question.id)
    ).all()
