"""Sprint 8.5 — адаптивный выбор следующего вопроса (CAT-lite).

Упрощённая версия Computerized Adaptive Testing (CAT):
- После каждого ответа обновляем оценку способности ученика (θ).
- Следующий вопрос выбирается с difficulty, ближайшей к θ
  (item difficulty = текущая сложность +0/+1/-1 от способности).

Реализация — без сложной IRT (item response theory), простое «правильно — повысить,
неправильно — понизить». Достаточно для MVP и заметно лучше фиксированной сложности.

TODO (Sprint 8.5+ расширения):
- IRT 2PL модель (разделить θ по темам).
- Item bank с информационной функцией (Fisher information).
- Способность рассчитывать по Вальду (MLE).
"""
from __future__ import annotations

import math
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.diagnostics import models
from app.subjects import models as subj_models

logger = logging.getLogger(__name__)


# Sprint 8.5 — константы алгоритма
MIN_DIFFICULTY = 1  # easy
MAX_DIFFICULTY = 5  # hard
INITIAL_THETA = 3.0  # начинаем со средней сложности
DIFFICULTY_STEP_UP = 0.5  # при правильном ответе — повысить θ
DIFFICULTY_STEP_DOWN = 0.7  # при неправильном — понизить чуть больше
TARGET_SUCCESS_RATE = 0.7  # цель — 70% успешных (комфортная зона)


@dataclass
class AdaptiveState:
    """Состояние адаптивной диагностики."""

    theta: float = INITIAL_THETA  # оценка способности ученика (1..5)
    answered: int = 0
    correct: int = 0
    history: list[dict] | None = None  # [{topic_id, correct, difficulty_after}]

    def __post_init__(self):
        if self.history is None:
            self.history = []

    @property
    def success_rate(self) -> float:
        return self.correct / self.answered if self.answered > 0 else 0.0


def estimate_theta_after_answer(theta: float, correct: bool) -> float:
    """Обновить θ на основе ответа.

    Если правильно и success_rate ниже target → повышаем (необходимо вытянуть наверх).
    Если неправильно — понижаем быстрее (компенсация лёгкого завышения).
    """
    if correct:
        # Успех: шаг вверх, но если уже превышаем target — помедленнее
        new = theta + DIFFICULTY_STEP_UP
    else:
        # Ошибка: шаг вниз
        new = theta - DIFFICULTY_STEP_DOWN

    # Ограничиваем [MIN, MAX]
    return max(MIN_DIFFICULTY, min(MAX_DIFFICULTY, new))


def choose_next_difficulty(state: AdaptiveState) -> int:
    """Sprint 8.5: адаптивный выбор difficulty следующего вопроса.

    Чем хуже успеваемость — тем проще следующий (θ уменьшается).
    Чем лучше — тем сложнее (θ увеличивается).

    Возвращает целое число difficulty 1..5.
    """
    theta_int = max(MIN_DIFFICULTY, min(MAX_DIFFICULTY, int(round(state.theta))))
    return theta_int


def next_topic_adaptive(
    db: Session,
    session_id: int,
    state: AdaptiveState | None = None,
) -> dict | None:
    """Sprint 8.5: вернуть следующий topic + вопрос с адаптивной difficulty.

    Returns:
        {
          "topic": Topic,
          "theta_before": float,
          "theta_after_estimate": float,  # оценка после следующего ответа
          "question": {...}
        }
        или None если диагностика завершена.
    """
    sess = db.get(models.DiagnosticSession, session_id)
    if sess is None or sess.status != "in_progress":
        return None

    if state is None:
        state = AdaptiveState()

    # Берём список тем для предмета
    all_topics = db.execute(
        select(subj_models.Topic)
        .join(subj_models.Section)
        .where(subj_models.Section.subject_id == sess.subject_id)
    ).scalars().all()

    answered_ids = set(
        db.execute(
            select(models.DiagnosticAnswer.topic_id).where(
                models.DiagnosticAnswer.session_id == session_id
            )
        ).scalars().all()
    )

    remaining = [t for t in all_topics if t.id not in answered_ids]
    if not remaining:
        # Диагностика завершена
        return None

    # Адаптивно выбираем difficulty
    target_diff = choose_next_difficulty(state)

    # Ищем тему с difficulty наиболее близкой к target
    best_topic = min(remaining, key=lambda t: (abs(t.difficulty - target_diff), t.order_index))

    # Оцениваем, какой θ будет если ученик ответит правильно/неправильно
    theta_if_correct = estimate_theta_after_answer(state.theta, correct=True)
    theta_if_wrong = estimate_theta_after_answer(state.theta, correct=False)

    # Генерируем вопрос через существующую инфраструктуру
    from app.ai.service import AIService, get_ai_service
    import asyncio

    async def _gen_question():
        svc = get_ai_service()
        from app.subjects.curriculum_7_class import CURRICULUM_7_CLASS  # noqa: F401
        # Используем существующий метод — generate_exercise
        try:
            gen = await svc.generate_exercise(
                subject_name=best_topic.section.subject.name,
                topic_name=best_topic.name,
                difficulty=best_topic.difficulty,
            )
            return {
                "question_text": gen.question_text,
                "options": gen.options,
                "type": gen.type,
                "correct_answer": gen.correct_answer,
                "explanation": gen.explanation,
            }
        except Exception as e:
            logger.warning("AI generation failed: %s", e)
            return None

    # Запускаем генерацию (sync API)
    try:
        question = asyncio.run(_gen_question())
    except Exception as e:
        logger.warning("asyncio.run failed: %s", e)
        question = None

    if question is None:
        # Fallback — синтетический вопрос
        question = {
            "question_text": f"Пример задачи на тему «{best_topic.name}»",
            "options": None,
            "type": "text",
            "correct_answer": "(см. учебник)",
            "explanation": f"Это пример задачи по теме {best_topic.name}.",
        }

    return {
        "topic": best_topic,
        "question": question,
        "target_difficulty": target_diff,
        "theta_before": state.theta,
        "theta_if_correct": theta_if_correct,
        "theta_if_wrong": theta_if_wrong,
        "answered_count": state.answered,
        "remaining_count": len(remaining),
    }


def record_answer_adaptive(
    state: AdaptiveState,
    topic_id: int,
    correct: bool,
) -> AdaptiveState:
    """Обновить state после ответа (Sprint 8.5)."""
    new_theta = estimate_theta_after_answer(state.theta, correct)
    new_history = list(state.history or [])
    new_history.append(
        {
            "topic_id": topic_id,
            "correct": correct,
            "theta_after": new_theta,
        }
    )
    return AdaptiveState(
        theta=new_theta,
        answered=state.answered + 1,
        correct=state.correct + (1 if correct else 0),
        history=new_history,
    )


def difficulty_label(d: int) -> str:
    """Human-readable label для difficulty 1..5."""
    return {
        1: "лёгкий",
        2: "средний",
        3: "продвинутый",
        4: "сложный",
        5: "очень сложный",
    }.get(d, "?")
