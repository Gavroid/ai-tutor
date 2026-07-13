"""Сервис AI-репетитора: объяснение, подсказка, проверка, генерация.

Sprint 8.4: record_ai_request() вызывается во ВСЕХ режимах (было только в explain).
Sprint 8.1 (частично): baseline Pydantic-схема `GeneratedMaterial` для structured output;
                       сам provider пока не поддерживает strict_json — fallback оставлен
                       как best-effort, метрика `ai_parse_status{result=ok|fallback|error}`.
"""
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


def _record_ai(
    mode: str,
    status: str,
    resp: AIResponse | None = None,
    parse_status: str | None = None,
) -> None:
    """Best-effort запись метрик AI. Ошибки метрик НЕ должны ломать основной поток.

    Args:
        mode: режим ('explain' | 'chat' | 'hint' | 'check' | 'generate' | 'teacher' | 'judge').
        status: 'ok' | 'error'.
        resp: ответ AI (если есть).
        parse_status: 'ok' | 'fallback' | 'error' (только если есть structured output).
    """
    try:
        from app.observability import record_ai_request
        in_tok = getattr(resp, "input_tokens", 0) if resp else 0
        out_tok = getattr(resp, "output_tokens", 0) if resp else 0
        record_ai_request(
            mode=mode,
            status=status,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
        if parse_status:
            try:
                from prometheus_client import Counter
                _PARSE_CNT.labels(mode=mode, result=parse_status).inc()
            except (ImportError, AttributeError, ValueError):
                # метрика может быть ещё не определена — игнорируем
                pass
    except Exception:
        # метрики — best-effort, не роняем основной поток
        pass


# === Метрика парсинга structured output (Sprint 8.1) ===
try:
    from prometheus_client import Counter
    _PARSE_CNT = Counter(
        "ai_parse_status_total",
        "Structured output parse result (ok=валидно, fallback=heuristic, error=invalid JSON).",
        labelnames=("mode", "result"),
    )
except ImportError:  # pragma: no cover — prometheus не в requirements-dev
    _PARSE_CNT = None  # type: ignore


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
            _record_ai("explain", "ok", resp=resp)
            return resp
        except Exception as e:
            _record_ai("explain", "error")
            logger.exception("AI explain failed: %s", e)
            raise

    async def hint(self, question_text: str, level: int = 1) -> AIResponse:
        """Sprint 7.4: подсказка уровня 1 (наводящий вопрос).

        Для уровней 2/3 используй hint_at_level().
        """
        return await self._hint_with_level(question_text, level=1)

    async def hint_at_level(self, question_text: str, level: int) -> AIResponse:
        """Sprint 7.4: подсказка уровня 1..3 (1=наводящий, 2=подсказка, 3=разбор)."""
        return await self._hint_with_level(question_text, level=level)

    async def _hint_with_level(self, question_text: str, level: int) -> AIResponse:
        level = max(1, min(3, level))  # clamp
        req = AIRequest(
            messages=[
                AIMessage(role="system", content=prompts.hint_system_at_level(level)),
                AIMessage(role="user", content=f"Задание: {question_text}"),
            ],
            mode="hint",
            max_tokens=400,
        )
        try:
            resp = await self.provider.complete(req)
            _record_ai("hint", "ok", resp=resp)
            return resp
        except Exception as e:
            _record_ai("hint", "error")
            logger.exception("AI hint failed: %s", e)
            raise

    async def check_answer(
        self,
        question_text: str,
        correct_answer: str,
        user_answer: str,
    ) -> CheckResult:
        user_answer = sanitize.sanitize_user_input(user_answer, self._settings.ai_max_input_chars)
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
            resp = await self.provider.complete(req)
            if resp.structured:
                try:
                    result = CheckResult(
                        is_correct=bool(resp.structured.get("is_correct")),
                        score=float(resp.structured.get("score", 0.0)),
                        first_error=resp.structured.get("first_error"),
                        explanation=str(resp.structured.get("explanation", "")),
                        hint_level=int(resp.structured.get("hint_level", 1)),
                        next_difficulty=int(resp.structured.get("next_difficulty", 1)),
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
                explanation=resp.content[:1000] or "Не удалось разобрать ответ.",
                hint_level=1,
                next_difficulty=2,
            )
        except Exception as e:
            _record_ai("check", "error")
            logger.exception("AI check failed: %s", e)
            raise

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
        try:
            resp = await self.provider.complete(req)
            if resp.structured:
                s = resp.structured
                opts = s.get("options")
                tm = s.get("typical_mistakes", [])
                try:
                    result = GeneratedExercise(
                        question_text=str(s.get("question_text", "")),
                        type=str(s.get("type", "text")),
                        options=list(opts) if isinstance(opts, list) else None,
                        correct_answer=str(s.get("correct_answer", "")),
                        explanation=str(s.get("explanation", "")),
                        typical_mistakes=list(tm) if isinstance(tm, list) else [],
                    )
                    _record_ai("generate", "ok", resp=resp, parse_status="ok")
                    return result
                except (TypeError, ValueError):
                    _record_ai("generate", "ok", resp=resp, parse_status="error")
            # Fallback — текстовое задание
            _record_ai("generate", "ok", resp=resp, parse_status="fallback")
            return GeneratedExercise(
                question_text=resp.content[:500],
                type="text",
                options=None,
                correct_answer="(см. объяснение)",
                explanation=resp.content[:1000],
                typical_mistakes=[],
            )
        except Exception as e:
            _record_ai("generate", "error")
            logger.exception("AI generate failed: %s", e)
            raise

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
        try:
            resp = await self.provider.complete(req)
            _record_ai("chat", "ok", resp=resp)
            return resp
        except Exception as e:
            _record_ai("chat", "error")
            logger.exception("AI chat failed: %s", e)
            raise


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
