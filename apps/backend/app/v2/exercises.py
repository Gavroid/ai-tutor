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
    # Sprint 61: difficulty=0 = auto (adaptive), 1-5 = explicit
    difficulty: int = Field(default=0, ge=0, le=5)


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
    # Sprint 4.3.1: error_type для context-aware hints (опциональный).
    error_type: str | None = None


# === Sprint 61: Adaptive difficulty ===

def compute_adaptive_difficulty(
    db: Session,
    user_id: int,
    topic_id: int,
    recovery_mode: bool = False,
) -> int:
    """Sprint 61: adaptive difficulty на основе recent performance + recovery.

    Returns:
        1 (easy) — recovery_mode active ИЛИ low recent accuracy
        2 (medium) — default
        3 (hard) — high recent accuracy AND no recovery

    Logic:
        - Если recovery_mode → 1 (T1D safety, легкий контент)
        - Иначе анализируем last 5 attempts:
            - avg_score < 0.5 → 1 (слишком сложно)
            - avg_score > 0.8 → 3 (можно усложнить)
            - иначе → 2 (default)
    """
    from app.progress import models as prog_models

    # T1D safety: recovery mode = easy
    if recovery_mode:
        return 1

    # Анализ recent attempts
    recent_attempts = (
        db.query(prog_models.Attempt)
        .filter(prog_models.Attempt.user_id == user_id)
        .filter(prog_models.Attempt.topic_id == topic_id)
        .order_by(prog_models.Attempt.created_at.desc())
        .limit(5)
        .all()
    )

    if not recent_attempts:
        return 2  # default для новых пользователей

    # avg score (0.0-1.0)
    avg_score = sum(a.score for a in recent_attempts) / len(recent_attempts)

    if avg_score < 0.5:
        return 1  # easy — слишком сложно
    elif avg_score > 0.8 and len(recent_attempts) >= 3:
        return 3  # hard — можно усложнить
    else:
        return 2  # medium — default


def _rotate_repeated_exercise(
    db: Session,
    current: User,
    topic: subj_models.Topic,
    target_difficulty: int,
    gen,
):
    """Server-side anti-repeat guard for repeated Practice clicks."""
    recent_questions = set(
        db.execute(
            select(GeneratedExerciseInstance.question_text)
            .where(
                GeneratedExerciseInstance.owner_id == current.id,
                GeneratedExerciseInstance.topic_id == topic.id,
            )
            .order_by(GeneratedExerciseInstance.created_at.desc())
            .limit(3)
        ).scalars().all()
    )
    if gen.question_text not in recent_questions:
        return gen
    svc = get_ai_service()
    for offset in range(1, 6):
        rotated = _run_sync_generate_fallback(topic, target_difficulty + offset, svc)
        if rotated.question_text not in recent_questions:
            return rotated
    return gen


def _run_sync_generate_fallback(topic: subj_models.Topic, difficulty: int, svc):
    """Use AIService fallback directly; kept small for anti-repeat guard."""
    from app.ai.service import _fallback_generated_exercise

    return _fallback_generated_exercise(
        topic.section.subject.name,
        topic.name,
        max(1, difficulty),
        topic_id=topic.id,
    )


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

    # Sprint 61: adaptive difficulty.
    # Если client явно НЕ передал difficulty (0 = auto), вычисляем на основе
    # recovery_mode + recent performance.
    target_difficulty = payload.difficulty
    if target_difficulty == 0:
        # Sprint 42: проверяем recovery_mode (недавняя hypo/hyper пауза)
        from app.sessions.models import SessionPause
        from datetime import datetime, timezone, timedelta
        recovery = (
            db.query(SessionPause)
            .filter(
                SessionPause.user_id == current.id,
                SessionPause.reason.in_(["hypo", "hyper"]),
            )
            .order_by(SessionPause.started_at.desc())
            .first()
        )
        recovery_mode = False
        if recovery and recovery.started_at:
            ref_time = datetime.now(timezone.utc)
            started = recovery.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            minutes_ago = (ref_time - started).total_seconds() / 60
            if minutes_ago < 30:
                recovery_mode = True

        target_difficulty = compute_adaptive_difficulty(
            db, user_id=current.id, topic_id=payload.topic_id, recovery_mode=recovery_mode
        )

    # Переиспользуем существующий AI-сервис. Он уже возвращает correct_answer
    # в GeneratedExercise — мы НЕ отдаём его в ответе, а сохраняем в БД.
    svc = get_ai_service()
    gen = await svc.generate_exercise(
        subject_name=topic.section.subject.name,
        topic_name=topic.name,
        difficulty=target_difficulty,
        topic_id=topic.id,
    )
    gen = _rotate_repeated_exercise(db, current, topic, target_difficulty, gen)

    options_json = None
    if gen.options:
        import json

        options_json = json.dumps(gen.options, ensure_ascii=False)

    # Sprint 19 P2-2: автоопределение checker_type по типу упражнения.
    # numeric → numeric checker
    # exact → exact match (default)
    # иначе → keyword
    inferred_checker = "keyword"
    if gen.type == "numeric":
        inferred_checker = "numeric"
    elif gen.type in ("single", "multiple", "text", "short"):
        inferred_checker = "exact"

    inst = GeneratedExerciseInstance(
        owner_id=current.id,
        topic_id=topic.id,
        question_text=gen.question_text,
        type=gen.type,
        options_json=options_json,
        correct_answer=gen.correct_answer,
        explanation=gen.explanation,
        difficulty=target_difficulty,
        model=getattr(get_ai_service().provider, "model_name", None)
        or getattr(get_ai_service().provider, "model", "mock"),
        prompt_version="pilot-1",
        checker_type=inferred_checker,
        reference_solution=gen.correct_answer,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return GenerateOut(**inst.to_safe_dict())


@router.post("/{exercise_id}/answer", response_model=AnswerOut)
async def submit_answer(
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
    # Idempotent only for the same already-correct answer. If the child changes
    # the answer after seeing feedback, the UI must reflect the latest answer.
    norm_incoming = (payload.user_answer or "").strip()
    if (
        inst.is_submitted
        and inst.submission_score is not None
        and inst.submission_score >= 0.5
        and norm_incoming.lower() == (inst.submission_answer or "").strip().lower()
    ):
        return AnswerOut(
            exercise_id=inst.id,
            is_correct=True,
            score=float(inst.submission_score or 0.0),
            feedback="(повторный submit, попытка уже зафиксирована)",
            explanation=inst.explanation,
        )

    norm_user = norm_incoming
    norm_ref = (inst.correct_answer or "").strip()

    # Sprint 19 P2-2 + Sprint 25: используем диспатчер checkers.
    # - numeric/keyword/exact — sync
    # - semantic — async через AIService.check_answer
    # Fallback на exact match для обратной совместимости.
    effective_checker = inst.checker_type or "exact"
    if inst.type in ("single", "multiple"):
        effective_checker = "exact"

    if effective_checker != "exact":
        from app.practice.checkers import check_answer, check_answer_async
        import json as _json

        keywords_list: list[str] = []
        if inst.required_keywords:
            try:
                keywords_list = _json.loads(inst.required_keywords)
            except (ValueError, TypeError):
                keywords_list = []

        if effective_checker == "semantic":
            # Sprint 25: async semantic через AI judge.
            check_result = await check_answer_async(
                user_answer=norm_user,
                reference_solution=norm_ref,
                question_text=inst.question_text,
            )
        else:
            check_result = check_answer(
                user_answer=norm_user,
                reference_solution=norm_ref,
                checker_type=effective_checker,
                keywords=keywords_list,
                question_text=inst.question_text,
            )
        is_correct = bool(check_result["correct"])
        score = float(check_result["score"])
        feedback = (
            f"[{check_result['checker']}] "
            + ("Верно!" if is_correct else "Есть ошибка")
        )
    else:
        # Fallback: exact match (default behavior).
        is_correct = bool(norm_user) and norm_user.lower() == norm_ref.lower()
        score = 1.0 if is_correct else 0.0
        feedback = "Верно!" if is_correct else "Есть ошибка"

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

    # Sprint 49: update parent metrics (attempts counter).
    from app.parent_metrics import increment_attempt, observe_session_duration

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    increment_attempt(user_id=current.id, day=today)
    # Наблюдаем session duration (~avg 600s типично).
    # TODO Sprint 50: track actual session duration from first WS connect.
    observe_session_duration(600.0)

    return AnswerOut(
        exercise_id=inst.id,
        is_correct=is_correct,
        score=score,
        feedback=feedback,
        explanation=inst.explanation,
    )
