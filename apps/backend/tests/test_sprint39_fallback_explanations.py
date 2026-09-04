"""Sprint 3.9 — расширенный fallback для AI explain.

Покрывает:
- Специализированные шаблоны для частых вводных тем (Физика, Русский, Алгебра, Геометрия, Информатика, География, Литература).
- Обобщённый fallback больше НЕ содержит бесполезное «начни с определения темы...».
- Все fallback'и имеют практическую ценность: правило + пример + вопрос для самопроверки.
"""
from __future__ import annotations

import pytest
from app.ai.service import _fallback_explanation


class TestFallbackExplanationStructure:
    """Все fallback'и должны иметь структуру: правило + пример + проверь себя."""

    @pytest.mark.parametrize("subject,topic", [
        ("Физика", "Что изучает физика"),
        ("Физика", "Физика и методы её изучения"),
        ("Русский язык", "Лексика и фразеология"),
        ("Русский язык", "Морфемика"),
        ("Алгебра", "Числовые выражения"),
        ("Геометрия", "Первый признак равенства треугольников"),
        ("Информатика", "Информация и её свойства"),
        ("География", "План местности"),
        ("Литература", "Что такое литература"),
    ])
    def test_specialized_fallbacks_have_structure(self, subject, topic):
        result = _fallback_explanation(subject, topic)
        # Любой нормальный fallback должен содержать эти блоки
        assert "### " in result, f"{subject}/{topic}: нет ни одного подзаголовка"
        # Должна быть либо 'Проверь себя', либо 'Что дальше'
        assert ("Проверь себя" in result) or ("Что дальше" in result), \
            f"{subject}/{topic}: нет ни 'Проверь себя' ни 'Что дальше'"

    def test_physics_what_studies_fallback(self):
        result = _fallback_explanation("Физика", "Что изучает физика")
        assert "Физика" in result
        assert "вещество" in result.lower() or "поле" in result.lower() or "энергия" in result.lower()
        assert "ускорение" in result or "9,8" in result  # конкретный пример

    def test_russian_lexika_fallback(self):
        result = _fallback_explanation("Русский язык", "Лексика и фразеология")
        assert "Лексика" in result
        assert "фразеолог" in result.lower()
        # Должны быть упомянуты омонимы/синонимы/антонимы
        assert "омоним" in result.lower() or "синоним" in result.lower() or "антоним" in result.lower()

    def test_algebra_numeric_expressions_fallback(self):
        result = _fallback_explanation("Алгебра", "Числовые выражения")
        assert "скобк" in result.lower()
        assert "порядок" in result.lower() or "слева направо" in result.lower()
        # Конкретный пример с числами
        assert "2 + 3" in result or "18 : 2" in result

    def test_geometry_triangle_first_sign_fallback(self):
        result = _fallback_explanation("Геометрия", "Первый признак равенства треугольников")
        assert "сторон" in result.lower() or "сторона" in result.lower()
        assert "угол" in result.lower()

    def test_informatics_fallback(self):
        result = _fallback_explanation("Информатика", "Информация")
        assert "информация" in result.lower()
        # Минимальная единица — бит
        assert "бит" in result.lower()

    def test_geography_plan_fallback(self):
        result = _fallback_explanation("География", "План местности")
        assert "масштаб" in result.lower()
        assert "условн" in result.lower()


class TestGenericFallbackImproved:
    """Обобщённый fallback (для тем без специализации) — структурирован."""

    @pytest.mark.parametrize("subject,topic", [
        ("История", "Древний Египет"),
        ("Биология", "Клетка"),
        ("Химия", "Периодический закон"),
        ("Английский язык", "Present Simple"),
        ("Обществознание", "Человек и общество"),
        ("Неизвестный предмет", "Какая-то тема"),
    ])
    def test_generic_fallback_has_useful_structure(self, subject, topic):
        result = _fallback_explanation(subject, topic)
        # НЕ должно быть старого бесполезного generic'а
        assert "начни с определения темы" not in result, (
            f"{subject}/{topic}: остался старый бесполезный generic"
        )
        # Должна быть структура (хотя бы один заголовок)
        assert "### " in result, f"{subject}/{topic}: нет подзаголовков"
        # Должны быть конкретные шаги
        assert any(kw in result.lower() for kw in [
            "определение", "пример", "правило", "алгоритм",
            "главное", "запомни", "проверь себя",
        ]), f"{subject}/{topic}: нет практических подсказок"

    def test_generic_fallback_suggests_practice(self):
        """Fallback должен предлагать перейти к практике (любой generic)."""
        result = _fallback_explanation("История", "Древний Египет")
        assert "Практика" in result or "практик" in result.lower()


class TestFallbackIsNotEmpty:
    """Sanity: функция всегда возвращает непустую строку."""

    @pytest.mark.parametrize("subject,topic", [
        ("", ""),
        ("X", "Y"),
        ("Длинный предмет" * 10, "Длинная тема" * 10),
    ])
    def test_returns_non_empty(self, subject, topic):
        result = _fallback_explanation(subject, topic)
        assert len(result) > 50, f"Empty/short result for {subject!r}/{topic!r}"
