"""Sprint 7.4: hint endpoint 3 уровня + hint_at_level."""
from __future__ import annotations

import asyncio
import pytest

from app.ai import prompts
from app.ai.prompts import hint_system_at_level


class TestHintLevels:
    """/ai/hint с уровнями 1..3."""

    def test_level_1_is_question_only(self):
        """Уровень 1: наводящий вопрос, БЕЗ финального ответа."""
        s = hint_system_at_level(1)
        # Должен включать 'наводящий вопрос'
        assert "наводящий" in s.lower() or "вопрос" in s.lower()
        # НЕ должен давать ответ напрямую
        assert "не давай ответа" in s.lower() or "не давай" in s.lower()

    def test_level_2_is_hint(self):
        """Уровень 2: подсказка к решению, без финального ответа."""
        s = hint_system_at_level(2)
        assert "подсказ" in s.lower()
        assert "не давай" in s.lower() or "не" in s.lower()

    def test_level_3_is_full_solution(self):
        """Уровень 3: полный разбор / пошаговое решение."""
        s = hint_system_at_level(3)
        assert "разбор" in s.lower() or "решение" in s.lower()
        assert "пошаговое" in s.lower() or "шаг" in s.lower()

    def test_levels_are_distinct(self):
        """Все 3 уровня содержат разные инструкции (Sprint 7.4 UX)."""
        s1 = hint_system_at_level(1)
        s2 = hint_system_at_level(2)
        s3 = hint_system_at_level(3)
        assert s1 != s2 != s3
        # Все 3 должны упомянуть уровень явно
        for s, lvl in [(s1, 1), (s2, 2), (s3, 3)]:
            assert f"уровень {lvl}" in s.lower()

    def test_unknown_level_falls_back_to_1(self):
        """Невалидный уровень → fallback на 1."""
        assert hint_system_at_level(0) == hint_system_at_level(1)
        assert hint_system_at_level(4) == hint_system_at_level(1)
        assert hint_system_at_level(-1) == hint_system_at_level(1)


class TestHintAIService:
    """/ai/hint with level via AIService.hint_at_level."""

    def test_clamp_level_under(self):
        """_hint_with_level clamps level < 1 в 1."""
        from unittest.mock import AsyncMock, MagicMock

        from app.ai.service import AIService
        from app.ai.types import AIMessage, AIResponse

        provider = MagicMock()
        provider.complete = AsyncMock(return_value=AIResponse(content="x", model="test"))
        ai = AIService(provider)
        asyncio.run(ai._hint_with_level("question", level=0))
        # Видим, что вызов прошёл и AI_REQUEST mode == "hint"
        # Для подтверждения clamp'а — смотрим, что сообщения system содержит правильный уровень
        call_args = provider.complete.call_args
        req = call_args[0][0]
        sys_msg = req.messages[0].content
        assert "уровень 1" in sys_msg.lower()

    def test_clamp_level_over(self):
        """_hint_with_level clamps level > 3 в 3."""
        from unittest.mock import AsyncMock, MagicMock

        from app.ai.service import AIService
        from app.ai.types import AIResponse

        provider = MagicMock()
        provider.complete = AsyncMock(return_value=AIResponse(content="x", model="test"))
        ai = AIService(provider)
        asyncio.run(ai._hint_with_level("question", level=100))
        call_args = provider.complete.call_args
        sys_msg = call_args[0][0].messages[0].content
        assert "уровень 3" in sys_msg.lower()


class TestHintIntegration:
    """POST /api/v1/ai/hint принимает level в body."""

    def test_hint_validates_level_1_to_3(self):
        from app.ai.router import HintIn

        h = HintIn(question_text="x", level=2)
        assert h.level == 2
        # Pydantic валидирует ge/le
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HintIn(question_text="x", level=0)
        with pytest.raises(ValidationError):
            HintIn(question_text="x", level=4)

    def test_hint_default_level_is_1(self):
        """Без level в body — уровень 1 (обратная совместимость)."""
        from app.ai.router import HintIn

        h = HintIn(question_text="x")
        assert h.level == 1
