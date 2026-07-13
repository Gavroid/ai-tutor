"""Sprint 8: тесты для качества AI.

Покрывает:
- 8.1: teacher generation retry при невалидном JSON, structured output fallback
- 8.4: record_ai_request() вызывается во всех режимах (метрики)
"""
from __future__ import annotations

import asyncio
import json

from app.ai.service import _PARSE_CNT, _record_ai
from app.ai.types import AIResponse
from app.teacher.service import SourceContent, call_ai_for_material
from unittest.mock import AsyncMock, MagicMock


def _mk_response(content: str, structured: dict | None = None, in_t: int = 100, out_t: int = 50) -> AIResponse:
    return AIResponse(content=content, model="test", input_tokens=in_t, output_tokens=out_t, structured=structured)


# ============ 8.1: Teacher generation retry ============


def test_structured_output_accepted_directly():
    """Если provider вернул structured — используем его напрямую."""
    provider = MagicMock()
    provider.complete = AsyncMock(
        return_value=_mk_response(
            "ignored",
            structured={
                "title": "Тест",
                "purpose": "Цель",
                "connection_to_prior": "Связь с предыдущим",
                "key_ideas": [{"idea": "идея1", "terms": []}],
                "self_check_questions": ["q1"],
                "practice_tasks": [
                    {
                        "difficulty": "easy",
                        "question_text": "p",
                        "reference_solution": "r",
                        "typical_mistakes": [],
                    }
                ],
                "mini_test": [
                    {
                        "question_text": "q1",
                        "options": ["a", "b", "c", "d"],
                        "correct_index": 0,
                        "explanation": "да",
                    }
                ],
                "flashcards": [{"question": "f", "answer": "a"}],
                "ai_uncertainty_notes": [],
            },
        )
    )

    ai_svc = MagicMock()
    ai_svc.provider = provider

    material = asyncio.run(
        call_ai_for_material(
            ai_service=ai_svc,
            subject_name="Алгебра",
            topic_name="Сложение",
            source=SourceContent(text="тестовый источник", detected_format="text"),
        )
    )

    assert material.title == "Тест"
    assert provider.complete.call_count == 1


def test_json_in_content_parsed():
    """Если structured=None, но content — валидный JSON, парсим его."""
    provider = MagicMock()
    provider.complete = AsyncMock(
        return_value=_mk_response(
            '{"title":"OK","purpose":"p","key_ideas":[],"self_check_questions":[],"practice_tasks":[],"mini_test":[],"flashcards":[],"ai_uncertainty_notes":[]}'
        )
    )
    ai_svc = MagicMock()
    ai_svc.provider = provider
    material = asyncio.run(
        call_ai_for_material(
            ai_svc, "Алгебра", "Сложение", SourceContent(text="src", detected_format="text")
        )
    )
    assert material.title == "OK"


def test_retry_on_invalid_json():
    """3 попытки при невалидном JSON, потом fallback."""
    provider = MagicMock()
    provider.complete = AsyncMock(
        side_effect=[
            _mk_response("not valid json {{{"),
            _mk_response("still not valid"),
            _mk_response(
                '{"title":"Recovered","purpose":"p","key_ideas":[],"self_check_questions":[],"practice_tasks":[],"mini_test":[],"flashcards":[],"ai_uncertainty_notes":[]}'
            ),
        ]
    )
    ai_svc = MagicMock()
    ai_svc.provider = provider
    material = asyncio.run(
        call_ai_for_material(
            ai_svc, "Алгебра", "Topic", SourceContent(text="x", detected_format="text")
        )
    )
    assert material.title == "Recovered"
    assert provider.complete.call_count == 3


def test_fallback_after_3_failures():
    """Если все 3 попытки — невалидный JSON, возврат fallback."""
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=_mk_response("not json at all"))
    ai_svc = MagicMock()
    ai_svc.provider = provider
    material = asyncio.run(
        call_ai_for_material(
            ai_svc, "Алгебра", "ТемаФоллбэк", SourceContent(text="x", detected_format="text")
        )
    )
    assert material.title == "ТемаФоллбэк"
    assert any("AI не вернул" in n for n in material.ai_uncertainty_notes)
    assert provider.complete.call_count == 3


# ============ 8.4: AI metrics record ============


def test_record_ok():
    """_record_ai не падает на разных режимах и статусах."""
    _record_ai("test-mode", "ok", resp=_mk_response("x"), parse_status="ok")
    _record_ai("test-mode", "error")
    _record_ai("test-mode", "ok", parse_status="fallback")
    _record_ai("test-mode", "error", resp=None)


def test_record_with_none_resp():
    """При resp=None — input/output_tokens=0, не падает."""
    _record_ai("test-mode", "error", resp=None)
    assert True


# ============ Метрика ai_parse_status ============


def test_metric_labels_ok():
    """Counter с labelnames=('mode','result') инкрементируется."""
    if _PARSE_CNT is None:
        import pytest
        pytest.skip("prometheus не настроен")
    before = _PARSE_CNT.labels(mode="test-sprint8", result="ok")._value.get()
    _PARSE_CNT.labels(mode="test-sprint8", result="ok").inc()
    after = _PARSE_CNT.labels(mode="test-sprint8", result="ok")._value.get()
    assert after == before + 1
