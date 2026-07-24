"""Sprint 25: тесты для async semantic checker."""
from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "mock-token")

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.practice.checkers import check_answer_async


@pytest.mark.asyncio
async def test_check_answer_async_empty_input():
    """Sprint 25: пустой ответ → correct=False."""
    result = await check_answer_async("", "42", "Сколько будет 6*7?")
    assert result["correct"] is False
    assert result["score"] == 0.0
    assert result["checker"] == "semantic"
    assert "empty" in result["details"]["reason"].lower()


@pytest.mark.asyncio
async def test_check_answer_async_whitespace_input():
    """Sprint 25: только пробелы → empty."""
    result = await check_answer_async("   \n  ", "42", "Вопрос?")
    assert result["correct"] is False
    assert "empty" in result["details"]["reason"].lower()


@pytest.mark.asyncio
async def test_check_answer_async_ai_judge_correct():
    """Sprint 25: AI judge возвращает is_correct=True → semantic correct=True."""
    # Mock AIService
    mock_svc = MagicMock()
    mock_result = MagicMock()
    mock_result.is_correct = True
    mock_result.score = 1.0
    mock_result.explanation = "Ответ верный"
    mock_result.first_error = None
    mock_result.error_type = None
    mock_svc.check_answer = AsyncMock(return_value=mock_result)

    with patch("app.ai.service.get_ai_service", return_value=mock_svc):
        result = await check_answer_async(
            "42", "42", "Сколько будет 6*7?"
        )

    assert result["correct"] is True
    assert result["score"] == 1.0
    assert result["checker"] == "semantic"
    # case-insensitive check (и для test_check_answer_async_ai_judge_partial)
    assert "верн" in result["details"]["explanation"].lower()


@pytest.mark.asyncio
async def test_check_answer_async_ai_judge_partial():
    """Sprint 25: AI judge возвращает is_correct=False → semantic correct=False."""
    mock_svc = MagicMock()
    mock_result = MagicMock()
    mock_result.is_correct = False
    mock_result.score = 0.0
    mock_result.explanation = "Неверно"
    mock_result.first_error = "Арифметическая ошибка"
    mock_result.error_type = "ARITHMETIC"
    mock_svc.check_answer = AsyncMock(return_value=mock_result)

    with patch("app.ai.service.get_ai_service", return_value=mock_svc):
        result = await check_answer_async("7", "42", "Сколько будет 6*7?")

    assert result["correct"] is False
    assert result["score"] == 0.0
    assert result["details"]["first_error"] == "Арифметическая ошибка"
    assert result["details"]["error_type"] == "ARITHMETIC"


@pytest.mark.asyncio
async def test_check_answer_async_ai_failure_fallback():
    """Sprint 25: если AI упал → fallback (correct=False, reason указывает на failure)."""
    mock_svc = MagicMock()
    mock_svc.check_answer = AsyncMock(
        side_effect=Exception("AI timeout")
    )

    with patch("app.ai.service.get_ai_service", return_value=mock_svc):
        result = await check_answer_async("42", "42", "Вопрос?")

    assert result["correct"] is False
    assert result["score"] == 0.0
    assert "AI judge failed" in result["details"]["reason"]
    assert "fallback" in result["details"]