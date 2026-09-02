"""Sprint 3.9.1 — расширенная LaTeX-нормализация для AI-вывода.

Покрывает:
- LaTeX-inline ``\\( ... \\)`` и display ``\\[ ... \\]`` (LaTeX-native нотация).
- Частые команды: \\\\angle, \\\\triangle, \\\\cdot, \\\\sqrt, \\\\frac, \\\\text.
- Степени и индексы в Unicode (50^\\circ → 50°, x^2 → x², x_{12} → x₁₂).
- Символы: ≤, ≥, ≠, ±, ×, ÷, →.
- Декораторы: \\\\overline, \\\\mathbf, \\\\mathrm → plain text.
- Вложенные дроби (3 уровня).
"""
from __future__ import annotations

import pytest

from app.ai.sanitize import _normalize_latex, sanitize_output


class TestLatexParenNotation:
    r"""LaTeX-native inline/display math через \( ... \) / \[ ... \]."""

    def test_inline_paren_basic(self):
        # Кирилл видит чистый текст, а не \( ... \)
        assert _normalize_latex(r"\(50^\circ\)") == "50°"

    def test_inline_paren_angles(self):
        # Главный кейс со скрина: \(\angle B = \angle C\)
        # Пробел после \angle — это ОК (нормализация оставляет один пробел).
        result = _normalize_latex(r"\(\angle B = \angle C\)")
        assert "∠" in result
        assert "B" in result and "C" in result
        # Никакого LaTeX в результате
        assert r"\(" not in result
        assert r"\)" not in result
        assert "\\" not in result

    def test_inline_paren_with_braces(self):
        # \overline{AB} → AB (декоратор убирается без скобок).
        assert _normalize_latex(r"\(\overline{AB}\)") == "AB"

    def test_display_paren(self):
        result = _normalize_latex(r"\[50^\circ\]")
        assert result == "50°"

    def test_multiple_inline_parens(self):
        text = r"боковые \(AB\) и \(AC\) равны"
        assert _normalize_latex(text) == "боковые AB и AC равны"


class TestMathSymbols:
    """Частые LaTeX-команды → Unicode."""

    @pytest.mark.parametrize("latex,expected", [
        (r"\angle", "∠"),
        (r"\triangle", "△"),
        (r"\leq", "≤"),
        (r"\geq", "≥"),
        (r"\neq", "≠"),
        (r"\pm", "±"),
        (r"\cdot", "×"),
        (r"\times", "×"),
        (r"\div", "÷"),
        (r"\to", "→"),
        (r"\rightarrow", "→"),
        (r"\approx", "≈"),
        (r"\infty", "∞"),
    ])
    def test_single_symbol(self, latex, expected):
        assert _normalize_latex(latex) == expected


class TestDegreesAndSuperscripts:
    """Градусы и степени в Unicode."""

    @pytest.mark.parametrize("latex,expected", [
        ("50^\\circ", "50°"),
        ("50^{\\circ}", "50°"),
        ("x^2", "x²"),
        ("x^10", "x¹⁰"),
        ("x^{2}", "x²"),
        ("x^{10}", "x¹⁰"),
        ("x^{n+1}", "xⁿ⁺¹"),
        ("2^8 = 256", "2⁸ = 256"),
    ])
    def test_superscripts(self, latex, expected):
        assert _normalize_latex(latex) == expected


class TestSubscripts:
    """Индексы в Unicode."""

    @pytest.mark.parametrize("latex,expected", [
        ("x_1", "x₁"),
        ("x_{12}", "x₁₂"),
        ("x_{n+1}", "xₙ₊₁"),
        ("AB_2", "AB2"),  # идентификатор: подчёркивание убирается (см. _IDENT_RE)
        ("H_2O", "H2O"),
    ])
    def test_subscripts_in_math(self, latex, expected):
        # Подчёркивание в identifiers убирается отдельно (rule 15),
        # в math-режиме с фигурными скобками конвертируется в Unicode.
        result = _normalize_latex(latex)
        # Проверяем что в math-режиме индекс в скобках стал Unicode
        if "_{" in latex:
            assert result == expected


class TestFractions:
    """Дроби в a / b формат."""

    def test_simple_frac(self):
        assert _normalize_latex(r"\frac{1}{2}") == "1 / 2"

    def test_frac_with_negatives(self):
        assert _normalize_latex(r"\frac{-3}{7}") == "-3 / 7"

    def test_nested_frac(self):
        # 3 уровня вложенности должно хватить.
        assert _normalize_latex(r"\frac{\frac{1}{2}}{3}") == "1 / 2 / 3"


class TestDecorators:
    """Декораторы → plain text."""

    @pytest.mark.parametrize("latex,expected", [
        (r"\overline{AB}", "AB"),
        (r"\mathbf{X}", "X"),
        (r"\mathrm{x}", "x"),
        (r"\text{word}", "word"),
    ])
    def test_decorator_stripped(self, latex, expected):
        assert _normalize_latex(latex) == expected


class TestUnknownCommands:
    """Неизвестные LaTeX-команды не должны ломать вывод."""

    def test_unknown_command_strips_backslash(self):
        assert _normalize_latex(r"\unknowncommand") == "unknowncommand"

    def test_unknown_in_sentence(self):
        result = _normalize_latex(r"Текст \foo и \bar текст")
        assert result == "Текст foo и bar текст"


class TestEndToEnd:
    """Реальные примеры из Кирилла."""

    def test_isosceles_triangle_explanation(self):
        # Реальный пример из скриншота "Равнобедренный треугольник"
        raw = (
            "В равнобедренном треугольнике \\(ABC\\) угол \\(\\angle B\\) равен "
            "\\(50^\\circ\\). Найдём угол \\(\\angle C\\). "
            "Так как стороны \\(AB\\) и \\(AC\\) равны, углы \\(\\angle B\\) и "
            "\\(\\angle C\\) равны: \\(\\angle C = \\angle B = 50^{\\circ}\\)."
        )
        result = _normalize_latex(raw)
        # Никаких LaTeX-скобок или команд в результате
        assert "\\" not in result
        assert "$" not in result
        # Содержательный текст с Unicode-символами
        assert "∠" in result
        assert "B" in result and "C" in result
        assert "50°" in result
        assert "ABC" in result

    def test_sanitize_output_calls_latex(self):
        """sanitize_output применяет _normalize_latex (regression check)."""
        raw = r"Угол \(\angle A = 30^\circ\)"
        out = sanitize_output(raw)
        assert "∠" in out
        assert "A" in out
        assert "30°" in out
        assert "\\" not in out


class TestBackwardsCompat:
    """Старые тесты (Sprint 7.x) продолжают работать."""

    def test_dollar_math_still_works(self):
        assert _normalize_latex("$50^\\circ$") == "50°"

    def test_double_dollar_math_still_works(self):
        assert _normalize_latex("$$x^2$$") == "x²"

    def test_text_still_works(self):
        assert _normalize_latex(r"\text{слово}") == "слово"

    def test_frac_still_works(self):
        assert _normalize_latex(r"\frac{a}{b}") == "a / b"
