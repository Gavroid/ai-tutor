"""Сервис AI-репетитора: объяснение, подсказка, проверка, генерация."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.ai import prompts, sanitize
from app.ai.types import AIMessage, AIRequest, AIResponse, AIProvider
from app.config import get_settings
from app.subjects import models as subj_models
from app.users import models as user_models
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    is_correct: bool
    score: float
    first_error: str | None
    explanation: str
    hint_level: int
    next_difficulty: int


@dataclass
class GeneratedExercise:
    question_text: str
    type: str
    options: list[str] | None
    correct_answer: str
    explanation: str
    typical_mistakes: list[str]


class AIService:
    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider
        self._settings = get_settings()

    async def explain_topic(
        self, db: Session, user: user_models.User, topic: subj_models.Topic
    ) -> AIResponse:
        subject = topic.section.subject
        system = prompts.explain_topic_system(subject.name, topic.name, user.student_profile.grade if user.student_profile else 7)
        req = AIRequest(
            messages=[AIMessage(role="system", content=system), AIMessage(role="user", content="Объясни тему.")],
            mode="explain",
            max_tokens=900,
        )
        try:
            resp = await self.provider.complete(req)
            # Sprint 5.1: метрики
            try:
                from app.observability import record_ai_request
                record_ai_request(
                    mode="explain", status="ok",
                    input_tokens=resp.input_tokens,
                    output_tokens=resp.output_tokens,
                )
            except Exception:
                pass
            return resp
        except Exception:
            try:
                from app.observability import record_ai_request
                record_ai_request(mode="explain", status="error")
            except Exception:
                pass
            raise

    async def hint(self, question_text: str) -> AIResponse:
        req = AIRequest(
            messages=[
                AIMessage(role="system", content=prompts.hint_system()),
                AIMessage(role="user", content=f"Задание: {question_text}"),
            ],
            mode="hint",
            max_tokens=400,
        )
        return await self.provider.complete(req)

    async def check_answer(
        self,
        question_text: str,
        correct_answer: str,
        user_answer: str,
    ) -> CheckResult:
        user_answer = sanitize.sanitize_user_input(user_answer, self._settings.ai_max_input_chars)
        if sanitize.detect_injection(user_answer):
            # Подозрительный ввод — не отправляем в LLM, считаем ошибкой
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
        resp = await self.provider.complete(req)
        if resp.structured:
            try:
                return CheckResult(
                    is_correct=bool(resp.structured.get("is_correct")),
                    score=float(resp.structured.get("score", 0.0)),
                    first_error=resp.structured.get("first_error"),
                    explanation=str(resp.structured.get("explanation", "")),
                    hint_level=int(resp.structured.get("hint_level", 1)),
                    next_difficulty=int(resp.structured.get("next_difficulty", 1)),
                )
            except (TypeError, ValueError):
                pass
        # Fallback: эвристический парсинг или возврат общего ответа
        return CheckResult(
            is_correct=False,
            score=0.0,
            first_error=None,
            explanation=resp.content[:1000] or "Не удалось разобрать ответ.",
            hint_level=1,
            next_difficulty=2,
        )

    async def generate_exercise(
        self,
        subject_name: str,
        topic_name: str,
        difficulty: int,
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
        resp = await self.provider.complete(req)
        if resp.structured:
            s = resp.structured
            opts = s.get("options")
            tm = s.get("typical_mistakes", [])
            return GeneratedExercise(
                question_text=str(s.get("question_text", "")),
                type=str(s.get("type", "text")),
                options=list(opts) if isinstance(opts, list) else None,
                correct_answer=str(s.get("correct_answer", "")),
                explanation=str(s.get("explanation", "")),
                typical_mistakes=list(tm) if isinstance(tm, list) else [],
            )
        # Fallback — текстовое задание
        return GeneratedExercise(
            question_text=resp.content[:500],
            type="text",
            options=None,
            correct_answer="(см. объяснение)",
            explanation=resp.content[:1000],
            typical_mistakes=[],
        )

    async def chat(
        self,
        history: list[dict],
        subject_name: str | None = None,
        topic_name: str | None = None,
    ) -> AIResponse:
        """Свободный диалог с AI-репетитором."""
        sys = prompts.BASE_SYSTEM
        if subject_name and topic_name:
            sys += f"\n\nКонтекст: предмет «{subject_name}», тема «{topic_name}»."
        msgs: list[AIMessage] = [AIMessage(role="system", content=sys)]
        for m in history:
            r = m.get("role")
            c = sanitize.sanitize_user_input(m.get("content", ""), self._settings.ai_max_input_chars)
            if r in ("user", "assistant") and c:
                msgs.append(AIMessage(role=r, content=c))
        req = AIRequest(messages=msgs, mode="chat", max_tokens=900)
        return await self.provider.complete(req)


# Singleton-провайдер (ленивая инициализация)
_provider_instance: AIProvider | None = None


def get_provider() -> AIProvider:
    global _provider_instance
    if _provider_instance is None:
        from app.ai.hermes import build_provider

        _provider_instance = build_provider()
    return _provider_instance


def get_ai_service() -> AIService:
    return AIService(get_provider())