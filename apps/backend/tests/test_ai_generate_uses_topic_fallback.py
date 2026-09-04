from types import SimpleNamespace

import pytest
from app.ai.service import AIService
from app.ai.types import AIResponse
from app.teacher import content_registry


class EmptyProvider:
    async def complete(self, request):
        return AIResponse(content="plain text", model="test", structured=None)


@pytest.mark.asyncio
async def test_generate_exercise_uses_topic_registry_fallback(monkeypatch):
    monkeypatch.setattr(
        content_registry,
        "fallback_for_topic",
        lambda topic_id, difficulty: {
            "question_text": "2 + 2 = ?",
            "type": "single",
            "options": ["4", "5"],
            "correct_answer": "4",
            "explanation": "2 + 2 = 4",
            "typical_mistakes": [],
        } if topic_id == 200 else None,
    )

    exercise = await AIService(EmptyProvider()).generate_exercise("Математика", "Распределительное свойство умножения", 2, topic_id=200)

    assert exercise.type == "single"
    assert exercise.correct_answer == "4"
