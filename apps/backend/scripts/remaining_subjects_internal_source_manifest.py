"""Project-owned source/practice manifest for remaining preview subjects.

Builds route/source/practice-shaped rows for all non Math/Algebra/Geometry
subjects from the existing curriculum. The content is internally authored,
short, auditable, and does not rely on unverified external sources.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from app.subjects.curriculum_7_class import CURRICULUM_7_CLASS

READY_SUBJECT_CODES = {"math", "algebra", "geom"}
REMAINING_SUBJECT_CODES = tuple(subject["code"] for subject in CURRICULUM_7_CLASS if subject["code"] not in READY_SUBJECT_CODES)
_LICENSE = "Project-owned internal notes"
_ATTRIBUTION = "AI-Tutor project-authored subject notes, created for this pilot curriculum."


def _topic_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    topic_id = 1
    for subject in CURRICULUM_7_CLASS:
        for section_name, topics in subject["sections"]:
            for order_in_section, (topic_name, difficulty, subtopics) in enumerate(topics, start=1):
                rows.append(
                    {
                        "subject_code": subject["code"],
                        "subject_name": subject["name"],
                        "topic_id": topic_id,
                        "topic_name": topic_name,
                        "section_name": section_name,
                        "difficulty": difficulty,
                        "subtopics": subtopics,
                        "order_in_section": order_in_section,
                    }
                )
                topic_id += 1
    return [row for row in rows if row["subject_code"] in REMAINING_SUBJECT_CODES]


def _note_text(row: dict[str, Any]) -> str:
    subtopics = row.get("subtopics") or []
    subtopic_text = ", ".join(subtopics) if subtopics else "ключевые определения и базовые примеры"
    return (
        f"Тема «{row['topic_name']}» относится к предмету «{row['subject_name']}» и разделу «{row['section_name']}». "
        f"На этом шаге ученик должен понять основной смысл темы, выучить опорные термины и уметь объяснить их своими словами. "
        f"Рабочий минимум: {subtopic_text}. Сначала разбираем определение, затем короткий пример, затем типичную ошибку. "
        f"Если задание кажется сложным, нужно вернуться к названию темы, выделить главное понятие и проверить ответ по одному правилу. "
        f"Эта заметка является внутренним учебным источником проекта AI-Tutor и используется как безопасная RAG-опора без внешних материалов."
    )


def _chunk_hash(material_id: int, text: str) -> str:
    return hashlib.sha256(f"remaining:{material_id}:{text}".encode("utf-8")).hexdigest()[:16]


def _fallback(row: dict[str, Any]) -> dict[str, object]:
    answer = "понять главное понятие темы и объяснить его на простом примере"
    return {
        "topic_id": row["topic_id"],
        "question_text": f"Что главное нужно сделать при изучении темы «{row['topic_name']}»?",
        "type": "single",
        "options": [
            answer,
            "заучить случайный факт без объяснения",
            "пропустить определение и сразу угадывать ответ",
            "использовать правило из другой темы без проверки",
        ],
        "correct_answer": answer,
        "explanation": f"В теме «{row['topic_name']}» сначала нужно понять базовое понятие, затем применить его на простом примере.",
        "typical_mistakes": ["Отвечать по памяти без правила", "Путать тему с соседним разделом"],
        "difficulty": 1,
        "order_index": 1,
        "is_active": True,
    }


def build_remaining_subjects_internal_source_manifest() -> dict[str, object]:
    materials: list[dict[str, object]] = []
    chunks: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []
    fallbacks: list[dict[str, object]] = []
    source_counts: dict[str, int] = {}
    for row in _topic_rows():
        material_id = 30000 + int(row["topic_id"])
        text = _note_text(row)
        subject_code = str(row["subject_code"])
        source = f"internal_{subject_code}_notes"
        title = f"{row['subject_name']} internal notes — {row['topic_name']}"
        source_section = f"{row['section_name']} / {row['topic_name']}"
        metadata = {
            "subject_code": subject_code,
            "topic_id": row["topic_id"],
            "topic_name": row["topic_name"],
            "source_title": f"{row['subject_name']} internal source notes",
            "material_title": title,
            "source_url": f"internal://{subject_code}/project-authored-notes",
            "source_section": source_section,
            "license": _LICENSE,
            "attribution": _ATTRIBUTION,
            "source_mode": "project_owned_text_notes",
        }
        material = {
            "id": material_id,
            "topic_id": row["topic_id"],
            "subject_code": subject_code,
            "title": title,
            "content": text,
            "source": source,
            "source_url": f"internal://{subject_code}/project-authored-notes",
            "source_section": source_section,
            "license": _LICENSE,
            "attribution": _ATTRIBUTION,
            "status": "draft_internal_source_notes",
        }
        chunk = {
            "id": f"{subject_code}-internal-{row['topic_id']}-1",
            "material_id": material_id,
            "hash": _chunk_hash(material_id, text),
            "text": text,
            "embedding_json": "[]",
            "metadata_json": json.dumps(metadata, ensure_ascii=False),
        }
        materials.append(material)
        chunks.append(chunk)
        audit_rows.append(
            {
                "chunk_id": chunk["id"],
                "material_id": material_id,
                "material_title": title,
                "material_topic_id": row["topic_id"],
                "material_subject_code": subject_code,
                "metadata_json": chunk["metadata_json"],
            }
        )
        fallbacks.append(_fallback(row))
        source_counts[subject_code] = source_counts.get(subject_code, 0) + 1
    return {
        "mode": "remaining_subjects_internal_source_manifest",
        "subject": "remaining_subjects",
        "subject_codes": list(REMAINING_SUBJECT_CODES),
        "topic_count": len(materials),
        "source_counts": source_counts,
        "license": _LICENSE,
        "production_mutation": False,
        "db_write": False,
        "rag_write": False,
        "promotion_allowed": False,
        "materials": materials,
        "chunks": chunks,
        "audit_rows": audit_rows,
        "fallbacks": fallbacks,
    }


def write_manifest(path: Path) -> Path:
    manifest = build_remaining_subjects_internal_source_manifest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build remaining subject internal source/practice manifest")
    parser.add_argument("--out", default="/tmp/ai-tutor-remaining-subjects-manifest.json")
    args = parser.parse_args()
    out = write_manifest(Path(args.out))
    manifest = json.loads(out.read_text(encoding="utf-8"))
    print(json.dumps({"ok": True, "out": str(out), "topic_count": manifest["topic_count"], "subject_codes": manifest["subject_codes"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
