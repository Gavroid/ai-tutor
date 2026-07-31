"""Stage 4 MVP content registry.

Small persistent JSON registry for teacher-managed content knobs before a full CMS schema.
Stored under UPLOAD_DIR so it survives app restarts/rebuilds in production volumes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.subjects import models as subj_models


def _registry_path() -> Path:
    base = Path(get_settings().upload_dir)
    base.mkdir(parents=True, exist_ok=True)
    return base / "teacher_content_registry.json"


def _default_registry() -> dict[str, Any]:
    return {
        "followups": {},
        "fallbacks": {},
        "topic_status": {},
        "rag_jobs": {},
    }


def load_registry() -> dict[str, Any]:
    path = _registry_path()
    if not path.exists():
        return _default_registry()
    try:
        data = json.loads(path.read_text())
    except Exception:
        return _default_registry()
    base = _default_registry()
    if isinstance(data, dict):
        for key in base:
            if isinstance(data.get(key), dict):
                base[key] = data[key]
    return base


def save_registry(data: dict[str, Any]) -> None:
    path = _registry_path()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def default_followups_for_topic(topic: subj_models.Topic) -> list[dict[str, Any]]:
    name = topic.name.lower()
    if "среднее арифметическое" in name:
        return [
            {"label": "Среднее чисел", "prompt": "Объясни подробнее среднее арифметическое обычных чисел на новом примере.", "kind": "choice", "order_index": 1},
            {"label": "Средняя скорость", "prompt": "Объясни среднюю скорость как отдельный тип задач, с простым примером.", "kind": "choice", "order_index": 2},
            {"label": "Средний вес", "prompt": "Объясни средний вес как отдельный тип задач, с простым примером.", "kind": "choice", "order_index": 3},
        ]
    if "наибольш" in name and "делител" in name:
        return [
            {"label": "Попробовать самому", "prompt": "Дай мне похожую задачу на НОД и взаимно простые числа, но не показывай ответ сразу.", "kind": "choice", "order_index": 1},
            {"label": "Второй способ", "prompt": "Покажи второй способ нахождения НОД через разложение на простые множители.", "kind": "choice", "order_index": 2},
        ]
    if "уравнен" in name:
        return [
            {"label": "Далее", "prompt": "Продолжи объяснение темы по следующему шагу: как переносить слагаемые в уравнении и менять знак.", "kind": "next", "order_index": 1},
        ]
    return []


def get_followups(topic: subj_models.Topic) -> list[dict[str, Any]]:
    data = load_registry()
    override = data.get("followups", {}).get(str(topic.id))
    rows = override if isinstance(override, list) else default_followups_for_topic(topic)
    return sorted([r for r in rows if isinstance(r, dict) and r.get("label") and r.get("prompt")], key=lambda r: int(r.get("order_index", 0)))


def set_followups(topic_id: int, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned = []
    for idx, row in enumerate(rows, start=1):
        label = str(row.get("label") or "").strip()
        prompt = str(row.get("prompt") or "").strip()
        if not label or not prompt:
            continue
        cleaned.append({
            "label": label[:80],
            "prompt": prompt[:500],
            "kind": str(row.get("kind") or "choice")[:20],
            "order_index": int(row.get("order_index") or idx),
        })
    data = load_registry()
    data.setdefault("followups", {})[str(topic_id)] = cleaned
    save_registry(data)
    return cleaned


def get_fallbacks(topic_id: int) -> list[dict[str, Any]]:
    data = load_registry()
    rows = data.get("fallbacks", {}).get(str(topic_id), [])
    return rows if isinstance(rows, list) else []


def set_fallbacks(topic_id: int, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned = []
    for idx, row in enumerate(rows, start=1):
        question_text = str(row.get("question_text") or "").strip()
        correct_answer = str(row.get("correct_answer") or "").strip()
        explanation = str(row.get("explanation") or "").strip()
        if not question_text or not correct_answer:
            continue
        options = row.get("options")
        cleaned.append({
            "question_text": question_text[:1000],
            "type": str(row.get("type") or "single")[:20],
            "options": [str(x)[:120] for x in options] if isinstance(options, list) else None,
            "correct_answer": correct_answer[:300],
            "explanation": explanation[:1500] or "Проверь правило темы и попробуй ещё раз.",
            "typical_mistakes": [str(x)[:200] for x in row.get("typical_mistakes", [])] if isinstance(row.get("typical_mistakes"), list) else [],
            "difficulty": int(row.get("difficulty") or idx),
            "order_index": int(row.get("order_index") or idx),
            "is_active": bool(row.get("is_active", True)),
        })
    data = load_registry()
    data.setdefault("fallbacks", {})[str(topic_id)] = cleaned
    save_registry(data)
    return cleaned


def fallback_for_topic(topic_id: int, difficulty: int) -> dict[str, Any] | None:
    active = [row for row in get_fallbacks(topic_id) if row.get("is_active", True)]
    if not active:
        return None
    active = sorted(active, key=lambda r: int(r.get("order_index", 0)))
    return active[(max(difficulty, 1) - 1) % len(active)]


def set_topic_status(topic_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"explain_status", "practice_status", "source_status", "manual_qa_status", "notes"}
    cleaned = {k: str(v)[:500] for k, v in payload.items() if k in allowed and v is not None}
    data = load_registry()
    current = data.setdefault("topic_status", {}).get(str(topic_id), {})
    if not isinstance(current, dict):
        current = {}
    current.update(cleaned)
    data.setdefault("topic_status", {})[str(topic_id)] = current
    save_registry(data)
    return current


def get_topic_status(topic_id: int) -> dict[str, Any]:
    data = load_registry()
    row = data.get("topic_status", {}).get(str(topic_id), {})
    return row if isinstance(row, dict) else {}


def record_rag_job(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = load_registry()
    data.setdefault("rag_jobs", {})[job_id] = payload
    save_registry(data)
    return payload


def get_rag_job(job_id: str) -> dict[str, Any] | None:
    data = load_registry()
    row = data.get("rag_jobs", {}).get(job_id)
    return row if isinstance(row, dict) else None
