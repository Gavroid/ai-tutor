"""Роутер учебной структуры: список предметов, разделы, темы, материалы, задания.

Sprint 64: Redis caching для read-heavy endpoints (subjects/topics).
Sprint 2026-08-22: fail-closed readiness policy. mvp_status вычисляется из
явного evidence-store (см. app.subjects.evidence), а не из counts/route/seed.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
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
from app.rag_models import RagChunk
from app.subjects import models, schemas
from app.subjects.evidence import (
    SubjectEvidence,
    evidence_to_dict,
    get_evidence_for,
)

logger = logging.getLogger(__name__)


def _route_topic_ids(subject: models.Subject) -> set[int]:
    if subject.code == "math":
        from app.math_plan import MATH_TOPIC_PLAN

        return {row.topic_id for row in MATH_TOPIC_PLAN}
    if subject.code == "algebra":
        from app.algebra_plan import ALGEBRA_TOPIC_PLAN

        return {row.topic_id for row in ALGEBRA_TOPIC_PLAN}
    if subject.code == "geom":
        from app.geometry_plan import GEOMETRY_TOPIC_PLAN

        return {row.topic_id for row in GEOMETRY_TOPIC_PLAN}
    return {topic.id for section in subject.sections for topic in section.topics}


def _subject_coverage(db: Session, subject: models.Subject) -> dict[str, object]:
    """Diagnostic counts (read-only).

    Возвращает coverage fields для UI diagnostics (route_topic_count, source_topic_count,
    practice_topic_count, route_ready). Эти поля НЕ участвуют в вычислении
    mvp_status — это только счётчики, чтобы оператор видел состояние.
    """
    topic_ids = [topic.id for section in subject.sections for topic in section.topics]
    route_topic_ids = _route_topic_ids(subject)
    if not topic_ids:
        return {
            "route_ready": False,
            "topic_count": 0,
            "route_topic_count": 0,
            "source_topic_count": 0,
            "practice_topic_count": 0,
        }

    source_topic_ids = set(
        db.execute(
            select(models.LearningMaterial.topic_id)
            .join(RagChunk, RagChunk.material_id == models.LearningMaterial.id)
            .where(models.LearningMaterial.topic_id.in_(topic_ids))
            .group_by(models.LearningMaterial.topic_id)
            .having(func.count(RagChunk.id) > 0)
        ).scalars().all()
    )

    from app.teacher import content_registry

    practice_topic_ids = {topic_id for topic_id in topic_ids if content_registry.get_fallbacks(topic_id)}
    return {
        "route_ready": bool(route_topic_ids) and len(route_topic_ids) == len(topic_ids),
        "topic_count": len(topic_ids),
        "route_topic_count": len(route_topic_ids),
        "source_topic_count": len(source_topic_ids),
        "practice_topic_count": len(practice_topic_ids),
    }


def _subject_out(subject: models.Subject, db: Session) -> dict[str, object]:
    """Compose SubjectOut: явный evidence + diagnostic counts.

    Pipeline:
    1. Читаем явный evidence из evidence-store (manifest/mapping/import/rag/
       practice/manual_smoke/pilot/promotion).
    2. Считаем mvp_status fail-closed (mvp_ready только при promotion_allowed
       и всех evidence_ready=true).
    3. Считаем diagnostic counts (route/source/practice) — они НЕ участвуют в
       mvp_status, только для operator UI.
    """
    base = schemas.SubjectOut.model_validate(subject).model_dump()

    # 1) Явный evidence (fail-closed).
    evidence = get_evidence_for(subject.code)
    base.update(evidence_to_dict(evidence))

    # 2) mvp_status computed from evidence only.
    # Promotion policy is stricter than raw evidence: only the controlled
    # Math-6 pilot may be mvp_ready/pilot-visible at this stage.
    status = evidence.mvp_status()
    if subject.code != "math" and status == "mvp_ready":
        status = "internal_mvp"
    base["mvp_status"] = status
    base["support_note"] = (
        evidence.support_note()
        if status == evidence.mvp_status()
        else "Внутренний MVP: evidence есть, но предмет не включён в текущий Math-6 pilot."
    )

    # 3) Diagnostic counts (не участвуют в mvp_status).
    coverage = _subject_coverage(db, subject)
    base.update(coverage)
    return base


router = APIRouter(prefix="/api/v1/subjects", tags=["subjects"])


@router.get("", response_model=list[schemas.SubjectOut])
def list_subjects(active_only: bool = True, db: Session = Depends(get_db)):
    # Sprint 64: cache (5 min TTL)
    cache_key = f"subjects:v3:list:active={active_only}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached  # list of Pydantic-compatible dicts

    q = select(models.Subject).order_by(models.Subject.recommended_grade, models.Subject.name)
    if active_only:
        q = q.where(models.Subject.is_active.is_(True))
    results = db.scalars(q).all()

    # Cache as Pydantic dicts (полная схема через model_dump)
    results_dicts = [_subject_out(s, db) for s in results]
    cache_set(cache_key, results_dicts, ttl=SUBJECTS_TTL)
    return results_dicts


@router.get("/{subject_id}", response_model=schemas.SubjectOut)
def get_subject(subject_id: int, db: Session = Depends(get_db)):
    cache_key = f"subjects:v3:id={subject_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    subj = db.get(models.Subject, subject_id)
    if subj is None:
        raise HTTPException(404, "Subject not found")
    result = _subject_out(subj, db)
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
def subject_route_plan(subject_id: int, db: Session = Depends(get_db)):
    """Student-friendly route map for every seeded subject."""
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
    rows = db.execute(
        select(models.Topic, models.Section)
        .join(models.Section, models.Topic.section_id == models.Section.id)
        .where(models.Section.subject_id == subject_id)
        .order_by(models.Section.order_index, models.Topic.order_index)
    ).all()
    return [
        schemas.MathTopicPlanOut(
            topic_id=topic.id,
            order=idx,
            section=section.name,
            tier="base" if topic.difficulty <= 2 else "medium" if topic.difficulty == 3 else "hard",
            focus=topic.name,
            checkpoint=topic.difficulty >= 4,
            next_topic_id=rows[idx][0].id if idx < len(rows) else None,
        )
        for idx, (topic, section) in enumerate(rows, start=1)
    ]


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
