"""Сервис прогресса: запись попыток, пересчёт mastery, группировка по темам."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.progress import models, schemas
from app.subjects import models as subj_models


def _server_validate_attempt(
    user_answer: str | None,
    correct_answer: str | None,
    client_is_correct: bool,
    client_score: float,
) -> Tuple[bool, float]:
    """Pilot Core Stage 1 — P1.2.1: server-owned truth.

    Закрывает exploit «client шлёт is_correct=True, score=1.0, а на самом деле
    ответ неверный» — server всё равно вычисляет ground truth и сверяет.

    Логика:
    1. Если client прислал пустой correct_answer (diagnostic / pre-test submit) —
       server-trust невозможен. В Pilot Core: score=0, is_correct=False.
       (для legacy/teacher flows ничего не записываем как правильный).
    2. Если client-trusted exact match = True:
       - client_score используем (с ограничением 0..1), если в этом диапазоне.
       - иначе client_score = 1.0 (полный exact match).
    3. Если client-trusted exact match = False:
       - НЕ доверяем client is_correct/score (эксплойт).
       - client_score оставляем 0.0, is_correct=False, даже если client
         прислал is_correct=True / score=1.0.

    Это закрывает exploit и при этом уважает существующий semantic-match
    (client is_correct / score используются, только если они согласованы
    с сервер-валидацией).
    """
    if correct_answer is None or not str(correct_answer).strip():
        return False, 0.0
    norm_user = (user_answer or "").strip().lower()
    norm_ref = str(correct_answer).strip().lower()
    if not norm_user:
        return False, 0.0
    if norm_user == norm_ref:
        # exact match: доверяем client_score, если он в [0, 1]
        score = client_score if 0.0 <= client_score <= 1.0 else 1.0
        return True, float(score)
    # Не совпало — server-trust превалирует над client, даже если client
    # заявил is_correct=True (exploit).
    return False, 0.0


def record_attempt(db: Session, user_id: int, payload: schemas.AttemptCreate) -> models.Attempt:
    """Сохраняет попытку и пересчитывает mastery для темы.

    P1.2.1: server-owned truth — is_correct/score вычисляются из correct_answer
    и user_answer, client-supplied is_correct/score ИГНОРИРУЮТСЯ.
    """
    is_correct, score = _server_validate_attempt(
        payload.user_answer,
        payload.correct_answer,
        payload.is_correct,
        payload.score,
    )
    attempt = models.Attempt(
        user_id=user_id,
        topic_id=payload.topic_id,
        question_text=payload.question_text,
        user_answer=payload.user_answer,
        correct_answer=payload.correct_answer,
        is_correct=is_correct,
        score=score,
        feedback=payload.feedback,
    )
    db.add(attempt)

    # Mastery: скользящее среднее последних 20 попыток × score
    recent = db.execute(
        select(models.Attempt.score)
        .where(models.Attempt.user_id == user_id, models.Attempt.topic_id == payload.topic_id)
        .order_by(models.Attempt.created_at.desc())
        .limit(20)
    ).scalars().all()
    recent_scores = [float(s) for s in recent] + [score]
    new_mastery = sum(recent_scores) / len(recent_scores)

    # Upsert в Progress
    prog = db.scalar(
        select(models.Progress).where(
            models.Progress.user_id == user_id, models.Progress.topic_id == payload.topic_id
        )
    )
    if prog is None:
        prog = models.Progress(
            user_id=user_id,
            topic_id=payload.topic_id,
            mastery_score=new_mastery,
            attempts_count=1,
            correct_count=1 if is_correct else 0,
        )
        db.add(prog)
    else:
        prog.mastery_score = new_mastery
        prog.attempts_count += 1
        if is_correct:
            prog.correct_count += 1

    # Если неверно — фиксируем ошибку (агрегируем по mistake_type)
    if not is_correct:
        mistake_type = (payload.feedback or "unknown")[:80]
        m = db.scalar(
            select(models.Mistake).where(
                models.Mistake.user_id == user_id,
                models.Mistake.topic_id == payload.topic_id,
                models.Mistake.mistake_type == mistake_type,
            )
        )
        if m is None:
            db.add(
                models.Mistake(
                    user_id=user_id,
                    topic_id=payload.topic_id,
                    mistake_type=mistake_type,
                    description=(payload.feedback or "Неизвестная ошибка")[:2000],
                )
            )
        else:
            m.count += 1
            m.last_seen = func.now()

    db.commit()
    db.refresh(attempt)

    # Email notification родителям: каждые 5 новых attempt
    # (не на каждый — иначе спам)
    try:
        from app.notifications import service as notif_service

        total_attempts = db.scalar(
            select(func.count(models.Attempt.id)).where(
                models.Attempt.user_id == user_id
            )
        )
        # Уведомление после 5, 10, 20, 50, 100... attempts
        if total_attempts and total_attempts in {5, 10, 20, 50, 100, 200, 500}:
            topic = db.get(subj_models.Topic, payload.topic_id)
            subject_name = topic.section.subject.name if topic and topic.section and topic.section.subject else "?"
            topic_name = topic.name if topic else "?"
            mastery = prog.mastery_score if prog else 0.0
            notif_service.notify_parents_of_milestone(
                db,
                student_id=user_id,
                milestone=f"📚 {total_attempts} уроков пройдено",
                details=(
                    f"Тема: {topic_name}\n"
                    f"Предмет: {subject_name}\n"
                    f"Mastery: {int(mastery * 100)}%\n"
                    f"Правильных ответов: {prog.correct_count if prog else 0}/{total_attempts}"
                ),
            )
    except Exception:
        pass  # не блокируем основной flow

    return attempt


def get_user_mistakes(db: Session, user_id: int, limit: int = 50) -> list[models.Mistake]:
    return db.scalars(
        select(models.Mistake)
        .where(models.Mistake.user_id == user_id)
        .order_by(models.Mistake.last_seen.desc())
        .limit(limit)
    ).all()


def get_user_progress(db: Session, user_id: int) -> list[models.Progress]:
    return db.scalars(
        select(models.Progress).where(models.Progress.user_id == user_id)
    ).all()


def get_subject_progress(db: Session, user_id: int, subject_id: int) -> list[schemas.TopicProgress]:
    """Прогресс по всем темам предмета (даже если попыток не было — mastery=0)."""
    rows = db.execute(
        select(
            subj_models.Topic.id,
            subj_models.Topic.name,
            subj_models.Subject.id,
            subj_models.Subject.name,
            models.Progress.mastery_score,
            models.Progress.attempts_count,
            models.Progress.correct_count,
        )
        .select_from(subj_models.Topic)
        .join(subj_models.Section, subj_models.Topic.section_id == subj_models.Section.id)
        .join(subj_models.Subject, subj_models.Section.subject_id == subj_models.Subject.id)
        .outerjoin(
            models.Progress,
            (models.Progress.topic_id == subj_models.Topic.id) & (models.Progress.user_id == user_id),
        )
        .where(subj_models.Subject.id == subject_id)
        .order_by(subj_models.Section.order_index, subj_models.Topic.order_index)
    ).all()
    return [
        schemas.TopicProgress(
            topic_id=r[0],
            topic_name=r[1],
            subject_id=r[2],
            subject_name=r[3],
            mastery_score=float(r[4] or 0.0),
            attempts_count=int(r[5] or 0),
            correct_count=int(r[6] or 0),
        )
        for r in rows
    ]


def recommend_review(db: Session, user_id: int, limit: int = 5) -> list[schemas.TopicProgress]:
    """Темы с самым низким mastery, по которым есть хотя бы одна попытка."""
    rows = db.execute(
        select(
            subj_models.Topic.id,
            subj_models.Topic.name,
            subj_models.Subject.id,
            subj_models.Subject.name,
            models.Progress.mastery_score,
            models.Progress.attempts_count,
            models.Progress.correct_count,
        )
        .join(models.Progress, models.Progress.topic_id == subj_models.Topic.id)
        .join(subj_models.Section, subj_models.Topic.section_id == subj_models.Section.id)
        .join(subj_models.Subject, subj_models.Section.subject_id == subj_models.Subject.id)
        .where(models.Progress.user_id == user_id)
        .order_by(models.Progress.mastery_score.asc())
        .limit(limit)
    ).all()
    return [
        schemas.TopicProgress(
            topic_id=r[0],
            topic_name=r[1],
            subject_id=r[2],
            subject_name=r[3],
            mastery_score=float(r[4]),
            attempts_count=int(r[5]),
            correct_count=int(r[6]),
        )
        for r in rows
    ]


# === Sprint 2.2: Spaced Repetition ===

def due_for_review(
    db: Session, user_id: int, limit: int = 20
) -> list[schemas.ReviewItem]:
    """Темы, которые нужно повторить сегодня (next_review_at <= now).

    Включает overdue (next_review_at в прошлом) и свежие (ещё рано — отрицательный days_overdue).
    Возвращаются только темы, по которым есть хотя бы одна попытка.
    """
    now = datetime.now(timezone.utc)
    rows = db.execute(
        select(
            models.Progress,
            subj_models.Topic.id,
            subj_models.Topic.name,
            subj_models.Subject.name,
        )
        .join(subj_models.Topic, models.Progress.topic_id == subj_models.Topic.id)
        .join(subj_models.Section, subj_models.Topic.section_id == subj_models.Section.id)
        .join(subj_models.Subject, subj_models.Section.subject_id == subj_models.Subject.id)
        .where(models.Progress.user_id == user_id)
        .where(models.Progress.next_review_at.is_not(None))
        .order_by(models.Progress.next_review_at.asc())
        .limit(limit)
    ).all()

    items: list[schemas.ReviewItem] = []
    for prog, topic_id, topic_name, subject_name in rows:
        next_review = prog.next_review_at
        # next_review может быть naive (SQLite) или tz-aware (Postgres)
        if next_review.tzinfo is None:
            next_review = next_review.replace(tzinfo=timezone.utc)
        delta = next_review - now
        days_overdue = -int(delta.total_seconds() // 86400)
        items.append(
            schemas.ReviewItem(
                topic_id=topic_id,
                topic_name=topic_name,
                subject_name=subject_name,
                mastery_score=prog.mastery_score,
                review_count=prog.review_count,
                next_review_at=next_review,
                days_overdue=days_overdue,
            )
        )
    return items


def schedule_topic_for_review(
    db: Session, user_id: int, topic_id: int, quality: int | None = None,
    is_correct: bool | None = None, hint_used: bool = False,
) -> models.Progress:
    """Пометить тему как 'повторённую' и пересчитать next_review_at по SM-2.

    Если quality не передан — берётся из is_correct + hint_used.
    Идемпотентно: если Progress нет — создаём с дефолтами.
    """
    from app.progress.spaced import quality_from_result, schedule_next_review

    prog = db.scalar(
        select(models.Progress).where(
            models.Progress.user_id == user_id,
            models.Progress.topic_id == topic_id,
        )
    )
    if quality is None and is_correct is not None:
        quality = quality_from_result(is_correct, hint_used)
    elif quality is None:
        quality = 3  # средний дефолт

    if prog is None:
        prog = models.Progress(
            user_id=user_id,
            topic_id=topic_id,
            mastery_score=0.0,
            attempts_count=0,
            correct_count=0,
            easiness_factor=2.5,
            review_count=0,
        )
        db.add(prog)
        db.flush()  # получить defaults до расчёта

    # Если поля всё ещё None (старая запись без default в БД) — берём дефолты
    ef = prog.easiness_factor if prog.easiness_factor is not None else 2.5
    rc = prog.review_count if prog.review_count is not None else 0

    sched = schedule_next_review(
        last_reviewed_at=prog.last_reviewed_at,
        review_count=rc,
        easiness_factor=ef,
        quality=quality,
    )

    prog.next_review_at = sched.next_review_at
    prog.last_reviewed_at = datetime.now(timezone.utc)
    prog.review_count = sched.review_count
    prog.easiness_factor = sched.new_ef
    db.commit()
    db.refresh(prog)
    return prog