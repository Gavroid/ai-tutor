"""Seed concrete checkable fallback tasks for math topics that need stable practice.

Safe/idempotent: replaces registry fallbacks only for selected topic IDs.
"""
from __future__ import annotations

import argparse
import json

from app.teacher import content_registry

FALLBACKS: dict[int, dict[str, object]] = {
    200: {
        "question_text": "Раскрой скобки: 3 × (4 + 5). Выбери правильный результат.",
        "type": "single",
        "options": ["27", "17", "32", "12"],
        "correct_answer": "27",
        "explanation": "По распределительному свойству: 3 × (4 + 5) = 3 × 4 + 3 × 5 = 12 + 15 = 27.",
        "typical_mistakes": ["Умножить только первое слагаемое", "Сложить без раскрытия скобок"],
    },
    213: {
        "question_text": "Цена была 100 рублей и увеличилась на 20%. Какой стала цена?",
        "type": "single",
        "options": ["120", "80", "20", "102"],
        "correct_answer": "120",
        "explanation": "20% от 100 — это 20. Новая цена: 100 + 20 = 120 рублей.",
        "typical_mistakes": ["Найти только изменение, но не новую величину", "Вычесть вместо прибавления"],
    },
    214: {
        "question_text": "На координатной прямой начни в точке -2 и прибавь 5. Где окажешься?",
        "type": "single",
        "options": ["3", "-7", "7", "-3"],
        "correct_answer": "3",
        "explanation": "Прибавить 5 — значит сдвинуться вправо на 5: -2 + 5 = 3.",
        "typical_mistakes": ["Двигаться влево при сложении", "Сложить модули и оставить минус"],
    },
    220: {
        "question_text": "Какое из чисел является рациональным?",
        "type": "single",
        "options": ["-3/4", "только √2", "только π", "ни одно"],
        "correct_answer": "-3/4",
        "explanation": "Рациональное число можно записать как дробь m/n, где n ≠ 0. Число -3/4 уже записано в таком виде.",
        "typical_mistakes": ["Считать отрицательные числа нерациональными", "Путать рациональные и натуральные числа"],
    },
    221: {
        "question_text": "Вычисли удобным способом: (-2) × 7 × 5. Выбери ответ.",
        "type": "single",
        "options": ["-70", "70", "-14", "35"],
        "correct_answer": "-70",
        "explanation": "Сначала 7 × 5 = 35, затем (-2) × 35 = -70. Один отрицательный множитель даёт отрицательный ответ.",
        "typical_mistakes": ["Потерять минус", "Нарушить правило знаков"],
    },
    222: {
        "question_text": "Раскрой скобки: -(x + 4). Выбери правильный вариант.",
        "type": "single",
        "options": ["-x - 4", "-x + 4", "x - 4", "x + 4"],
        "correct_answer": "-x - 4",
        "explanation": "Минус перед скобками меняет знак каждого слагаемого: -(x + 4) = -x - 4.",
        "typical_mistakes": ["Поменять знак только у первого слагаемого", "Оставить второй знак без изменения"],
    },
    224: {
        "question_text": "Собери подобные слагаемые: 3x + 2x. Выбери ответ.",
        "type": "single",
        "options": ["5x", "5x²", "6x", "x"],
        "correct_answer": "5x",
        "explanation": "У подобных слагаемых одинаковая буквенная часть. Складываем коэффициенты: 3 + 2 = 5, получаем 5x.",
        "typical_mistakes": ["Сложить буквы как степени", "Умножить коэффициенты вместо сложения"],
    },
    226: {
        "question_text": "Если две прямые пересекаются под углом 90°, как они называются?",
        "type": "single",
        "options": ["перпендикулярные", "параллельные", "совпадающие", "наклонные"],
        "correct_answer": "перпендикулярные",
        "explanation": "Перпендикулярные прямые пересекаются под прямым углом, то есть под углом 90°.",
        "typical_mistakes": ["Путать перпендикулярные и параллельные", "Не помнить, что прямой угол равен 90°"],
    },
    227: {
        "question_text": "На координатной плоскости точка A имеет координаты (2; -3). Какая у неё абсцисса?",
        "type": "single",
        "options": ["2", "-3", "5", "0"],
        "correct_answer": "2",
        "explanation": "Абсцисса — это первая координата точки. У точки (2; -3) первая координата равна 2.",
        "typical_mistakes": ["Перепутать абсциссу и ординату", "Взять вторую координату"],
    },
    228: {
        "question_text": "На столбчатой диаграмме столбец за понедельник равен 8, а за вторник 5. На сколько понедельник больше вторника?",
        "type": "single",
        "options": ["3", "13", "8", "5"],
        "correct_answer": "3",
        "explanation": "Чтобы сравнить высоты столбцов, вычитаем: 8 - 5 = 3.",
        "typical_mistakes": ["Сложить значения вместо сравнения", "Взять меньшее значение"],
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
