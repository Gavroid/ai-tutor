"""MVP rescue: contract tests for real-provider AI output cleanup/parsing."""
from __future__ import annotations

import json

from types import SimpleNamespace

import pytest

from app.ai.hermes import _extract_structured_json, _prepare_model_output
from app.ai.service import AIService, GeneratedExercise, _dedupe_rag_sources, _exercise_matches_topic, _rag_enabled_for_subject
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


def test_rag_sources_only_enabled_for_math_repeat_subject() -> None:
    assert _rag_enabled_for_subject("Математика (6 класс - повторение пройденного материала)")
    assert not _rag_enabled_for_subject("Русский язык")
    assert not _rag_enabled_for_subject("Алгебра")


def test_rag_sources_are_deduplicated() -> None:
    sources = [
        {"material_title": "Математика 6 класс", "page_number": 114, "chunk_id": "a"},
        {"material_title": "Математика 6 класс", "page_number": 114, "chunk_id": "b"},
        {"material_title": "Математика 6 класс", "page_number": 130, "chunk_id": "c"},
    ]

    deduped = _dedupe_rag_sources(sources)

    assert deduped == [
        {"material_title": "Математика 6 класс", "page_number": 114, "chunk_id": "a"},
        {"material_title": "Математика 6 класс", "page_number": 130, "chunk_id": "c"},
    ]


def test_decimal_topic_rejects_common_fraction_exercise_drift() -> None:
    exercise = GeneratedExercise(
        question_text="Вычисли: 1/2 + 1/3. Выбери правильный ответ.",
        type="single",
        options=["5/6", "2/5"],
        correct_answer="5/6",
        explanation="Приводим к общему знаменателю.",
        typical_mistakes=[],
    )

    assert not _exercise_matches_topic(exercise, "Действия с десятичными дробями")


def test_prepare_model_output_removes_markdown_fence_and_table_separator() -> None:
    content, structured = _prepare_model_output(
        """
```markdown
| Действие | Что помнить |
|---|---|
| Деление | Сделай делитель целым |
```
"""
    )

    assert structured is None
    assert "```" not in content
    assert "|---|" not in content
    assert "Действие" in content


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

    exercise = await svc.generate_exercise("Математика (6 класс - повторение пройденного материала)", "Действия с обыкновенными дробями", 2)

    assert "think" not in exercise.question_text.lower()
    assert "raw reasoning" not in exercise.question_text.lower()
    assert exercise.type == "single"
    assert exercise.options
    assert exercise.correct_answer in exercise.options
    assert "1/2" in exercise.question_text or "дроб" in exercise.question_text.lower()


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
async def test_generate_exercise_decimal_fallback_matches_decimal_topic() -> None:
    svc = AIService(StaticProvider(AIResponse(content="bad", model="test-model", structured=None)))

    exercise = await svc.generate_exercise(
        "Математика (6 класс - повторение пройденного материала)",
        "Действия с десятичными дробями",
        2,
    )

    assert exercise.type == "single"
    assert exercise.correct_answer == "0,24"
    assert exercise.correct_answer in (exercise.options or [])
    assert "0,6" in exercise.question_text
    assert "1/2" not in exercise.question_text


@pytest.mark.asyncio
async def test_explain_topic_math_fallback_is_instructional() -> None:
    svc = AIService(StaticProvider(AIResponse(content="", model="test-model", structured=None)))
    topic = SimpleNamespace(
        name="Действия с обыкновенными дробями",
        section=SimpleNamespace(
            subject=SimpleNamespace(name="Математика (6 класс - повторение пройденного материала)")
        ),
    )
    user = SimpleNamespace(student_profile=SimpleNamespace(grade=7))

    response = await svc.explain_topic(None, user, topic)

    assert "общему знаменателю" in response.content
    assert "1/2 + 1/3" in response.content
    assert len(response.content) > 500


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
