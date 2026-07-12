"""Сервис диагностики: генерирует 10 вопросов (по 2 на раздел, разные сложности),
проверяет ответы, считает mastery и формирует рекомендации.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.diagnostics import models, schemas
from app.subjects import models as subj_models
from app.subjects.curriculum_7_class import CURRICULUM_7_CLASS
from app.ai.types import AIRequest, AIMessage
from app.ai.service import get_ai_service


def _heuristic_check(question_text: str, correct: str, user_answer: str) -> bool:
    """Простая эвристика для шаблонных вопросов (без AI).

    Для математики: числовое сравнение с допуском.
    Для русского: ключевые слова (case-insensitive).
    """
    import re

    a = user_answer.strip().lower()
    b = correct.strip().lower()

    if a == b:
        return True

    # Числа?
    nums_a = re.findall(r"-?\d+(?:[.,]\d+)?", a)
    nums_b = re.findall(r"-?\d+(?:[.,]\d+)?", b)
    if nums_a and nums_b:
        try:
            return abs(float(nums_a[0].replace(",", ".")) - float(nums_b[0].replace(",", "."))) < 0.01
        except (ValueError, IndexError):
            pass

    # Содержит ключевые слова правильного ответа
    keywords = re.findall(r"\w{4,}", b)
    if keywords:
        matches = sum(1 for k in keywords if k in a)
        return matches >= max(1, len(keywords) // 2)

    return False


def start_diagnostic(db: Session, user_id: int, subject_id: int) -> models.DiagnosticSession:
    """Создаёт сессию и генерирует 10 вопросов через AI.

    Если AI недоступен — используем fallback (шаблонные вопросы по темам).
    """
    # Проверяем, что предмет существует
    subject = db.get(subj_models.Subject, subject_id)
    if subject is None:
        raise ValueError(f"Subject {subject_id} not found")

    # Берём 5 разных тем из предмета
    topics = db.execute(
        select(subj_models.Topic)
        .join(subj_models.Section)
        .where(subj_models.Section.subject_id == subject_id)
        .order_by(subj_models.Topic.difficulty, subj_models.Topic.order_index)
        .limit(5)
    ).scalars().all()

    session = models.DiagnosticSession(
        user_id=user_id,
        subject_id=subject_id,
        status="in_progress",
        total_questions=len(topics),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def next_question(db: Session, session_id: int) -> dict | None:
    """Возвращает следующий вопрос для сессии (генерирует через AI или fallback)."""
    import asyncio

    sess = db.get(models.DiagnosticSession, session_id)
    if sess is None or sess.status != "in_progress":
        return None

    answered = db.execute(
        select(models.DiagnosticAnswer.topic_id).where(
            models.DiagnosticAnswer.session_id == session_id
        )
    ).scalars().all()

    topic = db.execute(
        select(subj_models.Topic)
        .join(subj_models.Section)
        .where(subj_models.Section.subject_id == sess.subject_id)
        .where(subj_models.Topic.id.notin_(answered) if answered else True)
        .order_by(subj_models.Topic.difficulty, subj_models.Topic.order_index)
        .limit(1)
    ).scalars().first()

    if topic is None:
        return None

    subject = topic.section.subject

    # Генерируем вопрос через AI (синхронно, т.к. TestClient async-friendly)
    svc = get_ai_service()

    async def _gen():
        return await svc.generate_exercise(subject.name, topic.name, topic.difficulty)

    try:
        gen = asyncio.run(_gen())
        q_text = gen.question_text
        correct = gen.correct_answer
    except Exception:
        # Fallback
        q_text = f"[fallback] Тестовый вопрос по теме «{topic.name}». Опиши своими словами, что ты знаешь о ней."
        correct = topic.description or topic.name

    # Сохраняем вопрос (без ответа — он придёт через /answer)
    sess.total_questions = len(answered) + 1
    db.commit()
    db.refresh(sess)

    return {
        "session_id": sess.id,
        "topic_id": topic.id,
        "topic_name": topic.name,
        "subject_name": subject.name,
        "difficulty": topic.difficulty,
        "question_text": q_text,
    }


def submit_answer(
    db: Session,
    session_id: int,
    topic_id: int,
    question_text: str,
    user_answer: str,
    correct_answer: str,
) -> models.DiagnosticAnswer:
    sess = db.get(models.DiagnosticSession, session_id)
    if sess is None or sess.status != "in_progress":
        raise ValueError("Session not in progress")

    is_correct = _heuristic_check(question_text, correct_answer, user_answer)

    answer = models.DiagnosticAnswer(
        session_id=session_id,
        topic_id=topic_id,
        question_text=question_text,
        user_answer=user_answer,
        correct_answer=correct_answer,
        is_correct=is_correct,
        difficulty=2,
    )
    db.add(answer)
    if is_correct:
        sess.correct_count += 1
    db.commit()
    db.refresh(answer)
    return answer


def expire_stale_diagnostic_sessions(db: Session, ttl_hours: int = 24) -> int:
    """Завершает диагностические сессии, которые in_progress больше ttl часов.

    Полезно вызывать периодически (cron) или вручную через /admin/endpoint.
    Возвращает количество завершённых сессий.
    """
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)

    stale = db.scalars(
        select(models.DiagnosticSession).where(
            models.DiagnosticSession.status == "in_progress",
            models.DiagnosticSession.started_at < cutoff,
        )
    ).all()

    count = 0
    for sess in stale:
        sess.status = "expired"
        sess.finished_at = datetime.now(timezone.utc)
        # Не считаем оценку — пользователь не ответил
        sess.overall_score = 0.0
        sess.recommendations = "Сессия истекла (24 часа). Начните диагностику заново."
        db.commit()
        count += 1

    if count > 0:
        logger = __import__("logging").getLogger(__name__)
        logger.info("Expired %d stale diagnostic sessions", count)
    return count


def finish_diagnostic(db: Session, session_id: int, user_id: int) -> models.DiagnosticSession:
    sess = db.get(models.DiagnosticSession, session_id)
    if sess is None or sess.user_id != user_id:
        raise ValueError("Session not found")
    if sess.status == "finished":
        return sess

    answers = db.scalars(
        select(models.DiagnosticAnswer).where(models.DiagnosticAnswer.session_id == session_id)
    ).all()

    if not answers:
        raise ValueError("No answers recorded")

    # Считаем по темам
    from collections import defaultdict

    by_topic: dict[int, list[bool]] = defaultdict(list)
    for a in answers:
        by_topic[a.topic_id].append(a.is_correct)

    weak = []
    for tid, results in by_topic.items():
        ratio = sum(results) / len(results)
        if ratio < 0.6:
            topic = db.get(subj_models.Topic, tid)
            if topic:
                weak.append(
                    {
                        "topic_id": tid,
                        "topic_name": topic.name,
                        "mastery": round(ratio, 2),
                    }
                )

    sess.overall_score = sum(1 for a in answers if a.is_correct) / len(answers)
    sess.weak_topics = json.dumps(weak, ensure_ascii=False)
    if weak:
        rec_lines = ["Стоит повторить:"]
        for w in sorted(weak, key=lambda x: x["mastery"]):
            rec_lines.append(f"  • {w['topic_name']} (уверенность {int(w['mastery'] * 100)}%)")
        rec_lines.append(
            "\nПосле нескольких упражнений по этим темам результат улучшится."
        )
    else:
        rec_lines = ["Отличный результат! Можно двигаться дальше."]
    sess.recommendations = "\n".join(rec_lines)
    sess.status = "finished"
    from datetime import datetime, timezone

    sess.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(sess)

    # Уведомляем родителей о завершении диагностики
    try:
        from app.notifications import service as notif_service

        score_pct = int(sess.overall_score * 100)
        notif_service.notify_parents_of_milestone(
            db,
            student_id=sess.user_id,
            milestone=f"Пройдена диагностика — {score_pct}%",
            details=sess.recommendations or "",
        )
    except Exception:
        pass  # не блокируем основной flow

    return sess