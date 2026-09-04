"""Роутер AI-эндпоинтов."""

from __future__ import annotations

from datetime import UTC
from typing import Any

from app.ai.budget import BudgetExceeded, check_and_increment, get_usage
from app.ai.markdown_render import render_markdown
from app.ai.service import get_ai_service
from app.auth.security import get_current_user
from app.common.deps import require_admin
from app.db.session import get_db
from app.subjects import models as subj_models
from app.users import models as user_models
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class ExplainIn(BaseModel):
    topic_id: int


class HintIn(BaseModel):
    question_text: str = Field(min_length=1, max_length=4000)
    level: int = Field(default=1, ge=1, le=3)
    """Sprint 7.4: уровень подсказки (1=наводящий вопрос, 2=подсказка к решению, 3=полный разбор)."""
    # Sprint 4.3.2: optional error_type для context-aware hints.
    # Если указан, hint промпт будет адаптирован под тип ошибки.
    error_type: str | None = Field(default=None)
    """Sprint 4.3.2: тип ошибки от judge (ARITHMETIC/CONCEPTUAL/LOGIC/CARELESS)."""


class CheckIn(BaseModel):
    question_text: str = Field(min_length=1, max_length=4000)
    correct_answer: str = Field(min_length=1, max_length=4000)
    user_answer: str = Field(min_length=1, max_length=4000)


class GenerateIn(BaseModel):
    topic_id: int
    difficulty: int = Field(ge=1, le=5, default=2)


class ChatIn(BaseModel):
    history: list[dict[str, Any]] = Field(default_factory=list, max_length=40)
    topic_id: int | None = None


class CheckOut(BaseModel):
    is_correct: bool
    score: float
    first_error: str | None
    explanation: str
    hint_level: int
    next_difficulty: int
    # Sprint 4.3.1: error_type для context-aware hints.
    error_type: str | None = None


class GeneratedOut(BaseModel):
    question_text: str
    type: str
    options: list[str] | None
    correct_answer: str
    explanation: str
    typical_mistakes: list[str]


class QuizIn(BaseModel):
    topic_id: int
    difficulty: int = Field(ge=1, le=5, default=2)
    count: int = Field(ge=1, le=20, default=5)


class QuestionOut(BaseModel):
    question_text: str
    type: str
    options: list[str] | None
    correct_answer: str
    explanation: str


class UnderstandCheckOut(BaseModel):
    """S3.2 (2026-09-01, D1.4): проверка понимания — 2-3 вопроса «своими словами?».

    Ученик после решения задачи должен объяснить тему своими словами.
    AI задаёт 3 коротких вопроса БЕЗ правильных ответов (Socratic).
    """

    topic_id: int
    subject_name: str
    topic_name: str
    questions: list[str]
    style: str = "questions"


class QuizOut(BaseModel):
    questions: list[QuestionOut]


def _ai_response(
    content: str,
    model: str | None = None,
    sources: list[dict] | None = None,
) -> dict[str, Any]:
    """AI-ответ в формате {content, content_html, model, sources}.

    Sprint 4.1.3: sources — список RAG-источников [{material_title, page_number, ...}]
    для UI индикатора "📖 Источник".
    """
    return {
        "content": content,
        "content_html": render_markdown(content),
        "model": model,
        "sources": sources or [],
    }


def _enforce_budget(current: user_models.User) -> None:
    """AI-budget: 429 если превышен дневной/часовой лимит.

    Sprint 69: admin role bypasses budget (operational necessity).
    Admin/teacher используют AI для debugging и tests,
    обычные users (student/parent) ограничены.

    Sprint 3.9.5: понятные сообщения на русском с указанием времени сброса.
    Кирилл должен понимать: «лимит сбросится в полночь» или
    «лимит сбросится когда кончится текущий час».
    """
    # Sprint 69: admin bypass — только для оперативных нужд (debugging, tests).
    if current.role == user_models.Role.ADMIN:
        return

    try:
        check_and_increment(current.id)
    except BudgetExceeded as e:
        # Формируем человеческое сообщение на русском с указанием сброса.
        from datetime import datetime, timedelta, timezone

        now = datetime.now(UTC)
        if e.limit_kind == "hourly_requests":
            # Лимит сбрасывается в начале следующего часа (TTL 3600 сек).
            # Показываем сколько минут осталось.
            next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            mins_left = max(1, int((next_hour - now).total_seconds() // 60))
            detail = (
                f"Кирилл, ты сделал уже {e.used} запросов за этот час "
                f"(лимит {e.limit}). "
                f"Лимит сбросится через {mins_left} мин, "
                f"когда закончится текущий час."
            )
        elif e.limit_kind == "daily_requests":
            # Лимит сбрасывается в 00:00 UTC (= 03:00 МСК).
            next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            hours_left = max(1, int((next_midnight - now).total_seconds() // 3600))
            detail = (
                f"Кирилл, на сегодня лимит запросов исчерпан "
                f"({e.used}/{e.limit}). "
                f"Сбросится через {hours_left} ч, в 03:00 по Москве."
            )
        elif e.limit_kind == "daily_tokens":
            next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            hours_left = max(1, int((next_midnight - now).total_seconds() // 3600))
            used_k = e.used // 1000
            limit_k = e.limit // 1000
            detail = (
                f"Кирилл, на сегодня лимит слов исчерпан "
                f"({used_k} тыс. из {limit_k} тыс.). "
                f"Сбросится через {hours_left} ч, в 03:00 по Москве."
            )
        elif e.limit_kind == "hourly_tokens":
            next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            mins_left = max(1, int((next_hour - now).total_seconds() // 60))
            used_k = e.used // 1000
            limit_k = e.limit // 1000
            detail = (
                f"Кирилл, за этот час лимит слов исчерпан "
                f"({used_k} тыс. из {limit_k} тыс.). "
                f"Сбросится через {mins_left} мин."
            )
        else:
            detail = f"AI budget exceeded ({e.limit_kind}): {e.used}/{e.limit}. " f"Подожди до сброса лимита."
        raise HTTPException(429, detail)


@router.post("/explain")
async def explain_topic(
    payload: ExplainIn,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    _enforce_budget(current)
    topic = db.get(subj_models.Topic, payload.topic_id)
    if topic is None:
        raise HTTPException(404, "Topic not found")
    svc = get_ai_service()
    resp = await svc.explain_topic(db, current, topic)
    # Sprint 4.1.3: sources для UI индикатора "📖 Источник"
    return _ai_response(resp.content, resp.model, sources=resp.sources)


@router.post("/hint")
async def hint(payload: HintIn, current: user_models.User = Depends(get_current_user)):
    _enforce_budget(current)
    svc = get_ai_service()
    # Sprint 4.3.2: передаём error_type в service для context-aware промпта.
    resp = await svc.hint_at_level(payload.question_text, payload.level, error_type=payload.error_type)
    return _ai_response(resp.content, resp.model)


@router.post("/check-answer", response_model=CheckOut)
async def check_answer(
    payload: CheckIn,
    current: user_models.User = Depends(get_current_user),
):
    _enforce_budget(current)
    svc = get_ai_service()
    res = await svc.check_answer(payload.question_text, payload.correct_answer, payload.user_answer)
    return CheckOut(
        is_correct=res.is_correct,
        score=res.score,
        first_error=res.first_error,
        explanation=res.explanation,
        hint_level=res.hint_level,
        next_difficulty=res.next_difficulty,
        # Sprint 4.3.1: error_type для context-aware hints.
        error_type=res.error_type,
    )


@router.post("/generate-exercise", response_model=GeneratedOut)
async def generate(
    payload: GenerateIn,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    _enforce_budget(current)
    topic = db.get(subj_models.Topic, payload.topic_id)
    if topic is None:
        raise HTTPException(404, "Topic not found")
    svc = get_ai_service()
    gen = await svc.generate_exercise(topic.section.subject.name, topic.name, payload.difficulty, topic_id=topic.id)
    return GeneratedOut(
        question_text=gen.question_text,
        type=gen.type,
        options=gen.options,
        correct_answer=gen.correct_answer,
        explanation=gen.explanation,
        typical_mistakes=gen.typical_mistakes,
    )


@router.post("/quiz", response_model=QuizOut)
async def quiz(
    payload: QuizIn,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    """Сгенерировать квиз (набор разнотипных вопросов) по теме."""
    _enforce_budget(current)
    topic = db.get(subj_models.Topic, payload.topic_id)
    if topic is None:
        raise HTTPException(404, "Topic not found")
    svc = get_ai_service()
    quiz_obj = await svc.generate_quiz(
        topic.section.subject.name,
        topic.name,
        payload.difficulty,
        payload.count,
    )
    return QuizOut(
        questions=[
            QuestionOut(
                question_text=q.question_text,
                type=q.type,
                options=q.options,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
            )
            for q in quiz_obj.questions
        ]
    )


@router.post("/chat")
async def chat(
    payload: ChatIn,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    _enforce_budget(current)
    svc = get_ai_service()
    subject_name = topic_name = None
    if payload.topic_id:
        t = db.get(subj_models.Topic, payload.topic_id)
        if t:
            subject_name = t.section.subject.name
            topic_name = t.name
    resp = await svc.chat(payload.history, subject_name, topic_name)

    # Sprint 3.15: честный questions_to_ai для бейджа asked_question.
    # Инкрементим после УСПЕШНОГО chat (resp получен). Upsert ленивый.
    from app.student.models import UserCounter

    ctr = db.get(UserCounter, current.id)
    if ctr is None:
        ctr = UserCounter(
            user_id=current.id,
            easy_solved=0,
            questions_to_ai=1,
        )
        db.add(ctr)
    else:
        ctr.questions_to_ai = (ctr.questions_to_ai or 0) + 1

    db.commit()

    return _ai_response(resp.content, resp.model)


@router.get("/ping")
async def ping(current: user_models.User = Depends(get_current_user)):
    """Проверка соединения с AI. НЕ возвращает ключ и подробности ошибок."""
    provider = get_ai_service().provider
    ok = await provider.ping()
    return {"ok": ok, "model": getattr(provider, "model_name", None) or getattr(provider, "model", "mock")}


# ============ Sprint 9.4 — admin UI для AI-бюджета ============


@router.get("/budget/usage")
async def my_budget_usage(current: user_models.User = Depends(get_current_user)):
    """Текущее использование AI-бюджета (для UI/отладки)."""
    return get_usage(current.id)


@router.get("/admin/budget/top")
async def admin_top_budget_users(
    current: user_models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Top-N пользователей по использованию AI-бюджета (admin only)."""
    from sqlalchemy import text

    # Прямой SQL запрос к Redis НЕ идеален — поэтому используем метрику Prometheus.
    # Здесь возвращаем текущее использование всех admin/moderator только как заглушку.
    rows = db.execute(
        text(
            "SELECT id, email, role FROM users "
            "WHERE role IN ('admin', 'teacher', 'student', 'parent') "
            "ORDER BY id LIMIT 50"
        )
    ).fetchall()
    result = []
    for row in rows:
        uid, email, role = row
        result.append({"user_id": uid, "email": email, "role": role, "usage": get_usage(uid)})
    return result


# === Sprint 4.3.3: A/B testing метрики для context-aware hints ===


class HintMetricIn(BaseModel):
    topic_id: int
    error_type: str | None = None
    hint_level: int
    attempt_id: int | None = None
    time_to_solve_ms: int | None = None
    retry_count: int = 0
    hint_text: str | None = None
    success: bool = False


@router.post("/hint-metrics")
def record_hint_metric(
    payload: HintMetricIn,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    """Sprint 4.3.3: записывает метрику использования hint в БД.

    Поля:
    - error_type (от judge): ARITHMETIC/CONCEPTUAL/LOGIC/CARELESS
    - hint_level (1-3): какой уровень подсказки показал
    - time_to_solve_ms: сколько миллисекунд ученик потратил после подсказки
    - retry_count: сколько раз попытался после подсказки
    - success: решил или нет

    Использование: SELECT error_type, hint_level, COUNT(*) FILTER (WHERE success) ...
    """
    try:
        from sqlalchemy import text as sa_text

        db.execute(
            sa_text(
                "INSERT INTO hint_metrics (user_id, topic_id, error_type, hint_level, "
                "attempt_id, time_to_solve_ms, retry_count, hint_text, success) "
                "VALUES (:user_id, :topic_id, :error_type, :hint_level, "
                ":attempt_id, :time_to_solve_ms, :retry_count, :hint_text, :success)"
            ),
            {
                "user_id": current.id,
                "topic_id": payload.topic_id,
                "error_type": payload.error_type,
                "hint_level": payload.hint_level,
                "attempt_id": payload.attempt_id,
                "time_to_solve_ms": payload.time_to_solve_ms,
                "retry_count": payload.retry_count,
                "hint_text": payload.hint_text[:500] if payload.hint_text else None,
                "success": payload.success,
            },
        )
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        import logging

        logging.getLogger(__name__).warning("hint_metrics insert failed: %s", e)
        # Не падаем — это аналитика, не критично.
        return {"ok": False, "error": str(e)[:100]}


@router.get("/hint-metrics/summary")
def hint_metrics_summary(
    topic_id: int | None = None,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    """Sprint 4.3.3: агрегированные метрики для admin/teacher.

    Возвращает success_rate и avg_retry_count по (error_type, hint_level).
    """
    from sqlalchemy import text as sa_text

    where = ""
    params: dict = {}
    if topic_id is not None:
        where = "WHERE topic_id = :topic_id"
        params["topic_id"] = topic_id

    rows = db.execute(
        sa_text(
            f"SELECT error_type, hint_level, COUNT(*) AS total, "
            f"COUNT(*) FILTER (WHERE success) AS succeeded, "
            f"AVG(time_to_solve_ms) FILTER (WHERE time_to_solve_ms IS NOT NULL) AS avg_time, "
            f"AVG(retry_count) AS avg_retries "
            f"FROM hint_metrics {where} "
            f"GROUP BY error_type, hint_level "
            f"ORDER BY error_type, hint_level"
        ),
        params,
    ).fetchall()

    return [
        {
            "error_type": r[0],
            "hint_level": r[1],
            "total": r[2],
            "succeeded": r[3],
            "success_rate": (r[3] / r[2]) if r[2] else 0.0,
            "avg_time_ms": int(r[4]) if r[4] else None,
            "avg_retries": float(r[5]) if r[5] else 0.0,
        }
        for r in rows
    ]


@router.get("/understand-check/{topic_id}", response_model=UnderstandCheckOut)
async def understand_check(
    topic_id: int,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
) -> UnderstandCheckOut:
    """S3.2 (2026-09-01, D1.4): проверка понимания после успешного ответа.

    Возвращает 3 коротких вопроса «своими словами?» (Socratic).
    Бюджет НЕ расходуется: вопросы генерируются из prompts шаблона без AI-провайдера,
    чтобы не съедать 20/час на побочные проверки.
    """
    topic = db.get(subj_models.Topic, topic_id)
    if topic is None:
        raise HTTPException(404, "Topic not found")
    questions = _socratic_questions_for(topic.section.subject.name, topic.name)
    return UnderstandCheckOut(
        topic_id=topic.id,
        subject_name=topic.section.subject.name,
        topic_name=topic.name,
        questions=questions,
        style="questions",
    )


def _socratic_questions_for(subject_name: str, topic_name: str) -> list[str]:
    """S3.2: 3 вопроса «своими словами?» (deterministic, без AI).

    Использует 3 шаблона, чтобы ученик мог объяснить тему тремя способами:
    - "Объясни своими словами..."
    - "Приведи пример из жизни..."
    - "Где это пригодится?"
    """
    return [
        f"Объясни своими словами, в чём суть темы «{topic_name}» по предмету «{subject_name}».",
        f"Приведи пример из жизни или из игры, где встречается «{topic_name}».",
        f"Где ещё пригодится «{topic_name}»? Зачем взрослому это знать?",
    ]


@router.post("/understand-check-ai/{topic_id}", response_model=UnderstandCheckOut)
async def understand_check_ai(
    topic_id: int,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
) -> UnderstandCheckOut:
    """S3.2 advanced (2026-09-01, D1.4): AI-сгенерированные Socratic вопросы.

    Использует prompts.explain_topic_system(style="questions") для
    динамических вопросов «своими словами?» — расходует AI-бюджет.
    Лучше для personalized обучения, но дороже.
    """
    from app.ai import _thread_local
    from app.ai import prompts as _prompts

    _thread_local.explain_style = "questions"

    topic = db.get(subj_models.Topic, topic_id)
    if topic is None:
        raise HTTPException(404, "Topic not found")
    _enforce_budget(current)
    svc = get_ai_service()
    try:
        from app.ai.explain_runner import run_explain as _run_explain  # type: ignore
    except ImportError:
        _run_explain = None  # type: ignore

    subject = topic.section.subject
    grade = current.student_profile.grade if current.student_profile else 7
    sys_prompt = _prompts.explain_topic_system(subject.name, topic.name, grade, rag_context=None, style="questions")
    req = _build_request(sys_prompt, "Дай 3 коротких вопроса на проверку понимания.")
    res = await svc.provider.complete(req)

    return UnderstandCheckOut(
        topic_id=topic.id,
        subject_name=subject.name,
        topic_name=topic.name,
        questions=_parse_questions(res.content),
        style="questions",
    )


def _build_request(sys_prompt: str, user_msg: str):
    """S3.2: локальный билдер AIRequest (избегаем circular import)."""
    from app.ai.models import AIMessage, AIRequest

    return AIRequest(
        messages=[AIMessage(role="system", content=sys_prompt), AIMessage(role="user", content=user_msg)],
        mode="explain",
        max_tokens=300,
    )


def _parse_questions(content: str) -> list[str]:
    """S3.2: парсим AI-output в список вопросов (по строкам/нумерации)."""
    import re

    # Strip code blocks and JSON; ищем строки, начинающиеся с 1./1)/•/-/?.
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    out: list[str] = []
    for line in lines:
        m = re.match(r"^(?:\d+[.)]|[•\-?])\s+(.+)", line)
        if m and len(m.group(1)) > 3:
            out.append(m.group(1))
        if len(out) >= 5:  # hard cap
            break
    if not out:
        # Fallback: первая non-empty строка как один вопрос
        out = [content.strip().split("\n")[0][:500]] if content.strip() else ["Объясни своими словами эту тему."]
    return out[:3]
