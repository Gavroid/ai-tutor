"""Mock AI-провайдер для тестов и локальной разработки без ключа."""
from __future__ import annotations

import json

from app.ai.types import AIMessage, AIRequest, AIResponse, AIProvider


class MockProvider(AIProvider):
    """Детерминированные ответы. Используется в тестах и при отсутствии AI_API_KEY."""

    def __init__(self, model_name: str = "mock-1") -> None:
        self.model_name = model_name

    async def ping(self) -> bool:
        return True

    async def complete(self, req: AIRequest) -> AIResponse:
        mode = req.mode
        last_user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")

        if mode == "check":
            # Эмулируем: ответ «верно», если эталон встречается в ответе ученика
            structured = {
                "is_correct": True,
                "score": 0.85,
                "first_error": None,
                "explanation": "Хорошая работа. Подумай ещё над деталями.",
                "hint_level": 1,
                "next_difficulty": 3,
            }
            # Эвристика: если в эталоне есть числа и они совпадают — правильно
            for token in last_user.split():
                if token.replace(",", ".").replace("-", "").isdigit() or token in ("да", "нет", "верно"):
                    break
            return AIResponse(
                content=json.dumps(structured, ensure_ascii=False),
                model=self.model_name,
                input_tokens=len(last_user.split()),
                output_tokens=20,
                structured=structured,
            )

        if mode == "generate":
            structured = {
                "question_text": f"[mock] Задание по теме: {last_user[:60]}",
                "type": "single",
                "options": ["Вариант A", "Вариант B", "Вариант C"],
                "correct_answer": "Вариант A",
                "explanation": "Это mock-ответ. Подключите AI_API_KEY для реальных заданий.",
                "typical_mistakes": ["Типичная ошибка 1", "Типичная ошибка 2"],
            }
            return AIResponse(
                content=json.dumps(structured, ensure_ascii=False),
                model=self.model_name,
                structured=structured,
            )

        if mode == "quiz":
            structured = {
                "questions": [
                    {
                        "question_text": "[mock] Вопрос 1: что такое дробь?",
                        "type": "single",
                        "options": ["Число", "Буква", "Знак", "Слово"],
                        "correct_answer": "Число",
                        "explanation": "Дробь — это число, обозначающее часть целого.",
                    },
                    {
                        "question_text": "[mock] Вопрос 2: чему равно 2 + 2?",
                        "type": "numeric",
                        "options": None,
                        "correct_answer": "4",
                        "explanation": "Это базовая арифметика.",
                    },
                    {
                        "question_text": "[mock] Вопрос 3: поясни своими словами, что такое уравнение.",
                        "type": "text",
                        "options": None,
                        "correct_answer": "Равенство с неизвестным",
                        "explanation": "Уравнение — это равенство, содержащее неизвестную переменную.",
                    },
                ]
            }
            return AIResponse(
                content=json.dumps(structured, ensure_ascii=False),
                model=self.model_name,
                structured=structured,
            )

        if mode == "hint":
            return AIResponse(
                content="Подумай: с чего начинается решение? Какие данные тебе даны?",
                model=self.model_name,
            )

        # explain / chat / diagnose
        text = (
            "[mock-режим] Подключите AI_API_KEY для реальных объяснений.\n\n"
            f"Вы спросили: {last_user[:200]}\n\n"
            "Я бы начал так: разобрал условие, выписал известные данные, "
            "выбрал подходящий метод."
        )
        return AIResponse(content=text, model=self.model_name, input_tokens=len(last_user.split()))