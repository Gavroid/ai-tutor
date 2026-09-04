"""Sprint 3.29: explain_topic moved from app.ai.service.AIService.

Behavioral identity (zero change). Public API: AIService.explain_topic
по-прежнему работает через 1-line forwarding (см. AIService.explain_topic).

Все внутренние ссылки заменены self.X → service.X.
Эта функция принимает `service` (AIService instance) как первый аргумент
для shared state (provider, _settings).
"""
from __future__ import annotations

import logging
from typing import Any

from app.ai import prompts
from app.ai.service import (
    _clean_student_visible_text,
    _fallback_explanation,
    _record_ai,
    _verified_rag_sources,
)
from app.ai.types import AIMessage, AIRequest, AIResponse
from app.subjects import models as subj_models
from app.users import models as user_models
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def explain_topic(
    service,
    db: Session,
    user: user_models.User,
    topic: subj_models.Topic,
) -> AIResponse:
    """Sprint 3.29: вырезано из AIService.explain_topic (90 строк, body only).

    Поведение идентично оригиналу. Все вызовы self.* перенаправлены на
    service.* (AIService instance). Backward compat: AIService.explain_topic
    делает 1-line `return await explain_topic(self, db, user, topic)`.
    """
    subject = topic.section.subject
    rag_context: str | None = ""
    sources: list[dict[str, Any]] = []
    try:
        rag_context, sources = await service._build_rag_context(db, topic)
    except Exception as e:
        _record_ai("explain", "rag_error")
        logger.warning("AI explain RAG failure → fallback (no RAG context): %r", e)
        rag_context, sources = None, []
    from app.ai import _thread_local

    style = getattr(_thread_local, "explain_style", "default")
    system = prompts.explain_topic_system(
        subject.name,
        topic.name,
        user.student_profile.grade if user.student_profile else 7,
        rag_context=rag_context,
        style=style,
    )
    req = AIRequest(
        messages=[AIMessage(role="system", content=system), AIMessage(role="user", content="Объясни тему.")],
        mode="explain",
        max_tokens=900,
    )
    resp = None
    try:
        resp, used_label = await service._complete_with_fallback(db, subject.id, req)
        resp.content = _clean_student_visible_text(resp.content)
        used_fallback = False
        if len(resp.content.strip()) < 250:
            retry_req = AIRequest(
                messages=req.messages + [
                    AIMessage(
                        role="user",
                        content="Ответ слишком короткий. Дай полноценное объяснение: определение, правило, пример и проверочный вопрос. Не обрывай фразы.",
                    )
                ],
                mode="explain",
                max_tokens=1100,
                temperature=0.4,
            )
            retry_resp = await service.provider.complete(retry_req)
            retry_resp.content = _clean_student_visible_text(retry_resp.content)
            if len(retry_resp.content.strip()) >= 250:
                resp = retry_resp
            else:
                resp.content = _fallback_explanation(subject.name, topic.name)
                used_fallback = True
    except Exception as e:
        _record_ai("explain", "error")
        logger.warning("AI explain provider failure → fallback: %s", e)
        fallback = AIResponse(
            content=_fallback_explanation(subject.name, topic.name),
            model="fallback",
            sources=[],
        )
        _record_ai("explain", "ok", resp=fallback)
        resp = fallback

    topic_id = getattr(topic, "id", None)
    verified_sources = (
        _verified_rag_sources(sources, topic_id=topic_id, topic_name=topic.name)
        if topic_id is not None
        else []
    )
    if getattr(user, "role", None) == "student":
        verified_sources = []
    resp.sources = verified_sources
    return resp
