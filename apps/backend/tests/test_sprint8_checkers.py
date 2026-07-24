"""Sprint 8.2: чекеры для автопроверки практических задач.

Sprint 19 P2-2: РАСКОММЕНТИРОВАНО. Checkers интегрированы в
v2/exercises.py::submit_answer через dispatcher. Тесты снова активны.

3 стратегии:
- numeric — ответ сравнивается с эталоном как число (с допуском).
- keyword — в ответе должны присутствовать ключевые слова (case-insensitive, min-match-score).
- exact — точное совпадение с нормализацией (для "да/нет").
- semantic — для неоднозначных случаев: AI-judge (TODO, async).

Использование:
    from app.practice.checkers import check_answer
    result = check_answer(...)
"""
from __future__ import annotations

from app.practice.checkers import (
    NUMERIC_ABS_TOLERANCE,
    check_answer,
    check_exact,
    check_keyword,
    check_numeric,
    _extract_number,
)


class TestNumericChecker:
    """Sprint 8.2: numeric — точное или с допуском."""

    def test_exact_match(self):
        assert check_numeric("42", "42") is True

    def test_decimal_match(self):
        assert check_numeric("42.0", "42") is True

    def test_comma_separator(self):
        """'3,14' эквивалентно '3.14'."""
        assert check_numeric("3,14", "3.14") is True

    def test_within_absolute_tolerance(self):
        # Разница < 0.01
        assert check_numeric("42.005", "42") is True

    def test_outside_absolute_tolerance(self):
        assert check_numeric("43", "42") is False

    def test_within_relative_tolerance(self):
        # 100 * 1% = 1, поэтому 101 допустимо (разница = 1, база = 100)
        assert check_numeric("101", "100") is True

    def test_negative_numbers(self):
        assert check_numeric("-5", "-5") is True

    def test_with_units_extracts_number(self):
        """'42 см' — извлекаем 42."""
        assert check_numeric("42 см", "42") is True

    def test_no_number_in_user(self):
        assert check_numeric("ответ сорок два", "42") is False

    def test_invalid_input(self):
        assert check_numeric("", "42") is False


class TestExtractNumber:
    def test_extract_first_number(self):
        assert _extract_number("123 abc") == 123.0
        assert _extract_number("abc 456 def") == 456.0

    def test_extract_negative(self):
        assert _extract_number("-5") == -5.0

    def test_extract_decimal(self):
        assert _extract_number("3.14") == 3.14

    def test_no_number(self):
        assert _extract_number("abc") is None


class TestKeywordChecker:
    """Sprint 8.2: keyword — обязательные ключевые слова."""

    def test_all_keywords_found(self):
        r = check_keyword("Ответ пятьдесят", "эталон", ["пятьдесят"])
        assert r["correct"] is True
        assert r["matched"] == ["пятьдесят"]
        assert r["missing"] == []

    def test_missing_keyword(self):
        r = check_keyword("совсем другое", "эталон", ["нужное_слово"])
        assert r["correct"] is False
        assert "нужное_слово" in r["missing"]

    def test_partial_match(self):
        r = check_keyword("Первое есть", "Второе нужно", ["первое", "второе"])
        assert r["correct"] is False
        assert r["matched"] == ["первое"]
        assert r["missing"] == ["второе"]
        assert r["score"] == 0.5

    def test_case_insensitive(self):
        r = check_keyword("СЛОВО в ответе", "эталон", ["слово"])
        assert r["correct"] is True

    def test_auto_extracts_keywords_from_ref(self):
        """Без переданных keywords — берём первые 3 слова эталона."""
        r = check_keyword("Здесь есть альфа", "альфа бета гамма", [])
        assert r["correct"] is False  # только альфа, нет бета/гамма
        assert "бета" in r["missing"]
        assert "гамма" in r["missing"]

    def test_empty_ref_no_keywords(self):
        """Эталон пустой — нечего проверять."""
        r = check_keyword("любой ответ", "", [])
        assert r["correct"] is False
        assert r["score"] == 0.0


class TestExactChecker:
    def test_exact_match(self):
        assert check_exact("да", "да") is True

    def test_case_insensitive(self):
        assert check_exact("ДА", "да") is True

    def test_whitespace_normalized(self):
        assert check_exact("да", "  да  ") is True

    def test_no_match(self):
        assert check_exact("нет", "да") is False


class TestCheckAnswerDispatch:
    """Sprint 8.2 — универсальный dispatcher."""

    def test_dispatch_numeric(self):
        r = check_answer("42", "42", checker_type="numeric")
        assert r["correct"] is True
        assert r["checker"] == "numeric"
        assert r["score"] == 1.0

    def test_dispatch_keyword(self):
        r = check_answer(
            "Альфа-ответ",
            "эталон",
            checker_type="keyword",
            keywords=["альфа"],
        )
        assert r["correct"] is True
        assert r["checker"] == "keyword"

    def test_dispatch_exact(self):
        r = check_answer("Да", "да", checker_type="exact")
        assert r["correct"] is True

    def test_dispatch_semantic_needs_async(self):
        """Semantic пока не реализован синхронно (требует AI judge)."""
        r = check_answer("answer", "ref", checker_type="semantic")
        assert r["correct"] is False
        assert "details" in r
        # Возвращает «needs async» или просто 0, но НЕ должно быть 1.0
        assert r["score"] < 1.0

    def test_empty_answer(self):
        r = check_answer("", "ref", checker_type="keyword", keywords=["x"])
        assert r["correct"] is False
        assert r["details"]["reason"] == "empty answer"

    def test_unknown_checker_returns_false(self):
        r = check_answer("x", "y", checker_type="non-existent")
        assert r["correct"] is False
        assert "unknown" in r["details"].get("reason", "")


class TestCheckAnswerIntegrationWithMaterial:
    """Sprint 8.2: интеграция с PracticeTask.reference_solution."""

    def test_practice_task_reference_solution_used(self):
        # Это можно связать через middleware, но unit-тест:
        # если checker — keyword, должен использовать keywords + ref текст
        r = check_answer(
            user_answer="Сложение — это когда 2 + 3 = 5",
            reference_solution="Сложение — операция над числами",
            checker_type="keyword",
            keywords=["сложение"],
        )
        assert r["correct"] is True

    def test_numeric_for_math_problem(self):
        # Типичная задача: Сколько будет 6*7?
        r = check_answer(
            user_answer="42",
            reference_solution="42",
            checker_type="numeric",
        )
        assert r["correct"] is True
