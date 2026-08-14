"""Seed concrete checkable fallback tasks for math topics that need stable practice.

Safe/idempotent: replaces registry fallbacks only for selected topic IDs.
"""
from __future__ import annotations

import argparse
import json

from app.teacher import content_registry

FALLBACKS: dict[int, dict[str, object]] = {
    187: {
        "question_text": "У Пети оценки за три работы: 4, 5 и 3. Чему равно среднее арифметическое?",
        "type": "single",
        "options": ["4", "12", "5", "3"],
        "correct_answer": "4",
        "explanation": "Складываем все значения и делим на их количество: (4 + 5 + 3) / 3 = 12 / 3 = 4.",
        "typical_mistakes": ["Забыть разделить сумму", "Делить не на количество значений"],
    },
    188: {
        "question_text": "В классе 30 учеников, 10% пришли в красных футболках. Сколько это учеников?",
        "type": "single",
        "options": ["3", "10", "20", "27"],
        "correct_answer": "3",
        "explanation": "10% — это одна десятая. 30 / 10 = 3 ученика.",
        "typical_mistakes": ["Считать 10% как 10 учеников", "Вычитать процент вместо нахождения части"],
    },
    189: {
        "question_text": "На круговой диаграмме половина круга подписана как «яблоки». Какая это доля?",
        "type": "single",
        "options": ["1/2", "1/4", "1/3", "2/3"],
        "correct_answer": "1/2",
        "explanation": "Половина круга — это одна из двух равных частей, то есть 1/2.",
        "typical_mistakes": ["Путать половину и четверть", "Считать сектор по площади на глаз без доли"],
    },
    190: {
        "question_text": "У треугольника все три стороны равны. Как он называется?",
        "type": "single",
        "options": ["равносторонний", "прямоугольный", "разносторонний", "тупоугольный"],
        "correct_answer": "равносторонний",
        "explanation": "Если все стороны треугольника равны, это равносторонний треугольник.",
        "typical_mistakes": ["Путать стороны и углы", "Называть любой симметричный треугольник прямоугольным"],
    },
    191: {
        "question_text": "В множестве A = {2, 4, 6}. Какое число является элементом A?",
        "type": "single",
        "options": ["4", "5", "8", "1"],
        "correct_answer": "4",
        "explanation": "Элемент множества — это объект, который прямо перечислен в фигурных скобках. Число 4 есть в A.",
        "typical_mistakes": ["Выбирать число по похожести", "Не проверять список элементов"],
    },
    192: {
        "question_text": "Разложи 18 на простые множители. Выбери верный вариант.",
        "type": "single",
        "options": ["2 × 3 × 3", "2 × 9", "1 × 18", "3 × 6"],
        "correct_answer": "2 × 3 × 3",
        "explanation": "18 = 2 × 9, а 9 = 3 × 3. Все множители 2, 3 и 3 — простые.",
        "typical_mistakes": ["Остановиться на составном множителе 9", "Записывать 1 как простой множитель"],
    },
    193: {
        "question_text": "Найди НОД чисел 12 и 18.",
        "type": "single",
        "options": ["6", "3", "12", "36"],
        "correct_answer": "6",
        "explanation": "Делители 12: 1, 2, 3, 4, 6, 12. Делители 18: 1, 2, 3, 6, 9, 18. Наибольший общий делитель — 6.",
        "typical_mistakes": ["Найти общий делитель, но не наибольший", "Путать НОД и НОК"],
    },
    194: {
        "question_text": "Найди НОК чисел 4 и 6.",
        "type": "single",
        "options": ["12", "2", "24", "10"],
        "correct_answer": "12",
        "explanation": "Кратные 4: 4, 8, 12. Кратные 6: 6, 12. Первое общее кратное — 12.",
        "typical_mistakes": ["Путать НОК с НОД", "Умножать числа без проверки меньшего общего кратного"],
    },
    195: {
        "question_text": "Какой общий знаменатель удобно взять для дробей 1/3 и 1/4?",
        "type": "single",
        "options": ["12", "7", "3", "4"],
        "correct_answer": "12",
        "explanation": "Общий знаменатель должен делиться и на 3, и на 4. Наименьшее такое число — 12.",
        "typical_mistakes": ["Складывать знаменатели", "Оставлять один из знаменателей без проверки"],
    },
    196: {
        "question_text": "Вычисли: 1/4 + 1/4.",
        "type": "single",
        "options": ["1/2", "2/8", "1/8", "2/4/4"],
        "correct_answer": "1/2",
        "explanation": "Знаменатели одинаковые, складываем числители: 1 + 1 = 2, получаем 2/4 = 1/2.",
        "typical_mistakes": ["Складывать знаменатели", "Не сокращать простой ответ"],
    },
    197: {
        "question_text": "Вычисли: 2 1/3 + 1 1/3.",
        "type": "single",
        "options": ["3 2/3", "3 1/3", "4 2/3", "2 2/3"],
        "correct_answer": "3 2/3",
        "explanation": "Складываем целые части: 2 + 1 = 3. Складываем дробные части: 1/3 + 1/3 = 2/3.",
        "typical_mistakes": ["Сложить только целые части", "Сложить знаменатели дробных частей"],
    },
    198: {
        "question_text": "Вычисли: 1 1/2 × 2. Выбери ответ.",
        "type": "single",
        "options": ["3", "2 1/2", "1", "4"],
        "correct_answer": "3",
        "explanation": "1 1/2 = 3/2. Тогда 3/2 × 2 = 3.",
        "typical_mistakes": ["Умножить только целую часть", "Не перевести смешанное число в неправильную дробь"],
    },
    199: {
        "question_text": "Найди 1/3 от 12.",
        "type": "single",
        "options": ["4", "3", "9", "36"],
        "correct_answer": "4",
        "explanation": "Чтобы найти 1/3 от числа, делим число на 3: 12 / 3 = 4.",
        "typical_mistakes": ["Умножать на знаменатель", "Путать часть от числа с прибавлением дроби"],
    },
    200: {
        "question_text": "Раскрой скобки: 3 × (4 + 5). Выбери правильный результат.",
        "type": "single",
        "options": ["27", "17", "32", "12"],
        "correct_answer": "27",
        "explanation": "По распределительному свойству: 3 × (4 + 5) = 3 × 4 + 3 × 5 = 12 + 15 = 27.",
        "typical_mistakes": ["Умножить только первое слагаемое", "Сложить без раскрытия скобок"],
    },
    201: {
        "question_text": "Вычисли: 2 1/2 : 5. Выбери ответ.",
        "type": "single",
        "options": ["1/2", "2", "5/2", "10"],
        "correct_answer": "1/2",
        "explanation": "2 1/2 = 5/2. Делим на 5: 5/2 : 5 = 5/2 × 1/5 = 1/2.",
        "typical_mistakes": ["Делить только целую часть", "Не заменить деление умножением на обратное число"],
    },
    202: {
        "question_text": "Упрости дробное выражение: (6/7) : 3. Выбери ответ.",
        "type": "single",
        "options": ["2/7", "18/7", "6/21", "9/7"],
        "correct_answer": "2/7",
        "explanation": "Деление на 3 — это умножение на 1/3: 6/7 × 1/3 = 6/21 = 2/7.",
        "typical_mistakes": ["Умножить на 3 вместо деления", "Не сократить 6/21"],
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
