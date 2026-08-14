"""Math-only progression map for the 6th-grade review subject.

This is a product layer above raw curriculum order: it groups topics into a
student-friendly path, difficulty tiers, and diagnostic checkpoints.
"""
from __future__ import annotations

from dataclasses import dataclass

MATH_SUBJECT_ID = 3


@dataclass(frozen=True)
class MathTopicPlan:
    topic_id: int
    order: int
    section: str
    tier: str
    focus: str
    checkpoint: bool = False


MATH_TOPIC_PLAN: tuple[MathTopicPlan, ...] = (
    MathTopicPlan(187, 1, "Вычисления и построения", "base", "средние значения и вычисления"),
    MathTopicPlan(188, 2, "Вычисления и построения", "base", "проценты в бытовых задачах"),
    MathTopicPlan(189, 3, "Вычисления и построения", "base", "чтение круговых диаграмм"),
    MathTopicPlan(190, 4, "Вычисления и построения", "base", "виды треугольников", checkpoint=True),
    MathTopicPlan(191, 5, "Вычисления и построения", "base", "множества и элементы"),
    MathTopicPlan(192, 6, "Дроби и смешанные числа", "base", "простые множители"),
    MathTopicPlan(193, 7, "Дроби и смешанные числа", "base", "НОД и взаимно простые числа"),
    MathTopicPlan(194, 8, "Дроби и смешанные числа", "base", "НОК"),
    MathTopicPlan(195, 9, "Дроби и смешанные числа", "medium", "общий знаменатель"),
    MathTopicPlan(196, 10, "Дроби и смешанные числа", "medium", "сравнение, сложение и вычитание дробей"),
    MathTopicPlan(197, 11, "Дроби и смешанные числа", "medium", "смешанные числа: плюс/минус"),
    MathTopicPlan(198, 12, "Дроби и смешанные числа", "medium", "умножение смешанных чисел"),
    MathTopicPlan(199, 13, "Дроби и смешанные числа", "medium", "дробь от числа"),
    MathTopicPlan(200, 14, "Дроби и смешанные числа", "medium", "распределительное свойство"),
    MathTopicPlan(201, 15, "Дроби и смешанные числа", "medium", "деление смешанных чисел", checkpoint=True),
    MathTopicPlan(202, 16, "Отношения и пропорции", "medium", "дробные выражения"),
    MathTopicPlan(203, 17, "Отношения и пропорции", "base", "отношения"),
    MathTopicPlan(204, 18, "Отношения и пропорции", "medium", "пропорции"),
    MathTopicPlan(205, 19, "Отношения и пропорции", "medium", "прямая и обратная зависимость"),
    MathTopicPlan(206, 20, "Отношения и пропорции", "base", "масштаб"),
    MathTopicPlan(207, 21, "Отношения и пропорции", "base", "симметрия"),
    MathTopicPlan(208, 22, "Отношения и пропорции", "medium", "окружность, круг, шар", checkpoint=True),
    MathTopicPlan(209, 23, "Рациональные числа", "base", "положительные и отрицательные числа"),
    MathTopicPlan(210, 24, "Рациональные числа", "base", "противоположные числа"),
    MathTopicPlan(211, 25, "Рациональные числа", "base", "модуль числа"),
    MathTopicPlan(212, 26, "Рациональные числа", "base", "сравнение чисел"),
    MathTopicPlan(213, 27, "Рациональные числа", "medium", "изменение величин"),
    MathTopicPlan(214, 28, "Рациональные числа", "medium", "сложение на координатной прямой"),
    MathTopicPlan(215, 29, "Рациональные числа", "medium", "сложение отрицательных чисел"),
    MathTopicPlan(216, 30, "Рациональные числа", "medium", "сложение чисел с разными знаками"),
    MathTopicPlan(217, 31, "Рациональные числа", "medium", "вычитание рациональных чисел"),
    MathTopicPlan(218, 32, "Рациональные числа", "medium", "умножение рациональных чисел"),
    MathTopicPlan(219, 33, "Рациональные числа", "medium", "деление рациональных чисел"),
    MathTopicPlan(220, 34, "Рациональные числа", "hard", "обобщение рациональных чисел"),
    MathTopicPlan(221, 35, "Рациональные числа", "hard", "свойства действий", checkpoint=True),
    MathTopicPlan(222, 36, "Уравнения и координаты", "medium", "раскрытие скобок"),
    MathTopicPlan(223, 37, "Уравнения и координаты", "base", "коэффициент"),
    MathTopicPlan(224, 38, "Уравнения и координаты", "medium", "подобные слагаемые"),
    MathTopicPlan(225, 39, "Уравнения и координаты", "hard", "решение уравнений"),
    MathTopicPlan(226, 40, "Уравнения и координаты", "base", "перпендикулярные прямые"),
    MathTopicPlan(227, 41, "Уравнения и координаты", "medium", "координатная плоскость"),
    MathTopicPlan(228, 42, "Уравнения и координаты", "base", "диаграммы и графики", checkpoint=True),
)

PLAN_BY_TOPIC_ID = {row.topic_id: row for row in MATH_TOPIC_PLAN}


def tier_rank(tier: str) -> int:
    return {"base": 1, "medium": 2, "hard": 3}.get(tier, 2)


def diagnostic_topic_ids(max_questions: int = 8) -> list[int]:
    """Balanced diagnostic sample across all math route sections."""
    checkpoints = [row.topic_id for row in MATH_TOPIC_PLAN if row.checkpoint]
    base = [187, 188, 193, 196, 204, 212, 219, 225]
    ordered: list[int] = []
    for topic_id in base + checkpoints:
        if topic_id not in ordered:
            ordered.append(topic_id)
    return ordered[:max_questions]


def next_topic_after(topic_id: int) -> int | None:
    current = PLAN_BY_TOPIC_ID.get(topic_id)
    if current is None:
        return None
    for row in MATH_TOPIC_PLAN:
        if row.order == current.order + 1:
            return row.topic_id
    return None
