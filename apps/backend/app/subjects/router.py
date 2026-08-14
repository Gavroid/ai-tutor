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


MVP_READY_SUBJECT_KEYWORDS = ("математика", "6 класс", "повтор")


def _subject_support(subject: models.Subject) -> dict[str, object]:
    normalized = f"{subject.name} {subject.description or ''}".lower()
    ready = all(word in normalized for word in MVP_READY_SUBJECT_KEYWORDS)
    if ready:
        return {
            "mvp_status": "mvp_ready",
            "support_note": "MVP-ready: объяснения, практика и проверенные источники доступны для ручного тестирования.",
            "rag_ready": True,
            "practice_ready": True,
        }
    return {
        "mvp_status": "preview",
        "support_note": "Preview: учебный маршрут виден, но материалы/RAG ещё не подтверждены. Используй для навигации, не для пилотного теста.",
        "rag_ready": False,
        "practice_ready": False,
    }


def _subject_out(subject: models.Subject) -> dict[str, object]:
    base = schemas.SubjectOut.model_validate(subject).model_dump()
    base.update(_subject_support(subject))
    return base


router = APIRouter(prefix="/api/v1/subjects", tags=["subjects"])


@router.get("", response_model=list[schemas.SubjectOut])
def list_subjects(active_only: bool = True, db: Session = Depends(get_db)):
    # Sprint 64: cache (5 min TTL)
    cache_key = f"subjects:v2:list:active={active_only}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached  # list of Pydantic-compatible dicts

    q = select(models.Subject).order_by(models.Subject.recommended_grade, models.Subject.name)
    if active_only:
        q = q.where(models.Subject.is_active.is_(True))
    results = db.scalars(q).all()

    # Cache as Pydantic dicts (полная схема через model_dump)
    results_dicts = [_subject_out(s) for s in results]
    cache_set(cache_key, results_dicts, ttl=SUBJECTS_TTL)
    return results_dicts


@router.get("/{subject_id}", response_model=schemas.SubjectOut)
def get_subject(subject_id: int, db: Session = Depends(get_db)):
    cache_key = f"subjects:v2:id={subject_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    subj = db.get(models.Subject, subject_id)
    if subj is None:
        raise HTTPException(404, "Subject not found")
    result = _subject_out(subj)
    cache_set(cache_key, result, ttl=SUBJECTS_TTL)
    return result


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

    # Cache as Pydantic dicts (полная схема)
    rows_dicts = [schemas.TopicOut.model_validate(t).model_dump() for t in rows]
    cache_set(cache_key, rows_dicts, ttl=TOPICS_TTL)
    return rows


@router.get("/{subject_id}/route-plan", response_model=list[schemas.MathTopicPlanOut])
def subject_route_plan(subject_id: int):
    """Student-friendly route map.

    Math is MVP-ready. Algebra and Geometry are exposed as preview routes;
    they must remain preview until source/RAG and fallback coverage are complete.
    """
    from app.algebra_plan import ALGEBRA_SUBJECT_ID, ALGEBRA_TOPIC_PLAN, next_algebra_topic_after
    from app.geometry_plan import GEOMETRY_SUBJECT_ID, GEOMETRY_TOPIC_PLAN, next_geometry_topic_after
    from app.math_plan import MATH_SUBJECT_ID, MATH_TOPIC_PLAN, next_topic_after

    if subject_id == MATH_SUBJECT_ID:
        return [
            schemas.MathTopicPlanOut(
                topic_id=row.topic_id,
                order=row.order,
                section=row.section,
                tier=row.tier,
                focus=row.focus,
                checkpoint=row.checkpoint,
                next_topic_id=next_topic_after(row.topic_id),
            )
            for row in MATH_TOPIC_PLAN
        ]
    if subject_id == ALGEBRA_SUBJECT_ID:
        return [
            schemas.MathTopicPlanOut(
                topic_id=row.topic_id,
                order=row.order,
                section=row.section,
                tier=row.tier,
                focus=row.focus,
                checkpoint=row.checkpoint,
                next_topic_id=next_algebra_topic_after(row.topic_id),
            )
            for row in ALGEBRA_TOPIC_PLAN
        ]
    if subject_id == GEOMETRY_SUBJECT_ID:
        return [
            schemas.MathTopicPlanOut(
                topic_id=row.topic_id,
                order=row.order,
                section=row.section,
                tier=row.tier,
                focus=row.focus,
                checkpoint=row.checkpoint,
                next_topic_id=next_geometry_topic_after(row.topic_id),
            )
            for row in GEOMETRY_TOPIC_PLAN
        ]
    return []


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


def _followups_for_topic(topic: models.Topic) -> list[schemas.TopicFollowupOut]:
    name = topic.name.lower()
    if "среднее арифметическое" in name:
        return [
            schemas.TopicFollowupOut(label="Среднее чисел", prompt="Объясни подробнее среднее арифметическое обычных чисел на новом примере.", kind="choice", order_index=1),
            schemas.TopicFollowupOut(label="Средняя скорость", prompt="Объясни среднюю скорость как отдельный тип задач, с простым примером.", kind="choice", order_index=2),
            schemas.TopicFollowupOut(label="Средний вес", prompt="Объясни средний вес как отдельный тип задач, с простым примером.", kind="choice", order_index=3),
        ]
    if "наибольш" in name and "делител" in name:
        return [
            schemas.TopicFollowupOut(label="Попробовать самому", prompt="Дай мне похожую задачу на НОД и взаимно простые числа, но не показывай ответ сразу.", kind="choice", order_index=1),
            schemas.TopicFollowupOut(label="Второй способ", prompt="Покажи второй способ нахождения НОД через разложение на простые множители.", kind="choice", order_index=2),
        ]
    if "уравнен" in name:
        return [
            schemas.TopicFollowupOut(label="Далее", prompt="Продолжи объяснение темы по следующему шагу: как переносить слагаемые в уравнении и менять знак.", kind="next", order_index=1),
        ]
    return []


def _followup_count_for_topic(topic: models.Topic) -> int:
    return len(_followups_for_topic(topic))


@topics_router.get("/{topic_id}/followups", response_model=list[schemas.TopicFollowupOut])
def topic_followups(topic_id: int, db: Session = Depends(get_db)):
    topic = db.get(models.Topic, topic_id)
    if topic is None:
        raise HTTPException(404, "Topic not found")
    from app.teacher import content_registry

    return [schemas.TopicFollowupOut(**row) for row in content_registry.get_followups(topic)]


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

    # Cache as Pydantic dicts
    rows_dicts = [schemas.MaterialOut.model_validate(m).model_dump() for m in rows]
    cache_set(cache_key, rows_dicts, ttl=MATERIALS_TTL)
    return rows


@topics_router.get("/{topic_id}/questions", response_model=list[schemas.QuestionOut])
def topic_questions(topic_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(models.Question)
        .where(models.Question.topic_id == topic_id)
        .order_by(models.Question.difficulty, models.Question.id)
    ).all()
