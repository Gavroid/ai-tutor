"""S3 (2026-09-01): unit tests for pedagogical AI contracts.

Covers:
- S3.1 Multi-explain: 5 styles (default/simpler/example/schema/questions/freeform)
  + freeform интерпретация. Каждый стиль даёт уникальный промпт.
- S3.4 Offtopic guard: chat с явно offtopic сообщением возвращает короткий
  разворот без вызова AI-провайдера (model='offtopic-guard').
- S3.5 Honest refuse: system prompt содержит инструкцию для честного отказа.
- Render contract (S3.7): AIResponse.content и model поля — stable shape.

Не тестирует сам AI-провайдер (это external), а только Python-обвязку.
"""

from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-s3-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_DETERMINISTIC_MODE", "1")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest
from app.ai import prompts
from app.ai.service import AIResponse

# === S3.1 Multi-explain styles ==========================================


def test_explain_topic_system_default_style() -> None:
    s = prompts.explain_topic_system("Математика", "Среднее арифметическое", 7, rag_context=None, style="default")
    assert "объяснение" in s.lower()
    assert "пример" in s.lower() or "примеры" in s.lower()


def test_explain_topic_system_simpler_style() -> None:
    s = prompts.explain_topic_system("Математика", "Дроби", 7, rag_context=None, style="simpler")
    assert "проще" in s.lower() or "простыми словами" in s.lower()
    assert "младшему" in s  # специфичная фраза для simpler


def test_explain_topic_system_example_style() -> None:
    s = prompts.explain_topic_system("История", "Древний Египет", 7, rag_context=None, style="example")
    assert "пример" in s.lower() or "примеры" in s.lower()
    assert "игр" in s or "аниме" in s or "спорт" in s or "жизн" in s


def test_explain_topic_system_schema_style() -> None:
    s = prompts.explain_topic_system("Физика", "Сила", 7, rag_context=None, style="schema")
    assert "структурн" in s.lower()
    assert "Ключевое правило" in s
    assert "Главные признаки" in s
    assert "Частые ошибки" in s


def test_explain_topic_system_questions_style_socratic() -> None:
    """S3.3 integration: questions style = Socratic mode (no direct answer)."""
    s = prompts.explain_topic_system("Математика", "Уравнение", 7, rag_context=None, style="questions")
    # case-insensitive contains (file may have invisible chars from copy-paste)
    assert "сократ" in s.lower()
    assert "не давай прямого ответа" in s.lower()


def test_explain_topic_system_freeform_style() -> None:
    s = prompts.explain_topic_system("Алгебра", "Графики", 7, rag_context=None, style="freeform")
    assert "свободный запрос" in s.lower()


def test_explain_topic_system_unknown_style_falls_back_to_default() -> None:
    s = prompts.explain_topic_system("X", "Y", 7, rag_context=None, style="mystery_style")
    assert "не распознан" in s.lower()
    assert "стандартный" in s.lower()


# === S3.4 Offtopic guard =================================================


def test_is_likely_offtopic_detects_films() -> None:
    assert prompts.is_likely_offtopic("Расскажи про фильм Матрица")


def test_is_likely_offtopic_detects_games() -> None:
    assert prompts.is_likely_offtopic("Как играть в Майнкрафт?")


def test_is_likely_offtopic_detects_alcohol() -> None:
    assert prompts.is_likely_offtopic("Что такое пиво?")


def test_is_likely_offtopic_detects_relationships() -> None:
    assert prompts.is_likely_offtopic("Как найти девушку?")


def test_is_likely_offtopic_allows_math() -> None:
    assert not prompts.is_likely_offtopic("Реши уравнение 2x + 3 = 7")


def test_is_likely_offtopic_allows_history() -> None:
    assert not prompts.is_likely_offtopic("Расскажи про Древний Рим")


def test_is_likely_offtopic_allows_physics() -> None:
    assert not prompts.is_likely_offtopic("Что такое сила тяжести?")


def test_is_likely_offtopic_case_insensitive() -> None:
    assert prompts.is_likely_offtopic("МАЙНКРАФТ")
    assert prompts.is_likely_offtopic("Секс")


# === S3.5 Honest refuse in system prompt ================================


def test_chat_with_guards_system_has_honest_refuse() -> None:
    s = prompts.chat_with_guards_system()
    assert "ЧЕСТНЫЙ ОТКАЗ" in s
    assert "Пока не умею" in s
    assert "НЕ выдумывай" in s


def test_chat_with_guards_system_has_offtopic_instruction() -> None:
    s = prompts.chat_with_guards_system()
    assert "ОФФТОПИК" in s
    assert "разверни" in s.lower() or "разверн" in s.lower()


def test_chat_with_guards_system_has_socratic_instruction() -> None:
    s = prompts.chat_with_guards_system()
    assert "СОКРАТИЧЕСК" in s
    assert "наводящ" in s.lower()  # наводящий / наводящих


def test_chat_with_guards_system_includes_subject_context() -> None:
    s = prompts.chat_with_guards_system(subject_name="Математика", topic_name="Дроби")
    assert "Математика" in s
    assert "Дроби" in s


def test_chat_with_guards_system_works_without_context() -> None:
    s = prompts.chat_with_guards_system()
    assert "УЧЁБНЫЙ КОНТЕКСТ" in s


# === S3.7 Render contract ============================================


def test_ai_response_stable_shape() -> None:
    """AIResponse всегда имеет content (str), model (str), sources (list)."""
    r = AIResponse(content="hello", model="test-model", sources=[])
    assert isinstance(r.content, str)
    assert isinstance(r.model, str)
    assert isinstance(r.sources, list)
    assert r.sources == []


def test_ai_response_default_sources_empty() -> None:
    r = AIResponse(content="hi", model="x")
    assert r.sources == []


# === Integration: chat() pre-filter =====================================


def test_chat_offtopic_short_circuits_without_provider(monkeypatch) -> None:
    """S3.4: явный offtopic возвращает стандартный разворот без вызова провайдера.

    Это критично для D5.1: 20/час budget, offtopic-сообщения не должны его есть.
    """
    from app.ai import service as ai_service

    # Мокируем провайдер: если он вызовется — тест провалится.
    called = {"n": 0}

    class _BoomProvider:
        async def complete(self, req):
            called["n"] += 1
            raise RuntimeError("provider MUST NOT be called for offtopic")

    svc = ai_service.AIService(provider=_BoomProvider())
    import asyncio

    out = asyncio.run(
        svc.chat(
            history=[{"role": "user", "content": "Расскажи про секс"}],
            subject_name="Математика",
            topic_name="Дроби",
        )
    )
    assert called["n"] == 0, f"provider was called {called['n']} times for offtopic"
    assert "помогаю только с учёбой" in out.content
    assert out.model == "offtopic-guard"
    assert out.sources == []


def test_chat_nonofftopic_calls_provider(monkeypatch) -> None:
    """Sanity: нормальный учебный вопрос доходит до провайдера."""
    from app.ai import service as ai_service

    called = {"n": 0}

    class _StubProvider:
        async def complete(self, req):
            called["n"] += 1
            return ai_service.AIResponse(content="ответ AI", model="stub", sources=[])

    svc = ai_service.AIService(provider=_StubProvider())
    import asyncio

    out = asyncio.run(
        svc.chat(
            history=[{"role": "user", "content": "Объясни тему Дроби"}],
            subject_name="Математика",
            topic_name="Дроби",
        )
    )
    assert called["n"] == 1
    assert out.content == "ответ AI"
    assert out.model == "stub"
