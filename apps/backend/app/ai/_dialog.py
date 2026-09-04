"""Sprint 3.29: dialog methods (hint, hint_at_level, _hint_with_level, check_answer)
moved from AIService.

Behavioral identity (zero change). Function-based extraction pattern
(см. Sprint 3.29 step 1 commit 2fd6fc5).

Public API: AIService.{hint, hint_at_level, _hint_with_level, check_answer}
остались через 1-line forwarding.
"""
from __future__ import annotations

import logging

from app.ai import prompts, sanitize
from app.ai.datatypes import CheckResult
from app.ai.service import _clean_student_visible_text, _record_ai
from app.ai.types import AIMessage, AIRequest, AIResponse
from app.users import models as user_models
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def hint(service, question_text: str, level: int = 1) -> AIResponse:
    """Sprint 7.4: подсказка уровня 1 (наводящий вопрос).

    Для уровней 2/3 используй hint_at_level().
    """
    return await _hint_with_level(service, question_text, level=1)

async def hint_at_level(service, question_text: str, level: int, error_type: str | None = None) -> AIResponse:
    """Sprint 7.4 + 4.3.2: подсказка уровня 1..3 с учётом типа ошибки.

    error_type (опционально): ARITHMETIC/CONCEPTUAL/LOGIC/CARELESS от judge.
    Если указан — промпт адаптируется под тип ошибки.
    """
    return await _hint_with_level(service, question_text, level=level, error_type=error_type)

async def _hint_with_level(service, question_text: str, level: int, error_type: str | None = None) -> AIResponse:
    level = max(1, min(3, level))  # clamp
    req = AIRequest(
        messages=[
            AIMessage(role="system", content=prompts.hint_system_at_level(level, error_type=error_type)),
            AIMessage(role="user", content=f"Задание: {question_text}"),
        ],
        mode="hint",
        max_tokens=400,
    )
    try:
        resp = await service.provider.complete(req)
        resp.content = _clean_student_visible_text(resp.content)
        _record_ai("hint", "ok", resp=resp)
        return resp
    except Exception as e:
        _record_ai("hint", "error")
        logger.exception("AI hint failed: %s", e)
        raise

async def check_answer(
    service,
    question_text: str,
    correct_answer: str,
    user_answer: str,
) -> CheckResult:
    user_answer = sanitize.sanitize_user_input(user_answer, service._settings.ai_max_input_chars)
    if sanitize.detect_injection(user_answer):
        # Подозрительный ввод — не отправляем в LLM, считаем ошибкой
        _record_ai("check", "ok", parse_status="fallback")  # не LLM, но это решение
        return CheckResult(
            is_correct=False,
            score=0.0,
            first_error="Подозрительный ввод",
            explanation="Похоже, в ответе есть инструкции для модели. Дай обычный ответ на задание.",
            hint_level=1,
            next_difficulty=1,
        )
    req = AIRequest(
        messages=[
            AIMessage(
                role="system",
                content=prompts.check_answer_system(question_text, correct_answer, user_answer),
            ),
            AIMessage(role="user", content="Проверь."),
        ],
        mode="check",
        max_tokens=500,
        temperature=0.0,
    )
    try:
        resp = await service.provider.complete(req)
        if resp.structured:
            try:
                result = CheckResult(
                    is_correct=bool(resp.structured.get("is_correct")),
                    score=float(resp.structured.get("score", 0.0)),
                    first_error=_clean_student_visible_text(resp.structured.get("first_error")),
                    explanation=_clean_student_visible_text(resp.structured.get("explanation", "")),
                    hint_level=int(resp.structured.get("hint_level", 1)),
                    next_difficulty=int(resp.structured.get("next_difficulty", 1)),
                    # Sprint 4.3.1: error_type для context-aware hints.
                    # Валидируем чтобы не принимать мусор от LLM.
                    error_type=resp.structured.get("error_type")
                    if resp.structured.get("error_type") in ("ARITHMETIC", "CONCEPTUAL", "LOGIC", "CARELESS")
                    else None,
                )
                _record_ai("check", "ok", resp=resp, parse_status="ok")
                return result
            except (TypeError, ValueError):
                _record_ai("check", "ok", resp=resp, parse_status="error")
        # Fallback: эвристический парсинг или возврат общего ответа
        _record_ai("check", "ok", resp=resp, parse_status="fallback")
        return CheckResult(
            is_correct=False,
            score=0.0,
            first_error=None,
            explanation=_clean_student_visible_text(resp.content[:1000]) or "Не удалось разобрать ответ.",
            hint_level=1,
            next_difficulty=2,
        )
    except Exception as e:
        _record_ai("check", "error")
        logger.exception("AI check failed: %s", e)
        raise
