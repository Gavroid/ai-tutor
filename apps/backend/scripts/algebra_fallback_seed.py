"""Seed concrete checkable fallback tasks for Algebra preview route topics.

Safe/idempotent: replaces registry fallbacks only for selected Algebra topic IDs.
"""
from __future__ import annotations

import argparse
import json

from app.teacher import content_registry

FALLBACKS: dict[int, dict[str, object]] = {
    34: {
        "question_text": "Вычисли значение числового выражения: 3 + 4 × 2.",
        "type": "single",
        "options": ["11", "14", "10", "9"],
        "correct_answer": "11",
        "explanation": "Сначала выполняем умножение: 4 × 2 = 8. Затем 3 + 8 = 11.",
        "typical_mistakes": ["Считать слева направо без порядка действий", "Сначала сложить 3 и 4"],
    },
    35: {
        "question_text": "В выражении 5a + 2 чему равен коэффициент при a?",
        "type": "single",
        "options": ["5", "a", "2", "7"],
        "correct_answer": "5",
        "explanation": "Коэффициент при переменной — числовой множитель перед ней. В 5a это число 5.",
        "typical_mistakes": ["Путать коэффициент и переменную", "Считать свободный член коэффициентом"],
    },
    36: {
        "question_text": "Упрости выражение: 2x + 3x.",
        "type": "single",
        "options": ["5x", "6x", "5x²", "x"],
        "correct_answer": "5x",
        "explanation": "Это подобные слагаемые. Складываем коэффициенты: 2 + 3 = 5, буквенная часть остаётся x.",
        "typical_mistakes": ["Умножить коэффициенты", "Сделать степень x²"],
    },
    37: {
        "question_text": "Реши уравнение: x + 7 = 12.",
        "type": "single",
        "options": ["5", "19", "7", "12"],
        "correct_answer": "5",
        "explanation": "Вычитаем 7 из обеих частей: x = 12 - 7 = 5.",
        "typical_mistakes": ["Прибавить 7 вместо вычитания", "Взять 12 как ответ"],
    },
    38: {
        "question_text": "Если каждому x ставится в соответствие число y = x + 1, что это?",
        "type": "single",
        "options": ["функция", "случайный список", "неравенство", "дробь"],
        "correct_answer": "функция",
        "explanation": "Функция задаёт правило, по которому каждому допустимому x соответствует значение y.",
        "typical_mistakes": ["Путать функцию с уравнением", "Не видеть правила соответствия"],
    },
    39: {
        "question_text": "Для функции y = 2x + 3 найди y при x = 4.",
        "type": "single",
        "options": ["11", "8", "14", "9"],
        "correct_answer": "11",
        "explanation": "Подставляем x = 4: y = 2 × 4 + 3 = 8 + 3 = 11.",
        "typical_mistakes": ["Не подставить x", "Сложить 2 + 4 + 3"],
    },
    40: {
        "question_text": "Если y = 5x, чему равно y при x = 3?",
        "type": "single",
        "options": ["15", "8", "5", "3"],
        "correct_answer": "15",
        "explanation": "При прямой пропорциональности y = kx. Здесь y = 5 × 3 = 15.",
        "typical_mistakes": ["Сложить 5 и 3", "Путать прямую пропорциональность с обратной"],
    },
    41: {
        "question_text": "Что означает запись 2³?",
        "type": "single",
        "options": ["2 × 2 × 2", "2 + 3", "3 × 3", "2 × 3"],
        "correct_answer": "2 × 2 × 2",
        "explanation": "Степень 2³ означает произведение трёх одинаковых множителей 2.",
        "typical_mistakes": ["Умножить основание на показатель", "Сложить основание и показатель"],
    },
    42: {
        "question_text": "Упрости: a² × a³.",
        "type": "single",
        "options": ["a⁵", "a⁶", "a¹", "2a³"],
        "correct_answer": "a⁵",
        "explanation": "При умножении степеней с одинаковым основанием показатели складываются: 2 + 3 = 5.",
        "typical_mistakes": ["Умножить показатели", "Сложить основания"],
    },
    43: {
        "question_text": "Какой из вариантов является одночленом?",
        "type": "single",
        "options": ["3x²y", "x + y", "x - 4", "2/(x)"],
        "correct_answer": "3x²y",
        "explanation": "Одночлен — произведение чисел, переменных и их степеней с натуральными показателями.",
        "typical_mistakes": ["Считать сумму одночленом", "Не отличать одночлен от многочлена"],
    },
    44: {
        "question_text": "Какой из вариантов является многочленом?",
        "type": "single",
        "options": ["x² + 3x + 1", "только 5x", "1/x", "√x"],
        "correct_answer": "x² + 3x + 1",
        "explanation": "Многочлен — сумма одночленов. x², 3x и 1 являются одночленами.",
        "typical_mistakes": ["Считать только длинные выражения многочленами", "Включать 1/x как многочлен"],
    },
    45: {
        "question_text": "Упрости: (2x + 3) + (x + 4).",
        "type": "single",
        "options": ["3x + 7", "2x² + 7", "3x + 12", "x + 7"],
        "correct_answer": "3x + 7",
        "explanation": "Складываем подобные: 2x + x = 3x, 3 + 4 = 7.",
        "typical_mistakes": ["Умножить коэффициенты", "Не собрать свободные члены"],
    },
    46: {
        "question_text": "Раскрой скобки: 3x(2x + 5).",
        "type": "single",
        "options": ["6x² + 15x", "6x + 15", "5x² + 8x", "6x² + 5"],
        "correct_answer": "6x² + 15x",
        "explanation": "Умножаем 3x на каждое слагаемое: 3x·2x = 6x², 3x·5 = 15x.",
        "typical_mistakes": ["Умножить только первое слагаемое", "Потерять степень x²"],
    },
    47: {
        "question_text": "Раскрой скобки: (x + 2)(x + 3).",
        "type": "single",
        "options": ["x² + 5x + 6", "x² + 6", "2x + 5", "x² + 5"],
        "correct_answer": "x² + 5x + 6",
        "explanation": "Перемножаем каждое слагаемое: x² + 3x + 2x + 6 = x² + 5x + 6.",
        "typical_mistakes": ["Умножить только крайние члены", "Не сложить 3x и 2x"],
    },
    48: {
        "question_text": "Используй формулу: (a + b)². Какой вариант верный?",
        "type": "single",
        "options": ["a² + 2ab + b²", "a² + b²", "a² - b²", "2a + 2b"],
        "correct_answer": "a² + 2ab + b²",
        "explanation": "Квадрат суммы: (a + b)² = a² + 2ab + b².",
        "typical_mistakes": ["Забыть средний член 2ab", "Путать квадрат суммы и разность квадратов"],
    },
    49: {
        "question_text": "Какая пара (x; y) подходит к уравнению x + y = 5?",
        "type": "single",
        "options": ["(2; 3)", "(5; 5)", "(1; 1)", "(0; 6)"],
        "correct_answer": "(2; 3)",
        "explanation": "Подставляем: 2 + 3 = 5, значит пара подходит.",
        "typical_mistakes": ["Проверять только x", "Не подставлять оба значения"],
    },
    50: {
        "question_text": "Что означает графический способ решения системы?",
        "type": "single",
        "options": ["найти точку пересечения графиков", "сложить все коэффициенты", "стереть одну переменную", "заменить x на 0 всегда"],
        "correct_answer": "найти точку пересечения графиков",
        "explanation": "Решение системы двух линейных уравнений — точка, где их графики пересекаются.",
        "typical_mistakes": ["Искать любую точку на одном графике", "Не понимать смысл пересечения"],
    },
    51: {
        "question_text": "В системе x = 2y и x + y = 9 подставь первое уравнение во второе. Что получится?",
        "type": "single",
        "options": ["2y + y = 9", "x + 2y = 9", "2x + y = 9", "y = 9"],
        "correct_answer": "2y + y = 9",
        "explanation": "Так как x = 2y, во втором уравнении вместо x пишем 2y.",
        "typical_mistakes": ["Подставить не в то место", "Оставить обе переменные без замены"],
    },
    52: {
        "question_text": "Сложи уравнения системы: x + y = 7 и x - y = 3. Что получится?",
        "type": "single",
        "options": ["2x = 10", "2y = 10", "x = 4", "0 = 10"],
        "correct_answer": "2x = 10",
        "explanation": "При сложении y и -y уничтожаются, остаётся x + x = 7 + 3, то есть 2x = 10.",
        "typical_mistakes": ["Не уничтожить противоположные y", "Сложить только левые части"],
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
