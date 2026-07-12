"""Роутер учебной структуры: список предметов, разделы, темы, материалы, задания."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.subjects import models, schemas

router = APIRouter(prefix="/api/v1/subjects", tags=["subjects"])


@router.get("", response_model=list[schemas.SubjectOut])
def list_subjects(active_only: bool = True, db: Session = Depends(get_db)):
    q = select(models.Subject).order_by(models.Subject.recommended_grade, models.Subject.name)
    if active_only:
        q = q.where(models.Subject.is_active.is_(True))
    return db.scalars(q).all()


@router.get("/{subject_id}", response_model=schemas.SubjectOut)
def get_subject(subject_id: int, db: Session = Depends(get_db)):
    subj = db.get(models.Subject, subject_id)
    if subj is None:
        raise HTTPException(404, "Subject not found")
    return subj


@router.get("/{subject_id}/topics", response_model=list[schemas.TopicOut])
def list_subject_topics(subject_id: int, db: Session = Depends(get_db)):
    """Возвращает плоский список тем по всем разделам предмета (для навигации)."""
    rows = db.execute(
        select(models.Topic)
        .join(models.Section, models.Topic.section_id == models.Section.id)
        .where(models.Section.subject_id == subject_id)
        .order_by(models.Section.order_index, models.Topic.order_index)
    ).scalars().all()
    return rows


topics_router = APIRouter(prefix="/api/v1/topics", tags=["topics"])


@topics_router.get("/{topic_id}", response_model=schemas.TopicOut)
def get_topic(topic_id: int, db: Session = Depends(get_db)):
    t = db.get(models.Topic, topic_id)
    if t is None:
        raise HTTPException(404, "Topic not found")
    return t


@topics_router.get("/{topic_id}/materials", response_model=list[schemas.MaterialOut])
def topic_materials(topic_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(models.LearningMaterial)
        .where(models.LearningMaterial.topic_id == topic_id)
        .order_by(models.LearningMaterial.id)
    ).all()


@topics_router.get("/{topic_id}/questions", response_model=list[schemas.QuestionOut])
def topic_questions(topic_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(models.Question)
        .where(models.Question.topic_id == topic_id)
        .order_by(models.Question.difficulty, models.Question.id)
    ).all()