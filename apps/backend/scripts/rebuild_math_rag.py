#!/usr/bin/env python3
"""Rebuild MVP math curriculum + RAG mapping from Vilenkin 6th grade PDFs.

This is intentionally narrow and production-oriented:
- subject code `math`
- two uploaded PDFs already present in the app container
- replaces the previous 3 artificial topics with real textbook topics
- indexes page ranges per topic instead of indexing both books under every topic

Run inside backend container:
    cd /app && python scripts/rebuild_math_rag.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.rag_models import RagChunk
from app.rag_persist import chunk_hash, get_or_compute_embedding
from app.subjects import models as subj_models

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
MATH_CODE = "math"
MATH_NAME = "Математика (6 класс - повторение пройденного материала)"
MATH_DESCRIPTION = "Реальный маршрут по учебнику Виленкина 6 класса: части 1–2."

PDFS = {
    1: "/app/uploads/teacher_sources/src_3_vilenkin_6_ch1.pdf",
    2: "/app/uploads/teacher_sources/src_3_vilenkin_6_ch2.pdf",
}


@dataclass(frozen=True)
class TopicSpec:
    section: str
    name: str
    difficulty: int
    part: int
    start_printed_page: int
    end_printed_page: int


# Printed page numbers from the textbook table of contents.
# PDF index offset is +1 for both files: printed page N is PDF page index N+1 in pypdf 1-based output.
TOPICS: list[TopicSpec] = [
    TopicSpec("§ 1. Вычисления и построения", "Среднее арифметическое", 2, 1, 14, 18),
    TopicSpec("§ 1. Вычисления и построения", "Проценты", 2, 1, 19, 26),
    TopicSpec("§ 1. Вычисления и построения", "Круговые диаграммы", 2, 1, 27, 31),
    TopicSpec("§ 1. Вычисления и построения", "Виды треугольников", 2, 1, 32, 36),
    TopicSpec("§ 1. Вычисления и построения", "Понятие множества", 2, 1, 37, 42),
    TopicSpec("§ 2. Действия со смешанными числами", "Разложение числа на простые множители", 2, 1, 43, 49),
    TopicSpec("§ 2. Действия со смешанными числами", "Наибольший общий делитель. Взаимно простые числа", 3, 1, 50, 54),
    TopicSpec("§ 2. Действия со смешанными числами", "Наименьшее общее кратное", 3, 1, 55, 59),
    TopicSpec("§ 2. Действия со смешанными числами", "Приведение дробей к наименьшему общему знаменателю", 3, 1, 60, 63),
    TopicSpec("§ 2. Действия со смешанными числами", "Сравнение, сложение и вычитание обыкновенных дробей", 3, 1, 64, 70),
    TopicSpec("§ 2. Действия со смешанными числами", "Сложение и вычитание смешанных чисел", 3, 1, 71, 79),
    TopicSpec("§ 2. Действия со смешанными числами", "Умножение смешанных чисел", 3, 1, 80, 86),
    TopicSpec("§ 2. Действия со смешанными числами", "Нахождение дроби от числа", 3, 1, 87, 92),
    TopicSpec("§ 2. Действия со смешанными числами", "Распределительное свойство умножения", 3, 1, 93, 98),
    TopicSpec("§ 2. Действия со смешанными числами", "Деление смешанных чисел", 4, 1, 99, 109),
    TopicSpec("§ 3. Отношения и пропорции", "Дробные выражения", 3, 1, 110, 118),
    TopicSpec("§ 3. Отношения и пропорции", "Отношения", 3, 1, 119, 124),
    TopicSpec("§ 3. Отношения и пропорции", "Пропорции", 3, 1, 125, 129),
    TopicSpec("§ 3. Отношения и пропорции", "Прямая и обратная пропорциональные зависимости", 4, 1, 130, 135),
    TopicSpec("§ 3. Отношения и пропорции", "Масштаб", 3, 1, 136, 141),
    TopicSpec("§ 3. Отношения и пропорции", "Симметрия", 3, 1, 142, 148),
    TopicSpec("§ 3. Отношения и пропорции", "Длина окружности и площадь круга. Шар", 4, 1, 149, 156),
    TopicSpec("§ 4. Действия с рациональными числами", "Положительные и отрицательные числа", 2, 2, 6, 14),
    TopicSpec("§ 4. Действия с рациональными числами", "Противоположные числа", 2, 2, 15, 18),
    TopicSpec("§ 4. Действия с рациональными числами", "Модуль числа", 2, 2, 19, 22),
    TopicSpec("§ 4. Действия с рациональными числами", "Сравнение положительных и отрицательных чисел", 3, 2, 23, 27),
    TopicSpec("§ 4. Действия с рациональными числами", "Изменение величин", 3, 2, 28, 32),
    TopicSpec("§ 4. Действия с рациональными числами", "Сложение с помощью координатной прямой", 3, 2, 33, 36),
    TopicSpec("§ 4. Действия с рациональными числами", "Сложение отрицательных чисел", 3, 2, 37, 40),
    TopicSpec("§ 4. Действия с рациональными числами", "Сложение чисел с разными знаками", 3, 2, 41, 45),
    TopicSpec("§ 4. Действия с рациональными числами", "Вычитание рациональных чисел", 3, 2, 46, 50),
    TopicSpec("§ 4. Действия с рациональными числами", "Умножение рациональных чисел", 3, 2, 51, 55),
    TopicSpec("§ 4. Действия с рациональными числами", "Деление рациональных чисел", 3, 2, 56, 61),
    TopicSpec("§ 4. Действия с рациональными числами", "Рациональные числа", 3, 2, 62, 66),
    TopicSpec("§ 4. Действия с рациональными числами", "Свойства действий с рациональными числами", 4, 2, 67, 75),
    TopicSpec("§ 5. Решение уравнений", "Раскрытие скобок", 3, 2, 76, 80),
    TopicSpec("§ 5. Решение уравнений", "Коэффициент", 3, 2, 81, 84),
    TopicSpec("§ 5. Решение уравнений", "Подобные слагаемые", 3, 2, 85, 89),
    TopicSpec("§ 5. Решение уравнений", "Решение уравнений", 4, 2, 90, 104),
    TopicSpec("§ 6. Координаты на плоскости", "Перпендикулярные прямые", 2, 2, 100, 104),
    TopicSpec("§ 6. Координаты на плоскости", "Координатная плоскость", 3, 2, 105, 109),
    TopicSpec("§ 6. Координаты на плоскости", "Столбчатые диаграммы и графики", 3, 2, 110, 123),
]


def printed_to_pdf_page(printed_page: int) -> int:
    return printed_page + 1


def clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def extract_pages(file_path: str, start_printed: int, end_printed: int) -> list[tuple[int, str]]:
    reader = PdfReader(file_path)
    pages: list[tuple[int, str]] = []
    for printed_page in range(start_printed, end_printed + 1):
        pdf_page = printed_to_pdf_page(printed_page)
        idx = pdf_page - 1
        if idx < 0 or idx >= len(reader.pages):
            continue
        text = clean_text(reader.pages[idx].extract_text() or "")
        if text:
            pages.append((printed_page, text))
    return pages


def chunk_pages(pages: list[tuple[int, str]]) -> list[tuple[str, int]]:
    chunks: list[tuple[str, int]] = []
    current = ""
    current_page = pages[0][0] if pages else 1
    for printed_page, text in pages:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text]
        for para in paragraphs:
            if len(current) + len(para) + 2 <= CHUNK_SIZE:
                if not current:
                    current_page = printed_page
                current = (current + "\n\n" + para).strip() if current else para
            else:
                if current:
                    chunks.append((current, current_page))
                    current = current[-CHUNK_OVERLAP:] if len(current) > CHUNK_OVERLAP else ""
                    current_page = printed_page
                if len(para) > CHUNK_SIZE:
                    for start in range(0, len(para), CHUNK_SIZE - CHUNK_OVERLAP):
                        part = para[start : start + CHUNK_SIZE].strip()
                        if part:
                            chunks.append((part, printed_page))
                    current = ""
                else:
                    current = para
                    current_page = printed_page
    if current:
        chunks.append((current, current_page))
    return chunks


def rebuild(apply: bool) -> None:
    db = SessionLocal()
    try:
        subject = db.scalar(select(subj_models.Subject).where(subj_models.Subject.code == MATH_CODE))
        if subject is None:
            subject = subj_models.Subject(
                code=MATH_CODE,
                name=MATH_NAME,
                description=MATH_DESCRIPTION,
                color="#3b82f6",
                icon="🔢",
                recommended_grade=7,
                age_min=12,
                age_max=14,
                is_active=True,
            )
            db.add(subject)
            db.flush()
        else:
            subject.name = MATH_NAME
            subject.description = MATH_DESCRIPTION
            subject.color = subject.color or "#3b82f6"
            subject.icon = subject.icon or "🔢"

        old_topics = db.execute(select(subj_models.Topic.id).join(subj_models.Section).where(subj_models.Section.subject_id == subject.id)).scalars().all()
        print(f"subject_id={subject.id} old_topics={len(old_topics)} new_topics={len(TOPICS)}")
        if not apply:
            for spec in TOPICS:
                print(f"DRY {spec.part}:{spec.start_printed_page}-{spec.end_printed_page} | {spec.section} | {spec.name}")
            return

        if old_topics:
            # Remove chunks belonging to previous math learning materials.
            old_material_ids = db.execute(select(subj_models.LearningMaterial.id).where(subj_models.LearningMaterial.topic_id.in_(old_topics))).scalars().all()
            if old_material_ids:
                db.execute(delete(RagChunk).where(RagChunk.material_id.in_(old_material_ids)))
            db.execute(delete(subj_models.LearningMaterial).where(subj_models.LearningMaterial.topic_id.in_(old_topics)))
            db.execute(delete(subj_models.Subtopic).where(subj_models.Subtopic.topic_id.in_(old_topics)))
            db.execute(delete(subj_models.Topic).where(subj_models.Topic.id.in_(old_topics)))
            db.execute(delete(subj_models.Section).where(subj_models.Section.subject_id == subject.id))
            db.flush()

        sections: dict[str, subj_models.Section] = {}
        topic_count = 0
        chunk_count = 0
        for section_order, section_name in enumerate(dict.fromkeys(t.section for t in TOPICS)):
            sec = subj_models.Section(subject_id=subject.id, name=section_name, order_index=section_order)
            db.add(sec)
            db.flush()
            sections[section_name] = sec

        section_topic_ord: dict[str, int] = {name: 0 for name in sections}
        for spec in TOPICS:
            topic = subj_models.Topic(
                section_id=sections[spec.section].id,
                name=spec.name,
                difficulty=spec.difficulty,
                order_index=section_topic_ord[spec.section],
            )
            section_topic_ord[spec.section] += 1
            db.add(topic)
            db.flush()
            topic_count += 1

            file_path = PDFS[spec.part]
            material = subj_models.LearningMaterial(
                topic_id=topic.id,
                title=f"Виленкин 6 класс — часть {spec.part}: {spec.name}",
                content="{}",
                source="Виленкин 6 класс",
                file_path=file_path,
                status="published",
                source_type="pdf",
            )
            db.add(material)
            db.flush()

            pages = extract_pages(file_path, spec.start_printed_page, spec.end_printed_page)
            chunks = chunk_pages(pages)
            for chunk_text, printed_page in chunks:
                embedding = get_or_compute_embedding(chunk_text, db_session=db)
                h = chunk_hash(material.id, chunk_text)
                metadata = {
                    "subject_id": subject.id,
                    "topic_id": topic.id,
                    "topic_name": topic.name,
                    "section": spec.section,
                    "material_title": material.title,
                    "file_path": file_path,
                    "part": spec.part,
                    "page_number": printed_page,
                    "page_range": [spec.start_printed_page, spec.end_printed_page],
                }
                db.add(RagChunk(
                    material_id=material.id,
                    hash=h,
                    text=chunk_text,
                    embedding_json=json.dumps(embedding),
                    metadata_json=json.dumps(metadata, ensure_ascii=False),
                ))
                chunk_count += 1

        db.commit()
        print(f"DONE topics={topic_count} chunks={chunk_count}")
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    rebuild(apply=args.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
