"""Sprint 3.28: snapshot тест публичного API app.ai.service.

Sprint 3.28 (Этап 3 god-файлы): разбиваем app/ai/service.py (1560 LOC)
на ai/{generation,explain,rag_lookup,dialog}.py + slim service.py.

Этот тест гарантирует, что ВСЕ символы публичного API остаются
доступны через `from app.ai.service import X` после рефакторинга.

Если регрессируем — ловим сразу: imports и attrs.
"""
from __future__ import annotations

import pytest
from app.ai import service

PUBLIC_CLASSES = [
    "CheckResult",
    "GeneratedExercise",
    "QuizQuestion",
    "Quiz",
    "AIService",
]
PUBLIC_FUNCTIONS = [
    "get_provider",
    "get_ai_service",
]


@pytest.mark.parametrize("name", PUBLIC_CLASSES)
def test_service_exports_class(name: str):
    """Sprint 3.28: класс должен быть доступен через app.ai.service.X."""
    cls = getattr(service, name, None)
    assert cls is not None, f"{name} не экспортируется из app.ai.service"
    # Класс не должен быть объектом-импортом __getattr__ lazy (мы хотим
    # чтобы re-export работал и для статической проверки типов).
    assert isinstance(cls, type), f"{name} — не класс"


@pytest.mark.parametrize("name", PUBLIC_FUNCTIONS)
def test_service_exports_function(name: str):
    """Sprint 3.28: функция должна быть доступна через app.ai.service.X."""
    func = getattr(service, name, None)
    assert func is not None, f"{name} не экспортируется из app.ai.service"
    assert callable(func), f"{name} — не callable"


def test_ai_service_class_has_expected_methods():
    """Sprint 3.28: AIService имеет ожидаемые публичные методы."""
    expected_public = {
        "explain_topic",
        "hint",
        "hint_at_level",
        "check_answer",
        "generate_exercise",
        "generate_quiz",
        "chat",
        "resolve_provider_for_subject",
    }
    for method_name in expected_public:
        assert hasattr(service.AIService, method_name), (
            f"AIService.{method_name} отсутствует"
        )
