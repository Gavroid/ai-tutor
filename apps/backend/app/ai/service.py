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
from typing import Any

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
    # Sprint 4.3.1: тип ошибки для context-aware hints.
    # ARITHMETIC/CONCEPTUAL/LOGIC/CARELESS или None если ответ правильный.
    error_type: str | None = None


@dataclass
class GeneratedExercise:
    question_text: str
    type: str
    options: list[str] | None
    correct_answer: str
    explanation: str
    typical_mistakes: list[str]



def _rag_enabled_for_subject(subject_name: str) -> bool:
    """MVP: RAG materials are currently indexed only for 6th-grade math repeat subject."""
    normalized = subject_name.lower()
    return "математика" in normalized and "6" in normalized and "повтор" in normalized


def _dedupe_rag_sources(sources: list[dict]) -> list[dict]:
    """Deduplicate source display by material title + page."""
    seen: set[tuple[str, object]] = set()
    result: list[dict] = []
    for source in sources:
        key = (str(source.get("material_title") or ""), source.get("page_number"))
        if key in seen:
            continue
        seen.add(key)
        result.append(source)
    return result


def _fallback_explanation(subject_name: str, topic_name: str) -> str:
    """Safe explanation fallback when the model returns only stripped reasoning/empty text."""
    subject_lower = subject_name.lower()
    topic_lower = topic_name.lower()
    if "математика" in subject_lower and "десятич" in topic_lower:
        return (
            f"**{topic_name}** — это вычисления с числами, у которых есть запятая.\n\n"
            "### Главное правило\n"
            "- При сложении и вычитании записывай запятую под запятой: `2,5 + 0,8 = 3,3`.\n"
            "- При умножении сначала умножай как целые числа, потом верни запятую: `0,6 × 0,4 = 0,24`.\n"
            "- При делении на целое число дели как обычно и ставь запятую в частном: `7,2 : 3 = 2,4`.\n\n"
            "### Пример\n"
            "Вычислим `1,2 × 0,5`: считаем `12 × 5 = 60`; всего два знака после запятой, значит ответ `0,60 = 0,6`.\n\n"
            "### Проверь себя\n"
            "Сколько будет `0,5 × 0,3`?"
        )
    if "математика" in subject_lower and "дроб" in topic_lower:
        return (
            f"**{topic_name}** — это действия с частями целого.\n\n"
            "### Главное правило\n"
            "- Если знаменатели одинаковые, складываем или вычитаем только числители: `1/7 + 3/7 = 4/7`.\n"
            "- Если знаменатели разные, сначала приводим дроби к общему знаменателю: `1/2 + 1/3 = 3/6 + 2/6 = 5/6`.\n"
            "- При умножении дробей умножаем числитель на числитель, знаменатель на знаменатель: `2/3 × 3/5 = 6/15 = 2/5`.\n"
            "- При делении умножаем на обратную дробь: `2/3 : 4/5 = 2/3 × 5/4 = 10/12 = 5/6`.\n\n"
            "### Пример\n"
            "Вычислим `1/4 + 2/4`: знаменатель уже одинаковый, значит `1 + 2 = 3`, ответ `3/4`.\n\n"
            "### Проверь себя\n"
            "Почему нельзя складывать знаменатели напрямую? Например, почему `1/2 + 1/3` — это не `2/5`?"
        )
    return (
        f"**{topic_name}** — тема по предмету «{subject_name}».\n\n"
        "Коротко: начни с определения темы, затем разбери один простой пример "
        "и проверь себя вопросом: что здесь главное правило или смысл?\n\n"
        "Если хочешь, нажми «Практика» — я дам задание по этой теме."
    )


def _exercise_matches_topic(exercise: GeneratedExercise, topic_name: str) -> bool:
    """Reject common provider drift where a valid JSON task belongs to another topic."""
    topic_lower = topic_name.lower()
    question_lower = exercise.question_text.lower()
    blob = "\n".join([exercise.question_text, exercise.correct_answer, exercise.explanation]).lower()
    if "десятич" in topic_lower:
        if "1/2" in blob or "1/3" in blob or "обыкновенн" in blob:
            return False
        return "," in question_lower or "десятич" in question_lower or "0," in question_lower
    if "обыкнов" in topic_lower or "дроб" in topic_lower:
        return "/" in blob or "дроб" in blob
    return True


_ALLOWED_EXERCISE_TYPES = {"single", "multiple", "numeric", "text", "fill", "code"}


def _clean_ai_text(value: Any) -> str:
    return str(value or "").strip()


def _valid_generated_exercise(data: dict[str, Any]) -> GeneratedExercise:
    """Validate model JSON before it becomes a student-facing exercise."""
    question_text = _clean_ai_text(data.get("question_text"))
    exercise_type = _clean_ai_text(data.get("type") or "text")
    correct_answer = _clean_ai_text(data.get("correct_answer"))
    explanation = _clean_ai_text(data.get("explanation"))

    lowered_blob = "\n".join([question_text, correct_answer, explanation]).lower()
    if (
        len(question_text) < 10
        or "<think" in lowered_blob
        or "&lt;think" in lowered_blob
        or not correct_answer
        or correct_answer == "(см. объяснение)"
        or exercise_type not in _ALLOWED_EXERCISE_TYPES
    ):
        raise ValueError("AI did not return a valid structured exercise")

    raw_options = data.get("options")
    options = [str(item).strip() for item in raw_options if str(item).strip()] if isinstance(raw_options, list) else None
    if exercise_type in {"single", "multiple"} and (not options or len(options) < 2):
        raise ValueError("AI did not return a valid structured exercise")

    raw_mistakes = data.get("typical_mistakes", [])
    typical_mistakes = (
        [str(item).strip() for item in raw_mistakes if str(item).strip()]
        if isinstance(raw_mistakes, list)
        else []
    )
    return GeneratedExercise(
        question_text=question_text,
        type=exercise_type,
        options=options,
        correct_answer=correct_answer,
        explanation=explanation,
        typical_mistakes=typical_mistakes,
    )


def _fallback_generated_exercise(
    subject_name: str,
    topic_name: str,
    difficulty: int,
) -> GeneratedExercise:
    """Safe deterministic fallback when the model does not return usable JSON."""
    subject_lower = subject_name.lower()
    topic_lower = topic_name.lower()
    if "математика" in subject_lower and "среднее арифметическое" in topic_lower:
        return GeneratedExercise(
            question_text="Найди среднее арифметическое чисел 8, 9 и 4. Выбери правильный ответ.",
            type="single",
            options=["7", "8", "6", "21"],
            correct_answer="7",
            explanation="Складываем числа: 8 + 9 + 4 = 21. Делим сумму на количество чисел: 21 : 3 = 7.",
            typical_mistakes=["Забыть разделить сумму на количество чисел", "Взять только самое большое число"],
        )

    if "математика" in subject_lower and "кругов" in topic_lower and "диаграм" in topic_lower:
        return GeneratedExercise(
            question_text="На круговой диаграмме сектор занимает 25% всего круга. Какой угол у этого сектора?",
            type="single",
            options=["90°", "45°", "25°", "180°"],
            correct_answer="90°",
            explanation="Весь круг — это 360°. 25% — это четверть круга, значит 360° : 4 = 90°.",
            typical_mistakes=["Путать проценты и градусы", "Забыть, что полный круг — 360°"],
        )

    if "математика" in subject_lower and "разложение" in topic_lower and "прост" in topic_lower:
        return GeneratedExercise(
            question_text="Разложи число 36 на простые множители. Выбери правильный вариант.",
            type="single",
            options=["2² × 3²", "2 × 18", "4 × 9", "6 × 6"],
            correct_answer="2² × 3²",
            explanation="36 делится на 2: 36 = 2 × 18. Ещё раз на 2: 18 = 2 × 9. А 9 = 3 × 3. Значит 36 = 2² × 3².",
            typical_mistakes=["Остановиться на составных множителях 4 и 9", "Забыть, что множители должны быть простыми"],
        )

    if "математика" in subject_lower and "наибольш" in topic_lower and "делител" in topic_lower:
        return GeneratedExercise(
            question_text="Найди наибольший общий делитель чисел 18 и 24. Выбери ответ.",
            type="single",
            options=["6", "3", "12", "8"],
            correct_answer="6",
            explanation="Делители 18: 1, 2, 3, 6, 9, 18. Делители 24: 1, 2, 3, 4, 6, 8, 12, 24. Самый большой общий делитель — 6.",
            typical_mistakes=["Выбрать общий делитель, но не самый большой", "Перепутать НОД и НОК"],
        )

    if "математика" in subject_lower and "наимень" in topic_lower and "кратн" in topic_lower:
        return GeneratedExercise(
            question_text="Найди наименьшее общее кратное чисел 6 и 8. Выбери ответ.",
            type="single",
            options=["24", "48", "14", "12"],
            correct_answer="24",
            explanation="Кратные 6: 6, 12, 18, 24. Кратные 8: 8, 16, 24. Первое общее кратное — 24.",
            typical_mistakes=["Выбрать произведение 6 × 8 без проверки", "Перепутать НОК и НОД"],
        )

    if "математика" in subject_lower and "приведение" in topic_lower and "знаменател" in topic_lower:
        return GeneratedExercise(
            question_text="К какому наименьшему общему знаменателю удобно привести дроби 1/3 и 1/4?",
            type="single",
            options=["12", "7", "6", "24"],
            correct_answer="12",
            explanation="Общий знаменатель должен делиться и на 3, и на 4. Наименьшее такое число — 12.",
            typical_mistakes=["Сложить знаменатели 3 + 4", "Взять общий знаменатель больше нужного без необходимости"],
        )

    if "математика" in subject_lower and "сложение и вычитание смешанных" in topic_lower:
        return GeneratedExercise(
            question_text="Вычисли: 2 1/3 + 1 1/3. Выбери ответ.",
            type="single",
            options=["3 2/3", "3 1/3", "4 2/3", "2 2/3"],
            correct_answer="3 2/3",
            explanation="Складываем целые части: 2 + 1 = 3. Складываем дробные части: 1/3 + 1/3 = 2/3. Ответ: 3 2/3.",
            typical_mistakes=["Сложить знаменатели", "Забыть отдельно сложить целые части"],
        )

    if "математика" in subject_lower and "умножение смешанных" in topic_lower:
        return GeneratedExercise(
            question_text="Вычисли: 1 1/2 × 2. Выбери ответ.",
            type="single",
            options=["3", "2 1/2", "1", "4"],
            correct_answer="3",
            explanation="1 1/2 = 3/2. Умножаем: 3/2 × 2 = 3.",
            typical_mistakes=["Умножить только дробную часть", "Не перевести смешанное число в неправильную дробь"],
        )

    if "математика" in subject_lower and "нахождение дроби от числа" in topic_lower:
        return GeneratedExercise(
            question_text="Найди 3/4 от числа 20. Выбери ответ.",
            type="single",
            options=["15", "12", "10", "16"],
            correct_answer="15",
            explanation="Чтобы найти 3/4 от 20, делим 20 на 4 и умножаем на 3: 20 : 4 = 5, 5 × 3 = 15.",
            typical_mistakes=["Умножить только на знаменатель", "Забыть умножить на числитель"],
        )

    if "математика" in subject_lower and "деление смешанных" in topic_lower:
        return GeneratedExercise(
            question_text="Вычисли: 3 1/2 ÷ 1/2. Выбери ответ.",
            type="single",
            options=["7", "3", "6", "1 3/4"],
            correct_answer="7",
            explanation="3 1/2 = 7/2. Деление на 1/2 заменяем умножением на 2: 7/2 × 2 = 7.",
            typical_mistakes=["Не перевернуть вторую дробь", "Работать отдельно с целой частью"],
        )

    if "математика" in subject_lower and topic_lower.strip() == "отношения":
        return GeneratedExercise(
            question_text="В классе 18 мальчиков и 12 девочек. Каково отношение мальчиков к девочкам после сокращения?",
            type="single",
            options=["3:2", "2:3", "18:12", "6:4"],
            correct_answer="3:2",
            explanation="Отношение 18:12 можно сократить на 6. Получаем 3:2.",
            typical_mistakes=["Не сократить отношение", "Перепутать порядок: мальчики к девочкам"],
        )

    if "математика" in subject_lower and ("процент" in topic_lower or "проценты" in topic_lower):
        return GeneratedExercise(
            question_text="Найди 20% от 150. Выбери правильный ответ.",
            type="single",
            options=["30", "20", "75", "300"],
            correct_answer="30",
            explanation="20% = 0,2. Значит 150 × 0,2 = 30.",
            typical_mistakes=["Делить на 20 вместо умножения на 0,2", "Путать 20% и 20"],
        )

    if "математика" in subject_lower and "пропорц" in topic_lower:
        return GeneratedExercise(
            question_text="Реши пропорцию: x/5 = 12/3. Выбери x.",
            type="single",
            options=["20", "15", "4", "60"],
            correct_answer="20",
            explanation="12/3 = 4, значит x/5 = 4. Умножаем обе части на 5: x = 20.",
            typical_mistakes=["Перемножить не те члены пропорции", "Забыть умножить на 5"],
        )

    if "математика" in subject_lower and "уравнен" in topic_lower:
        return GeneratedExercise(
            question_text="Реши уравнение: 2x + 3 = 11. Выбери x.",
            type="single",
            options=["4", "7", "5", "14"],
            correct_answer="4",
            explanation="Сначала вычитаем 3: 2x = 8. Затем делим на 2: x = 4.",
            typical_mistakes=["Не перенести 3 в другую часть", "Забыть разделить на 2"],
        )

    if "математика" in subject_lower and "десятич" in topic_lower:
        return GeneratedExercise(
            question_text="Вычисли: 0,6 × 0,4. Выбери правильный ответ.",
            type="single",
            options=["0,24", "2,4", "0,024", "24"],
            correct_answer="0,24",
            explanation=(
                "Умножаем как целые числа: 6 × 4 = 24. "
                "В множителях 0,6 и 0,4 вместе два знака после запятой, поэтому ответ 0,24."
            ),
            typical_mistakes=[
                "Забыть посчитать знаки после запятой",
                "Поставить запятую сразу после первой цифры без проверки",
            ],
        )

    if "математика" in subject_lower and "дроб" in topic_lower:
        return GeneratedExercise(
            question_text="Вычисли: 1/2 + 1/3. Выбери правильный ответ.",
            type="single",
            options=["5/6", "2/5", "2/6", "1/5"],
            correct_answer="5/6",
            explanation=(
                "Чтобы сложить 1/2 и 1/3, приводим дроби к общему знаменателю 6: "
                "1/2 = 3/6, 1/3 = 2/6, значит 3/6 + 2/6 = 5/6."
            ),
            typical_mistakes=[
                "Складывать знаменатели напрямую",
                "Не приводить дроби к общему знаменателю",
            ],
        )

    prompt = (
        f"Сформулируй короткий ответ по теме «{topic_name}» "
        f"({subject_name}, сложность {difficulty}/5)."
    )
    return GeneratedExercise(
        question_text=prompt,
        type="text",
        options=None,
        correct_answer=f"Короткое объяснение по теме «{topic_name}» своими словами.",
        explanation="Попробуй ответить своими словами: назови главное правило темы и приведи короткий пример.",
        typical_mistakes=["Копировать определение без понимания", "Отвечать слишком общо"],
    )


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
            used_fallback = False
            if not resp.content.strip():
                resp.content = _fallback_explanation(subject.name, topic.name)
                used_fallback = True
            _record_ai("explain", "ok", resp=resp)
            # MVP rescue: source snippets are not reliable enough yet for student-facing citation.
            # Keep RAG context for grounding, but do not show a misleading page link in UI.
            resp.sources = []
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

        subject = topic.section.subject
        if not _rag_enabled_for_subject(subject.name):
            return None, []
        # Sprint 3.5.2 + MVP rescue: RAG только для предмета, где материалы реально загружены.
        query = f"{topic.name} {topic.section.subject.name}"
        try:
            query_emb = get_or_compute_embedding(query)
            # Sprint 3.5.2: persistent search через PostgreSQL rag_chunks.
            # Используем db сессию через SessionLocal (self-contained).
            from app.db.session import SessionLocal
            with SessionLocal() as db:
                chunks = search_persistent(db, query_emb, top_k=top_k)
                chunks = [
                    c for c in chunks
                    if (getattr(c, "metadata", {}) or {}).get("topic_id") == topic.id
                ]
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
        return "\n".join(lines), _dedupe_rag_sources(sources)

    async def hint(self, question_text: str, level: int = 1) -> AIResponse:
        """Sprint 7.4: подсказка уровня 1 (наводящий вопрос).

        Для уровней 2/3 используй hint_at_level().
        """
        return await self._hint_with_level(question_text, level=1)

    async def hint_at_level(self, question_text: str, level: int, error_type: str | None = None) -> AIResponse:
        """Sprint 7.4 + 4.3.2: подсказка уровня 1..3 с учётом типа ошибки.

        error_type (опционально): ARITHMETIC/CONCEPTUAL/LOGIC/CARELESS от judge.
        Если указан — промпт адаптируется под тип ошибки.
        """
        return await self._hint_with_level(question_text, level=level, error_type=error_type)

    async def _hint_with_level(self, question_text: str, level: int, error_type: str | None = None) -> AIResponse:
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
                        # Sprint 4.3.1: error_type для context-aware hints.
                        # Валидируем чтобы не принимать мусор от LLM.
                        error_type=resp.structured.get("error_type") if resp.structured.get("error_type") in ("ARITHMETIC", "CONCEPTUAL", "LOGIC", "CARELESS") else None,
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
                try:
                    result = _valid_generated_exercise(resp.structured)
                    if not _exercise_matches_topic(result, topic_name):
                        _record_ai("generate", "ok", resp=resp, parse_status="fallback")
                        return _fallback_generated_exercise(subject_name, topic_name, difficulty)
                    _record_ai("generate", "ok", resp=resp, parse_status="ok")
                    return result
                except (TypeError, ValueError):
                    _record_ai("generate", "ok", resp=resp, parse_status="error")
                    raise ValueError("AI did not return a valid structured exercise")
            _record_ai("generate", "ok", resp=resp, parse_status="fallback")
            return _fallback_generated_exercise(subject_name, topic_name, difficulty)
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
