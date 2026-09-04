"""Regression pack for student-facing AI output quality."""

from __future__ import annotations

from app.ai.hermes import _prepare_model_output
from app.ai.service import _trim_incomplete_trailing_fragment


def test_output_removes_json_preamble_and_private_reasoning() -> None:
    content, structured = _prepare_model_output(
        '<think>hidden</think>\n{"answer": "x"}\n\nОбъяснение: сначала сложи числа.'
    )

    assert "think" not in content.lower()
    assert "hidden" not in content
    assert content.startswith("Объяснение") or structured is not None


def test_output_keeps_readable_markdown_table_without_fence_noise() -> None:
    content, structured = _prepare_model_output(
        """
```markdown
| Шаг | Действие |
|---|---|
| 1 | Сложить числа |
| 2 | Разделить на количество |
```
"""
    )

    assert structured is None
    assert "```" not in content
    assert "|---|" not in content
    assert "Шаг" in content
    assert "Разделить" in content


def test_output_normalizes_broken_display_math_for_mobile_reading() -> None:
    content, structured = _prepare_model_output(r"$$\frac{24}{6}=4$$ и это среднее")

    assert structured is None
    assert "$$" not in content
    assert "\\frac" not in content
    assert "24 / 6" in content


def test_output_trims_unfinished_teacher_like_fragment() -> None:
    content = _trim_incomplete_trailing_fragment("Решение готово. Теперь попробуй похожую задачу:\n\nВ")

    assert content == "Решение готово."
