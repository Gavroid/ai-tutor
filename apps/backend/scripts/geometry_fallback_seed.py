"""Seed concrete checkable fallback tasks for Geometry preview route topics.

Safe/idempotent: replaces registry fallbacks only for selected Geometry topic IDs.
"""
from __future__ import annotations

import argparse
import json

from app.teacher import content_registry

FALLBACKS: dict[int, dict[str, object]] = {
    53: {
        "question_text": "На одной прямой точки A, B, C идут в таком порядке. Какой объект обозначает часть прямой от A до B?",
        "type": "single",
        "options": ["отрезок AB", "луч AB", "угол ABC", "вся прямая AC"],
        "correct_answer": "отрезок AB",
        "explanation": "Отрезок AB — часть прямой, ограниченная двумя точками A и B.",
        "typical_mistakes": ["Путать отрезок и луч", "Считать, что нужны все точки на прямой"],
    },
    54: {
        "question_text": "Отрезок AB равен 7 см, а BC равен 5 см. Точка B лежит между A и C. Чему равен AC?",
        "type": "single",
        "options": ["12 см", "2 см", "35 см", "7 см"],
        "correct_answer": "12 см",
        "explanation": "Если B между A и C, длина AC равна сумме AB и BC: 7 + 5 = 12 см.",
        "typical_mistakes": ["Вычитать длины вместо сложения", "Игнорировать порядок точек"],
    },
    55: {
        "question_text": "Один из вертикальных углов равен 40°. Чему равен второй вертикальный угол?",
        "type": "single",
        "options": ["40°", "140°", "80°", "90°"],
        "correct_answer": "40°",
        "explanation": "Вертикальные углы равны, поэтому второй угол тоже равен 40°.",
        "typical_mistakes": ["Путать вертикальные и смежные углы", "Делать сумму до 180° для вертикальных углов"],
    },
    56: {
        "question_text": "Две прямые пересекаются под углом 90°. Как они называются?",
        "type": "single",
        "options": ["перпендикулярные", "параллельные", "смежные", "равные"],
        "correct_answer": "перпендикулярные",
        "explanation": "Перпендикулярные прямые пересекаются под прямым углом, то есть 90°.",
        "typical_mistakes": ["Путать перпендикулярные и параллельные прямые", "Считать любой пересекающийся угол прямым"],
    },
    57: {
        "question_text": "У двух треугольников равны две стороны и угол между ними. Какой признак равенства подходит?",
        "type": "single",
        "options": ["по двум сторонам и углу между ними", "по трём углам", "по одной стороне", "по периметру"],
        "correct_answer": "по двум сторонам и углу между ними",
        "explanation": "Первый признак равенства треугольников: две стороны и угол между ними соответственно равны.",
        "typical_mistakes": ["Забывать, что угол должен быть между сторонами", "Путать равенство и подобие"],
    },
    58: {
        "question_text": "Как называется отрезок из вершины треугольника к середине противоположной стороны?",
        "type": "single",
        "options": ["медиана", "биссектриса", "высота", "сторона"],
        "correct_answer": "медиана",
        "explanation": "Медиана соединяет вершину треугольника с серединой противоположной стороны.",
        "typical_mistakes": ["Путать медиану и биссектрису", "Не учитывать середину стороны"],
    },
    59: {
        "question_text": "В равнобедренном треугольнике две стороны равны. Как называются углы при основании?",
        "type": "single",
        "options": ["равные", "прямые", "смежные", "вертикальные"],
        "correct_answer": "равные",
        "explanation": "В равнобедренном треугольнике углы при основании равны.",
        "typical_mistakes": ["Путать стороны и углы", "Считать, что равны все три угла"],
    },
    60: {
        "question_text": "Какая фигура является множеством точек, равноудалённых от одной точки?",
        "type": "single",
        "options": ["окружность", "отрезок", "луч", "угол"],
        "correct_answer": "окружность",
        "explanation": "Окружность — множество точек плоскости, равноудалённых от центра.",
        "typical_mistakes": ["Путать окружность и круг", "Считать центром любую точку на окружности"],
    },
    61: {
        "question_text": "Если при пересечении двух прямых секущей накрест лежащие углы равны, что можно сказать о прямых?",
        "type": "single",
        "options": ["они параллельны", "они перпендикулярны", "они совпадают", "они образуют треугольник"],
        "correct_answer": "они параллельны",
        "explanation": "Равенство накрест лежащих углов — признак параллельности прямых.",
        "typical_mistakes": ["Путать накрест лежащие и смежные углы", "Делать вывод о перпендикулярности"],
    },
    62: {
        "question_text": "Две параллельные прямые пересечены секущей. Один из соответственных углов равен 70°. Чему равен другой соответственный угол?",
        "type": "single",
        "options": ["70°", "110°", "20°", "90°"],
        "correct_answer": "70°",
        "explanation": "При параллельных прямых соответственные углы равны.",
        "typical_mistakes": ["Использовать 180° для соответственных углов", "Путать соответственные и односторонние углы"],
    },
    63: {
        "question_text": "Два угла треугольника равны 50° и 60°. Чему равен третий угол?",
        "type": "single",
        "options": ["70°", "110°", "90°", "60°"],
        "correct_answer": "70°",
        "explanation": "Сумма углов треугольника равна 180°. 180 - 50 - 60 = 70°.",
        "typical_mistakes": ["Забыть сумму 180°", "Сложить углы и принять сумму за ответ"],
    },
    64: {
        "question_text": "Внешний угол треугольника равен сумме каких углов?",
        "type": "single",
        "options": ["двух внутренних, не смежных с ним", "двух смежных с ним", "всех трёх внутренних", "только прямых углов"],
        "correct_answer": "двух внутренних, не смежных с ним",
        "explanation": "Внешний угол треугольника равен сумме двух внутренних углов, не смежных с ним.",
        "typical_mistakes": ["Брать смежный внутренний угол", "Складывать все углы треугольника"],
    },
    65: {
        "question_text": "Могут ли стороны треугольника быть 2 см, 3 см и 10 см?",
        "type": "single",
        "options": ["нет", "да", "только если угол прямой", "только если стороны равны"],
        "correct_answer": "нет",
        "explanation": "Сумма двух меньших сторон должна быть больше третьей: 2 + 3 = 5, а 5 < 10, значит треугольник невозможен.",
        "typical_mistakes": ["Проверять только разность сторон", "Считать любые три отрезка треугольником"],
    },
}


def build_rows(topic_id: int) -> list[dict[str, object]]:
    row = FALLBACKS[topic_id]
    return [{**row, "difficulty": 1, "order_index": 1, "is_active": True}]


def run(topic_ids: list[int], *, dry_run: bool = False) -> dict[str, object]:
    result: dict[str, object] = {"dry_run": dry_run, "updated": {}, "missing": []}
    for topic_id in topic_ids:
        if topic_id not in FALLBACKS:
            result["missing"].append(topic_id)  # type: ignore[index]
            continue
        rows = build_rows(topic_id)
        if not dry_run:
            content_registry.set_fallbacks(topic_id, rows)
        result["updated"][str(topic_id)] = len(rows)  # type: ignore[index]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topics", default=",".join(map(str, FALLBACKS)))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    topic_ids = [int(part.strip()) for part in args.topics.split(",") if part.strip()]
    print(json.dumps(run(topic_ids, dry_run=args.dry_run), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
