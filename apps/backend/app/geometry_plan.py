"""Geometry preview progression map for Month 2 subject expansion.

Stage 13 intentionally exposes a structured preview route only. The subject
remains `preview` until source/RAG and fallback practice coverage are complete.
"""
from __future__ import annotations

from dataclasses import dataclass

GEOMETRY_SUBJECT_ID = 5


@dataclass(frozen=True)
class GeometryTopicPlan:
    topic_id: int
    order: int
    section: str
    tier: str
    focus: str
    checkpoint: bool = False


GEOMETRY_TOPIC_PLAN: tuple[GeometryTopicPlan, ...] = (
    GeometryTopicPlan(53, 1, "Начальные геометрические сведения", "base", "прямая, отрезок, луч, угол"),
    GeometryTopicPlan(54, 2, "Начальные геометрические сведения", "base", "измерение отрезков и углов"),
    GeometryTopicPlan(55, 3, "Начальные геометрические сведения", "medium", "смежные и вертикальные углы"),
    GeometryTopicPlan(56, 4, "Начальные геометрические сведения", "medium", "перпендикулярные прямые", checkpoint=True),
    GeometryTopicPlan(57, 5, "Треугольники", "medium", "признаки равенства треугольников"),
    GeometryTopicPlan(58, 6, "Треугольники", "base", "медиана, биссектриса, высота"),
    GeometryTopicPlan(59, 7, "Треугольники", "medium", "равнобедренный треугольник"),
    GeometryTopicPlan(60, 8, "Треугольники", "hard", "окружность и задачи на построение", checkpoint=True),
    GeometryTopicPlan(61, 9, "Параллельные прямые", "medium", "признаки параллельности прямых"),
    GeometryTopicPlan(62, 10, "Параллельные прямые", "medium", "свойства параллельных прямых", checkpoint=True),
    GeometryTopicPlan(63, 11, "Соотношения между сторонами и углами треугольника", "base", "сумма углов треугольника"),
    GeometryTopicPlan(64, 12, "Соотношения между сторонами и углами треугольника", "medium", "внешний угол треугольника"),
    GeometryTopicPlan(65, 13, "Соотношения между сторонами и углами треугольника", "hard", "неравенство треугольника", checkpoint=True),
)

PLAN_BY_GEOMETRY_TOPIC_ID = {row.topic_id: row for row in GEOMETRY_TOPIC_PLAN}


def next_geometry_topic_after(topic_id: int) -> int | None:
    current = PLAN_BY_GEOMETRY_TOPIC_ID.get(topic_id)
    if current is None:
        return None
    for row in GEOMETRY_TOPIC_PLAN:
        if row.order == current.order + 1:
            return row.topic_id
    return None
