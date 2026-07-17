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


@dataclass
class QuizQuestion:
    """Один вопрос квиза (режим mode='quiz').

    Поля совпадают со схемой, которую LLM возвращает в JSON.
    """
    question_text: str
    type: str  # "single" | "multiple" | "numeric" | "text"
    options: list[str] | None
    correct_answer: str
    explanation: str


@dataclass
class Quiz:
    """Набор вопросов, сгенерированных AI для квиза."""
    questions: list[QuizQuestion]


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
        # Sprint 3.5.2: RAG — найти релевантные chunk'и из загруженных учебников
        # и добавить в system prompt как контекст. Без RAG AI отвечает "из головы".
        # Sprint 4.1.3: возвращает (context_str, sources) — sources для UI.
        rag_context, sources = await self._build_rag_context(db, topic)
        system = prompts.explain_topic_system(
            subject.name, topic.name,
            user.student_profile.grade if user.student_profile else 7,
            rag_context=rag_context,
        )
        req = AIRequest(
            messages=[AIMessage(role="system", content=system), AIMessage(role="user", content="Объясни тему.")],
            mode="explain",
            max_tokens=900,
        )
        try:
            resp = await self.provider.complete(req)
            _record_ai("explain", "ok", resp=resp)
            # Sprint 4.1.3: добавляем sources в response для UI индикатора "📖 Источник"
            resp.sources = sources
            return resp
        except Exception as e:
            _record_ai("explain", "error")
            logger.exception("AI explain failed: %s", e)
            raise

    async def _build_rag_context(
        self, db: Session, topic: subj_models.Topic, top_k: int = 3
    ) -> tuple[str | None, list[dict]]:
        """Sprint 3.5.2 + 4.1.3: RAG — топ-K chunk'ов из загруженных учебников.

        Returns:
            (context_str, sources_list) — текст для system prompt + список источников
            для UI (Sprint 4.1.3 — индикатор "📖 Источник").
            context_str = None если RAG пуст (не ошибка, сигнал "материалов по теме нет").
            sources_list = [{"material_title", "page_number", "chunk_id"}, ...]

        Использует hash-based pseudo-embedding (без расходов на embedding API).
        Sprint 3.5.2: persistent search через app.rag_persist.search_persistent
        (читает из rag_chunks в PostgreSQL). RAG-база переживает рестарт backend.
        """
        from app.rag_persist import get_or_compute_embedding, search_persistent

        query = f"{topic.name} {topic.section.subject.name}"
        try:
            query_emb = get_or_compute_embedding(query)
            # Sprint 3.5.2: persistent search через PostgreSQL rag_chunks.
            # Используем db сессию через SessionLocal (self-contained).
            from app.db.session import SessionLocal
            with SessionLocal() as db:
                chunks = search_persistent(db, query_emb, top_k=top_k)
        except Exception as e:
            logger.warning("RAG search failed: %s", e)
            return None, []

        if not chunks:
            return None, []

        # Форматируем chunk'и в читаемый контекст для LLM + собираем sources.
        # app/rag.py::DocumentChunk: id, material_id, text, embedding, metadata.
        # material_title и page_number — в metadata dict.
        lines = ["Контекст из загруженных учебников (top-{} chunk'ов):".format(len(chunks))]
        sources: list[dict] = []
        for i, c in enumerate(chunks, 1):
            meta = getattr(c, "metadata", {}) or {}
            mat_title = meta.get("material_title") or f"Материал {getattr(c, 'material_id', '?')}"
            page = meta.get("page_number")
            text = (getattr(c, "text", "") or "").strip()[:800]
            page_str = f", стр. {page}" if page else ""
            lines.append(f"\n[{i}] {mat_title}{page_str}:\n{text}\n")
            # Sprint 4.1.3: собираем source для UI
            sources.append({
                "chunk_id": getattr(c, "id", None),
                "material_id": getattr(c, "material_id", None),
                "material_title": mat_title,
                "page_number": page,
            })
        return "\n".join(lines), sources

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

    async def generate_quiz(
        self,
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
            resp = await self.provider.complete(req)
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
                                    question_text=str(item.get("question_text", "")),
                                    type=str(item.get("type", "text")),
                                    options=list(opts) if isinstance(opts, list) else None,
                                    correct_answer=str(item.get("correct_answer", "")),
                                    explanation=str(item.get("explanation", "")),
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
                        question_text=resp.content[:500] or "(нет ответа)",
                        type="text",
                        options=None,
                        correct_answer="(см. объяснение)",
                        explanation=resp.content[:1000],
                    )
                ]
            )
        except Exception as e:
            _record_ai("quiz", "error")
            logger.exception("AI quiz failed: %s", e)
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
