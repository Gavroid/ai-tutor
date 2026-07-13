"""Pilot Core Stage 1 — Phase 2 (P1.2.3, P1.2.4): server-owned exercise endpoints.

POST /api/v2/exercises/generate
  - принимает { topic_id, difficulty? }
  - создаёт GeneratedExerciseInstance в БД
  - возвращает safe projection (НЕ содержит correct_answer/explanation)
  - opaque `exercise_id` (int)

POST /api/v2/exercises/{exercise_id}/answer
  - принимает { user_answer } (только идентификатор задания + ответ ученика)
  - загружает truth из БД, проверяет owner/expiry/state
  - в одной транзакции: пишет attempt и обновляет progress
  - идемпотентно: повтор submit НЕ создаёт второй attempt
  - expired exercise_id → 410
  - чужой exercise_id → 404
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.models import GeneratedExerciseInstance
from app.ai.service import get_ai_service
from app.auth.security import get_current_user
from app.db.session import get_db
from app.progress import models as progress_models
from app.subjects import models as subj_models
from app.users.models import Role, User


router = APIRouter(prefix="/api/v2/exercises", tags=["v2-exercises"])


class GenerateIn(BaseModel):
    topic_id: int
    difficulty: int = Field(default=2, ge=1, le=5)


class GenerateOut(BaseModel):
    exercise_id: int
    question_text: str
    type: str
    options: list[str] | None
    difficulty: int
    expires_at: str


class AnswerIn(BaseModel):
    user_answer: str = Field(min_length=1, max_length=4000)


class AnswerOut(BaseModel):
    exercise_id: int
    is_correct: bool
    score: float
    feedback: str
    explanation: str


@router.post("/generate", response_model=GenerateOut)
async def generate_exercise(
    payload: GenerateIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """P1.2.3: server-owned generation. Возвращает safe projection + opaque id.

    Только для student/parent/teacher (admin — для отладки). Генерирует
    упражнение через существующий AIService, сохраняет в БД вместе с
    server-side truth (correct_answer), и возвращает safe dict без него.
    """
    if current.role not in (Role.STUDENT, Role.PARENT, Role.TEACHER, Role.ADMIN):
        raise HTTPException(status_code=403, detail="Role not allowed to generate exercises")

    topic = db.get(subj_models.Topic, payload.topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Переиспользуем существующий AI-сервис. Он уже возвращает correct_answer
    # в GeneratedExercise — мы НЕ отдаём его в ответе, а сохраняем в БД.
    svc = get_ai_service()
    gen = await svc.generate_exercise(
        subject_name=topic.section.subject.name,
        topic_name=topic.name,
        difficulty=payload.difficulty,
    )
    options_json = None
    if gen.options:
        import json

        options_json = json.dumps(gen.options, ensure_ascii=False)

    inst = GeneratedExerciseInstance(
        owner_id=current.id,
        topic_id=topic.id,
        question_text=gen.question_text,
        type=gen.type,
        options_json=options_json,
        correct_answer=gen.correct_answer,
        explanation=gen.explanation,
        difficulty=payload.difficulty,
        model=getattr(get_ai_service().provider, "model_name", None)
        or getattr(get_ai_service().provider, "model", "mock"),
        prompt_version="pilot-1",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return GenerateOut(**inst.to_safe_dict())


@router.post("/{exercise_id}/answer", response_model=AnswerOut)
def submit_answer(
    exercise_id: int,
    payload: AnswerIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """P1.2.3 + P1.2.4: server-owned answer evaluation.

    - загружает exercise из БД
    - 404 если не существует или owner != current
    - 410 если expired
    - 410 если уже submitted (idempotency)
    - exact match для server-trusted score
    - одна транзакция: attempt + progress
    """
    inst = db.get(GeneratedExerciseInstance, exercise_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    if inst.owner_id != current.id:
        raise HTTPException(status_code=404, detail="Exercise not found")
    if inst.is_expired:
        raise HTTPException(status_code=410, detail="Exercise expired")
    if inst.is_submitted:
        # Идемпотентно: возвращаем тот же результат, не пишем новый attempt.
        return AnswerOut(
            exercise_id=inst.id,
            is_correct=bool(inst.submission_score and inst.submission_score >= 0.5),
            score=float(inst.submission_score or 0.0),
            feedback="(повторный submit, попытка уже зафиксирована)",
            explanation=inst.explanation,
        )

    norm_user = (payload.user_answer or "").strip().lower()
    norm_ref = (inst.correct_answer or "").strip().lower()
    is_correct = bool(norm_user) and norm_user == norm_ref
    score = 1.0 if is_correct else 0.0

    inst.submitted_at = datetime.now(timezone.utc)
    inst.submission_answer = payload.user_answer
    inst.submission_score = score

    # Пишем Attempt + Progress (server-owned is_correct/score)
    attempt = progress_models.Attempt(
        user_id=current.id,
        topic_id=inst.topic_id,
        question_text=inst.question_text,
        user_answer=payload.user_answer,
        correct_answer=inst.correct_answer,
        is_correct=is_correct,
        score=score,
        feedback=None,
    )
    db.add(attempt)

    # Upsert Progress (replicate logic из progress.service.record_attempt)
    prog = db.scalar(
        select(progress_models.Progress).where(
            progress_models.Progress.user_id == current.id,
            progress_models.Progress.topic_id == inst.topic_id,
        )
    )
    if prog is None:
        prog = progress_models.Progress(
            user_id=current.id,
            topic_id=inst.topic_id,
            mastery_score=score,
            attempts_count=1,
            correct_count=1 if is_correct else 0,
        )
        db.add(prog)
    else:
        # 20-attempt sliding window
        recent = db.execute(
            select(progress_models.Attempt.score)
            .where(
                progress_models.Attempt.user_id == current.id,
                progress_models.Attempt.topic_id == inst.topic_id,
            )
            .order_by(progress_models.Attempt.created_at.desc())
            .limit(20)
        ).scalars().all()
        recent_scores = [float(s) for s in recent] + [score]
        prog.mastery_score = sum(recent_scores) / len(recent_scores)
        prog.attempts_count += 1
        if is_correct:
            prog.correct_count += 1

    db.commit()
    db.refresh(attempt)

    feedback = "Верно!" if is_correct else "Есть ошибка"
    return AnswerOut(
        exercise_id=inst.id,
        is_correct=is_correct,
        score=score,
        feedback=feedback,
        explanation=inst.explanation,
    )
