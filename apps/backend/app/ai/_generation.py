"""Sprint 3.29: generation methods (generate_exercise, generate_quiz) moved from AIService.

Behavioral identity (zero change). Function-based extraction pattern
(см. Sprint 3.29 step 1 commit 2fd6fc5).

Public API: AIService.{generate_exercise, generate_quiz} остались через
1-line forwarding.
"""

from __future__ import annotations

import logging

from app.ai import prompts
from app.ai.datatypes import GeneratedExercise
from app.ai.quiz_types import Quiz, QuizQuestion
from app.ai.service import (
    _clean_student_visible_text,
    _exercise_matches_topic,
    _fallback_generated_exercise,
    _record_ai,
    _valid_generated_exercise,
)
from app.ai.types import AIMessage, AIRequest, AIResponse
from app.subjects import models as subj_models
from app.users import models as user_models
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def generate_exercise(
    service,
    subject_name: str,
    topic_name: str,
    difficulty: int,
    topic_id: int | None = None,
) -> GeneratedExercise:
    req = AIRequest(
        messages=[
            AIMessage(
                role="system",
                content=prompts.generate_exercise_system(subject_name, topic_name, difficulty),
            ),
            AIMessage(role="user", content="Сгенерируй задание."),
        ],
        mode="generate",
        max_tokens=700,
        temperature=0.6,
    )
    try:
        resp = await service.provider.complete(req)
        if resp.structured:
            try:
                result = _valid_generated_exercise(resp.structured)
                if not _exercise_matches_topic(result, topic_name):
                    _record_ai("generate", "ok", resp=resp, parse_status="fallback")
                    return _fallback_generated_exercise(subject_name, topic_name, difficulty, topic_id=topic_id)
                _record_ai("generate", "ok", resp=resp, parse_status="ok")
                return result
            except (TypeError, ValueError):
                _record_ai("generate", "ok", resp=resp, parse_status="error")
                return _fallback_generated_exercise(subject_name, topic_name, difficulty, topic_id=topic_id)
        _record_ai("generate", "ok", resp=resp, parse_status="fallback")
        return _fallback_generated_exercise(subject_name, topic_name, difficulty, topic_id=topic_id)
    except Exception as e:
        _record_ai("generate", "error")
        logger.warning("AI generate provider failure → fallback: %s", e)
        return _fallback_generated_exercise(subject_name, topic_name, difficulty, topic_id=topic_id)


async def generate_quiz(
    service,
    subject_name: str,
    topic_name: str,
    difficulty: int,
    count: int,
) -> Quiz:
    """Сгенерировать набор из `count` разнотипных вопросов по теме (квиз).

    Парсит JSON {"questions": [...]} из resp.structured. Если парсинг не удался —
    возвращает квиз из одного текстового вопроса (fallback). Метрика parse_status:
    ok / fallback / error.
    """
    max_tokens = max(2048, count * 350)
    req = AIRequest(
        messages=[
            AIMessage(
                role="system",
                content=prompts.quiz_system(subject_name, topic_name, difficulty, count),
            ),
            AIMessage(role="user", content="Сгенерируй квиз."),
        ],
        mode="quiz",
        max_tokens=max_tokens,
        temperature=0.6,
    )
    try:
        resp = await service.provider.complete(req)
        if resp.structured:
            raw_questions = resp.structured.get("questions")
            if isinstance(raw_questions, list) and raw_questions:
                try:
                    questions: list[QuizQuestion] = []
                    for item in raw_questions:
                        if not isinstance(item, dict):
                            continue
                        opts = item.get("options")
                        questions.append(
                            QuizQuestion(
                                question_text=_clean_student_visible_text(item.get("question_text", "")),
                                type=str(item.get("type", "text")),
                                options=[
                                    _clean_student_visible_text(option)
                                    for option in opts
                                    if _clean_student_visible_text(option)
                                ]
                                if isinstance(opts, list)
                                else None,
                                correct_answer=_clean_student_visible_text(item.get("correct_answer", "")),
                                explanation=_clean_student_visible_text(item.get("explanation", "")),
                            )
                        )
                    if questions:
                        _record_ai("quiz", "ok", resp=resp, parse_status="ok")
                        return Quiz(questions=questions)
                except (TypeError, ValueError):
                    _record_ai("quiz", "ok", resp=resp, parse_status="error")
        # Fallback: один текстовый вопрос с обрезанным содержимым ответа
        _record_ai("quiz", "ok", resp=resp, parse_status="fallback")
        return Quiz(
            questions=[
                QuizQuestion(
                    question_text=_clean_student_visible_text(resp.content[:500]) or "(нет ответа)",
                    type="text",
                    options=None,
                    correct_answer="(см. объяснение)",
                    explanation=_clean_student_visible_text(resp.content[:1000]) or "Не удалось разобрать ответ.",
                )
            ]
        )
    except Exception as e:
        _record_ai("quiz", "error")
        logger.exception("AI quiz failed: %s", e)
        raise
