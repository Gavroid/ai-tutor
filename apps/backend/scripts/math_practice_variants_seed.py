"""Seed 3 deterministic practice variants for every math route topic.

The first variant may be a hand-authored topic-specific fallback from
math_fallback_seed. The other variants are safe generic school tasks: one
self-check concept question and one example-recognition question. All are
checkable single-choice tasks, not free text.
"""
from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.math_plan import MATH_TOPIC_PLAN
from app.subjects.models import Topic
from app.teacher import content_registry

try:
    from scripts.math_fallback_seed import FALLBACKS as SPECIFIC_FALLBACKS
except Exception:  # pragma: no cover
    SPECIFIC_FALLBACKS = {}


def _generic_rows(topic_name: str) -> list[dict[str, object]]:
    return [
        {
            "question_text": f"Что лучше всего описывает тему «{topic_name}»?",
            "type": "single",
            "options": [
                f"Главное правило или способ решения по теме «{topic_name}»",
                "Случайный набор чисел без правила",
                "Только оформление тетради",
                "Тема не связана с математикой",
            ],
            "correct_answer": f"Главное правило или способ решения по теме «{topic_name}»",
            "explanation": "В этой задаче проверяется базовое понимание: нужно узнать смысл темы, а не угадывать числа.",
            "typical_mistakes": ["Отвечать слишком общо", "Не выделять главное правило"],
        },
        {
            "question_text": f"Какой первый шаг обычно самый разумный в теме «{topic_name}»?",
            "type": "single",
            "options": [
                "Вспомнить правило и разобрать один простой пример",
                "Сразу писать случайный ответ",
                "Игнорировать условие задачи",
                "Менять тему без попытки решения",
            ],
            "correct_answer": "Вспомнить правило и разобрать один простой пример",
            "explanation": "Почти любую школьную математическую тему безопасно начинать с правила и простого примера.",
            "typical_mistakes": ["Начинать без правила", "Не читать условие"],
        },
    ]


def build_rows(topic_id: int, topic_name: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    specific = SPECIFIC_FALLBACKS.get(topic_id)
    if specific:
        rows.append(dict(specific))
    rows.extend(_generic_rows(topic_name))
    cleaned = []
    for idx, row in enumerate(rows[:3], start=1):
        cleaned.append({**row, "difficulty": idx, "order_index": idx, "is_active": True})
    return cleaned


def run(topic_ids: list[int] | None = None, *, dry_run: bool = False) -> dict[str, object]:
    allowed = [row.topic_id for row in MATH_TOPIC_PLAN]
    ids = topic_ids or allowed
    result: dict[str, object] = {"dry_run": dry_run, "updated": {}, "missing": []}
    with SessionLocal() as db:
        for topic_id in ids:
            if topic_id not in allowed:
                result["missing"].append(topic_id)  # type: ignore[index]
                continue
            topic = db.get(Topic, topic_id)
            if topic is None:
                result["missing"].append(topic_id)  # type: ignore[index]
                continue
            rows = build_rows(topic_id, topic.name)
            if not dry_run:
                content_registry.set_fallbacks(topic_id, rows)
            result["updated"][str(topic_id)] = len(rows)  # type: ignore[index]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topics", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    topic_ids = [int(part.strip()) for part in args.topics.split(",") if part.strip()] or None
    print(json.dumps(run(topic_ids, dry_run=args.dry_run), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
