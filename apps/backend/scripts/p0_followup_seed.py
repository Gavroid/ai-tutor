"""Seed practical follow-up buttons for math topics.

Safe/idempotent: replaces only math followup registry entries with deterministic rows.
"""
from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.subjects.models import Topic
from app.teacher import content_registry

DEFAULT_MATH_TOPIC_IDS = [187,188,189,190,191,192,193,194,195,196,197,198,199,200,201,202,203,204,205,206,207,208,209,210,211,212,213,214,215,216,217,218,219,220,221,222,223,224,225,226,227,228]


def build_followups(topic_name: str) -> list[dict[str, object]]:
    return [
        {
            "label": "Ещё пример",
            "prompt": f"Объясни тему «{topic_name}» на ещё одном коротком примере, без длинной теории.",
            "kind": "choice",
            "order_index": 1,
        },
        {
            "label": "Проверь меня",
            "prompt": f"Задай один вопрос на самопроверку по теме «{topic_name}» и не показывай ответ сразу.",
            "kind": "choice",
            "order_index": 2,
        },
        {
            "label": "Дай задачу",
            "prompt": f"Дай одну практическую задачу по теме «{topic_name}» средней сложности. Ответ пока не раскрывай.",
            "kind": "next",
            "order_index": 3,
        },
    ]


def run(topic_ids: list[int], *, dry_run: bool = False) -> dict[str, object]:
    with SessionLocal() as db:
        result: dict[str, object] = {"dry_run": dry_run, "updated": {}, "missing": []}
        for topic_id in topic_ids:
            topic = db.get(Topic, topic_id)
            if topic is None:
                result["missing"].append(topic_id)  # type: ignore[index]
                continue
            rows = build_followups(topic.name)
            if not dry_run:
                content_registry.set_followups(topic_id, rows)
            result["updated"][str(topic_id)] = len(rows)  # type: ignore[index]
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topics", default=",".join(map(str, DEFAULT_MATH_TOPIC_IDS)))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    topic_ids = [int(part.strip()) for part in args.topics.split(",") if part.strip()]
    print(json.dumps(run(topic_ids, dry_run=args.dry_run), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
