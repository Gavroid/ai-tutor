"""Роутер AI-эндпоинтов."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.budget import BudgetExceeded, check_and_increment, get_usage
from app.ai.markdown_render import render_markdown
from app.ai.service import get_ai_service
from app.auth.security import get_current_user
from app.common.deps import require_admin
from app.db.session import get_db
from app.subjects import models as subj_models
from app.users import models as user_models

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class ExplainIn(BaseModel):
    topic_id: int


class HintIn(BaseModel):
    question_text: str = Field(min_length=1, max_length=4000)


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


class GeneratedOut(BaseModel):
    question_text: str
    type: str
    options: list[str] | None
    correct_answer: str
    explanation: str
    typical_mistakes: list[str]


def _ai_response(content: str, model: str | None = None) -> dict[str, Any]:
    """AI-ответ в формате {content, content_html, model}."""
    return {
        "content": content,
        "content_html": render_markdown(content),
        "model": model,
    }


def _enforce_budget(current: user_models.User) -> None:
    """AI-budget: 429 если превышен дневной лимит."""
    try:
        check_and_increment(current.id)
    except BudgetExceeded as e:
        raise HTTPException(
            429,
            f"AI budget exceeded ({e.limit_kind}): {e.used}/{e.limit} (24h). "
            f"Подожди до завтра или попроси администратора увеличить лимит.",
        )


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
    return _ai_response(resp.content, resp.model)


@router.post("/hint")
async def hint(payload: HintIn, current: user_models.User = Depends(get_current_user)):
    _enforce_budget(current)
    svc = get_ai_service()
    resp = await svc.hint(payload.question_text)
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
    gen = await svc.generate_exercise(topic.section.subject.name, topic.name, payload.difficulty)
    return GeneratedOut(
        question_text=gen.question_text,
        type=gen.type,
        options=gen.options,
        correct_answer=gen.correct_answer,
        explanation=gen.explanation,
        typical_mistakes=gen.typical_mistakes,
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
