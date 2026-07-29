"""MVP rescue: contract tests for real-provider AI output cleanup/parsing."""
from __future__ import annotations

import json

from types import SimpleNamespace

import pytest

from app.ai.hermes import _extract_structured_json, _prepare_model_output
from app.ai.service import AIService
from app.ai.types import AIMessage, AIRequest, AIResponse, AIProvider


class StaticProvider(AIProvider):
    def __init__(self, response: AIResponse) -> None:
        self.response = response

    async def complete(self, req: AIRequest) -> AIResponse:
        return self.response

    async def ping(self) -> bool:
        return True


def test_prepare_model_output_strips_raw_think_blocks() -> None:
    content, structured = _prepare_model_output(
        "<think>private reasoning</think>\n\n**Коротко:** это дробь."
    )

    assert "think" not in content.lower()
    assert "private reasoning" not in content
    assert content == "**Коротко:** это дробь."
    assert structured is None


def test_prepare_model_output_strips_escaped_think_blocks() -> None:
    content, structured = _prepare_model_output(
        "&lt;think&gt;private reasoning&lt;/think&gt;\n\nОтвет ученику"
    )

    assert "think" not in content.lower()
    assert "private reasoning" not in content
    assert content == "Ответ ученику"
    assert structured is None


def test_prepare_model_output_extracts_json_after_reasoning() -> None:
    raw = """
<think>Need JSON.</think>
Here is the result:
{"is_correct": true, "score": 1.0, "explanation": "Верно"}
"""

    content, structured = _prepare_model_output(raw)

    assert structured == {"is_correct": True, "score": 1.0, "explanation": "Верно"}
    assert json.loads(content) == structured
    assert "think" not in content.lower()


def test_extract_structured_json_handles_fenced_json() -> None:
    structured = _extract_structured_json(
        "```json\n{\"question_text\": \"Сколько будет 2+2?\", \"type\": \"numeric\"}\n```"
    )

    assert structured == {"question_text": "Сколько будет 2+2?", "type": "numeric"}


@pytest.mark.asyncio
async def test_generate_exercise_uses_safe_fallback_for_unstructured_output() -> None:
    svc = AIService(
        StaticProvider(
            AIResponse(
                content=" raw reasoning without valid object",
                model="test-model",
                structured=None,
            )
        )
    )

    exercise = await svc.generate_exercise("Русский язык", "Фразеологизмы", 2)

    assert "think" not in exercise.question_text.lower()
    assert "raw reasoning" not in exercise.question_text.lower()
    assert exercise.type == "text"
    assert exercise.correct_answer
    assert "Фразеологизмы" in exercise.question_text


@pytest.mark.asyncio
async def test_explain_topic_uses_safe_fallback_when_model_content_empty() -> None:
    svc = AIService(
        StaticProvider(
            AIResponse(
                content="",
                model="test-model",
                structured=None,
            )
        )
    )
    topic = SimpleNamespace(
        name="Фразеологизмы",
        section=SimpleNamespace(subject=SimpleNamespace(name="Русский язык")),
    )
    user = SimpleNamespace(student_profile=SimpleNamespace(grade=7))

    response = await svc.explain_topic(None, user, topic)

    assert response.content
    assert "Фразеологизмы" in response.content
    assert "think" not in response.content.lower()


@pytest.mark.asyncio
async def test_generate_exercise_accepts_json_after_think() -> None:
    content, structured = _prepare_model_output(
        """
<think>Create one task.</think>
{"question_text":"Что означает фразеологизм бить баклуши?","type":"single","options":["Лениться","Бежать","Читать"],"correct_answer":"Лениться","explanation":"Так говорят о безделье.","typical_mistakes":["Понимать буквально"]}
"""
    )
    svc = AIService(StaticProvider(AIResponse(content=content, model="test-model", structured=structured)))

    exercise = await svc.generate_exercise("Русский язык", "Фразеологизмы", 2)

    assert exercise.question_text == "Что означает фразеологизм бить баклуши?"
    assert exercise.type == "single"
    assert exercise.options == ["Лениться", "Бежать", "Читать"]
    assert exercise.correct_answer == "Лениться"
