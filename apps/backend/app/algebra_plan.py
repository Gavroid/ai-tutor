"""Algebra preview progression map for Month 2 subject expansion.

Stage 12 intentionally exposes a structured preview route only. The subject
remains `preview` until source/RAG and fallback practice coverage are complete.
"""

from __future__ import annotations

from dataclasses import dataclass

ALGEBRA_SUBJECT_ID = 4


@dataclass(frozen=True)
class AlgebraTopicPlan:
    topic_id: int
    order: int
    section: str
    tier: str
    focus: str
    checkpoint: bool = False


ALGEBRA_TOPIC_PLAN: tuple[AlgebraTopicPlan, ...] = (
    AlgebraTopicPlan(34, 1, "Выражения, тождества, уравнения", "base", "числовые выражения"),
    AlgebraTopicPlan(35, 2, "Выражения, тождества, уравнения", "base", "переменная и буквенное выражение"),
    AlgebraTopicPlan(36, 3, "Выражения, тождества, уравнения", "medium", "преобразование буквенных выражений"),
    AlgebraTopicPlan(
        37, 4, "Выражения, тождества, уравнения", "medium", "линейное уравнение с одной переменной", checkpoint=True
    ),
    AlgebraTopicPlan(38, 5, "Функции", "base", "понятие функции"),
    AlgebraTopicPlan(39, 6, "Функции", "medium", "линейная функция y = kx + b"),
    AlgebraTopicPlan(40, 7, "Функции", "medium", "прямая пропорциональность", checkpoint=True),
    AlgebraTopicPlan(41, 8, "Степень с натуральным показателем", "base", "определение степени"),
    AlgebraTopicPlan(42, 9, "Степень с натуральным показателем", "medium", "свойства степени"),
    AlgebraTopicPlan(43, 10, "Степень с натуральным показателем", "medium", "одночлены", checkpoint=True),
    AlgebraTopicPlan(44, 11, "Многочлены", "base", "понятие многочлена"),
    AlgebraTopicPlan(45, 12, "Многочлены", "medium", "сложение и вычитание многочленов"),
    AlgebraTopicPlan(46, 13, "Многочлены", "medium", "умножение одночлена на многочлен"),
    AlgebraTopicPlan(47, 14, "Многочлены", "hard", "умножение многочлена на многочлен"),
    AlgebraTopicPlan(48, 15, "Многочлены", "hard", "формулы сокращённого умножения", checkpoint=True),
    AlgebraTopicPlan(49, 16, "Системы линейных уравнений", "medium", "линейное уравнение с двумя переменными"),
    AlgebraTopicPlan(50, 17, "Системы линейных уравнений", "medium", "графический способ решения"),
    AlgebraTopicPlan(51, 18, "Системы линейных уравнений", "hard", "способ подстановки"),
    AlgebraTopicPlan(52, 19, "Системы линейных уравнений", "hard", "способ сложения", checkpoint=True),
)

PLAN_BY_ALGEBRA_TOPIC_ID = {row.topic_id: row for row in ALGEBRA_TOPIC_PLAN}


def next_algebra_topic_after(topic_id: int) -> int | None:
    current = PLAN_BY_ALGEBRA_TOPIC_ID.get(topic_id)
    if current is None:
        return None
    for row in ALGEBRA_TOPIC_PLAN:
        if row.order == current.order + 1:
            return row.topic_id
    return None
