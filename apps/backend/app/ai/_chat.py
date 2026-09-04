"""Sprint 3.29: chat method moved from AIService.

Behavioral identity (zero change). Function-based extraction pattern
(см. Sprint 3.29 step 1 commit 2fd6fc5).

Public API: AIService.chat остался через 1-line forwarding.
"""
from __future__ import annotations

import logging

from app.ai import prompts, sanitize
from app.ai.service import _clean_student_visible_text, _record_ai, _trim_incomplete_trailing_fragment
from app.ai.types import AIMessage, AIRequest, AIResponse
from app.users import models as user_models

logger = logging.getLogger(__name__)


async def chat(
    service,
    history: list[dict],
    subject_name: str | None = None,
    topic_name: str | None = None,
) -> AIResponse:
    """Свободный диалог с AI-репетитором.

    S3.4 + S3.5 (2026-09-01, D4.2 + D2.3): использует chat_with_guards_system
    с offtopic-guard (мягкий разворот к учёбе) и honest refuse («пока не умею»).
    Также: pre-AI эвристика is_likely_offtopic() отдаёт короткий стандартный
    разворот без обращения к провайдеру для явно offtopic-сообщений
    (экономия AI-бюджета на 20/час, D5.1).
    """
    # S3.4 pre-filter: если последнее user-сообщение явно offtopic — сразу
    # мягкий разворот, без вызова провайдера.
    last_user_msg = next(
        (m.get("content", "") for m in reversed(history) if m.get("role") == "user"),
        "",
    )
    if prompts.is_likely_offtopic(last_user_msg):
        return AIResponse(
            content=(
                "Это интересно, но я помогаю только с учёбой. "
                "Может, посмотрим задачу по теме, которую сейчас проходим? "
                "Нажми «Объясни тему» или «Дай задание»."
            ),
            model="offtopic-guard",
            sources=[],
        )

    sys = prompts.chat_with_guards_system(subject_name, topic_name)
    msgs: list[AIMessage] = [AIMessage(role="system", content=sys)]
    for m in history:
        r = m.get("role")
        c = sanitize.sanitize_user_input(m.get("content", ""), service._settings.ai_max_input_chars)
        if r in ("user", "assistant") and c:
            msgs.append(AIMessage(role=r, content=c))
    req = AIRequest(messages=msgs, mode="chat", max_tokens=900)
    try:
        resp = await service.provider.complete(req)
        resp.content = _trim_incomplete_trailing_fragment(_clean_student_visible_text(resp.content))
        _record_ai("chat", "ok", resp=resp)
        return resp
    except Exception as e:
        _record_ai("chat", "error")
        logger.warning("AI chat provider failure → fallback: %s", e)
        topic_label = topic_name or "этой темы"
        return AIResponse(
            content=(
                f"Сейчас репетитор временно недоступен. Но мы можем продолжить тему «{topic_label}»: "
                "нажми «Ещё пример» или «Практика», чтобы закрепить правило."
            ),
            model="fallback",
            sources=[],
        )

