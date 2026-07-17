#!/usr/bin/env python3
"""Sprint 4.1.1 — index_materials.py

Скрипт для индексации PDF/учебных материалов в RAG-базу.

Запуск:
  - вручную:    docker exec deploy-backend-1 python3 /app/scripts/index_materials.py [--material-id N] [--all]
  - через cron: см. deploy/monitoring/index-cron.sh (Sprint 4.1.4)

Что делает:
- Находит learning_materials с status=published и file_path (PDF)
- Извлекает текст через pypdf
- Разбивает на чанки по 800 chars (overlap 100)
- Для каждого чанка:
  - POST /api/v1/rag/index { material_id, text, metadata }
  - metadata: { material_title, page_number, chapter, subject }

Идемпотентно: повторный index не дублирует (idempotent по hash).
Resume на failure: пропускает уже проиндексированные chunks.

Sprint 4.1.1 — Sprint 4 (RAG indexing pipeline).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

# Добавляем /app в sys.path чтобы импортировать app.*
sys.path.insert(0, "/app")

from pypdf import PdfReader

from app.config import get_settings
from app.db.session import SessionLocal
from app.rag_persist import (
    get_or_compute_embedding,
    add_chunks_persistent,
    chunk_hash,
)
from app.rag_models import RagChunk
from app.subjects import models as subj_models

# === Параметры ===
CHUNK_SIZE = 800       # символов на chunk
CHUNK_OVERLAP = 100    # overlap между chunks (для контекста)
PROGRESS_EVERY = 10    # логировать каждые N chunks


def extract_pdf_text(file_path: str) -> list[tuple[int, str]]:
    """Читает PDF, возвращает [(page_number, page_text), ...].

    Использует pypdf (уже в requirements).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF не найден: {file_path}")

    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            print(f"  [warn] page {i} extraction failed: {e}")
            text = ""
        # Очистка: схлопываем множественные переносы
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        text = text.strip()
        if text:
            pages.append((i, text))
    return pages


def chunk_pages(
    pages: list[tuple[int, str]],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[tuple[str, int]]:
    """Разбивает (page_num, text) на chunks.

    Возвращает [(chunk_text, page_number), ...].
    Chunk может начаться на одной странице и закончиться на другой —
    мы запоминаем page_number первой страницы chunk'а.
    """
    chunks: list[tuple[str, int]] = []
    current = ""
    current_page = 1

    for page_num, text in pages:
        # Разбиваем page_text на абзацы по \n\n
        paragraphs = text.split("\n\n")

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Если current + para не превышает chunk_size → добавляем
            if len(current) + len(para) + 2 <= chunk_size:
                current = (current + "\n\n" + para).strip() if current else para
                if not chunks and current:
                    current_page = page_num
            else:
                # Сохраняем current как chunk (если не пустой)
                if current:
                    chunks.append((current, current_page))
                    # Overlap: берём последние overlap chars
                    if overlap > 0 and len(current) > overlap:
                        current = current[-overlap:]
                    else:
                        current = ""

                # Если сам para > chunk_size → split further by sentences
                if len(para) > chunk_size:
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    for sent in sentences:
                        sent = sent.strip()
                        if not sent:
                            continue
                        if len(current) + len(sent) + 1 <= chunk_size:
                            current = (current + " " + sent).strip() if current else sent
                            current_page = page_num
                        else:
                            if current:
                                chunks.append((current, current_page))
                            current = sent
                            current_page = page_num
                else:
                    current = para
                    current_page = page_num

    # Финальный chunk
    if current:
        chunks.append((current, current_page))

    return chunks


def index_material(material_id: int, dry_run: bool = False) -> dict:
    """Индексирует один material. Возвращает stats dict."""
    s = SessionLocal()
    try:
        mat = s.get(subj_models.LearningMaterial, material_id)
        if not mat:
            return {"ok": False, "error": f"material {material_id} не найден"}

        title = mat.title
        file_path = mat.file_path
        topic_id = mat.topic_id

        if not file_path:
            return {"ok": False, "error": f"material {material_id} без file_path (text-only?)"}

        print(f"\n=== Indexing material #{material_id}: {title} ===")
        print(f"  file: {file_path}")
        print(f"  topic_id: {topic_id}")

        # 1. Extract PDF
        try:
            pages = extract_pdf_text(file_path)
        except FileNotFoundError as e:
            return {"ok": False, "error": str(e)}
        print(f"  pages extracted: {len(pages)}")
        if not pages:
            return {"ok": False, "error": "PDF пустой или не читается"}

        # 2. Check existing chunks (idempotent)
        existing_count = (
            s.query(RagChunk)
            .filter(RagChunk.material_id == material_id)
            .count()
        )
        print(f"  existing chunks: {existing_count}")

        # 3. Chunk
        chunks = chunk_pages(pages)
        print(f"  new chunks: {len(chunks)}")

        if dry_run:
            return {
                "ok": True,
                "material_id": material_id,
                "pages": len(pages),
                "chunks": len(chunks),
                "dry_run": True,
            }

        # 4. Index via RAG (use persistent add_chunks_persistent)
        # Collect all chunks first
        chunk_texts = [c[0] for c in chunks]
        chunk_page_nums = [c[1] for c in chunks]

        # Compute embeddings (idempotent via get_or_compute_embedding)
        embeddings = [get_or_compute_embedding(text) for text in chunk_texts]

        # Get material title for metadata
        metadata = {
            "material_title": title,
            "file_path": file_path,
            "topic_id": topic_id,
        }

        # Add via persistent (idempotent: hash-based, no duplicates)
        # We add to rag_chunks table directly
        from sqlalchemy import select as sa_select

        added_count = 0
        skipped_count = 0
        for chunk_text, page_num, embedding in zip(chunk_texts, chunk_page_nums, embeddings):
            h = chunk_hash(material_id, chunk_text)
            existing = (
                s.query(RagChunk)
                .filter(RagChunk.hash == h)
                .first()
            )
            if existing is not None:
                skipped_count += 1
                continue

            chunk_meta = dict(metadata)
            chunk_meta["page_number"] = page_num

            chunk = RagChunk(
                material_id=material_id,
                hash=h,
                text=chunk_text,
                embedding_json=str(embedding).replace("'", '"') if isinstance(embedding, list) else "[]",
                metadata_json=str(chunk_meta).replace("'", '"'),
            )
            s.add(chunk)
            added_count += 1
            if added_count % PROGRESS_EVERY == 0:
                print(f"  indexed {added_count}/{len(chunks)}")

        s.commit()
        print(f"  ✓ added: {added_count}, skipped (existing): {skipped_count}")

        return {
            "ok": True,
            "material_id": material_id,
            "title": title,
            "pages": len(pages),
            "chunks_total": len(chunks),
            "added": added_count,
            "skipped": skipped_count,
        }
    finally:
        s.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Index materials to RAG")
    parser.add_argument(
        "--material-id",
        type=int,
        help="Index one material by ID",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Index all published materials with file_path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be indexed without actually indexing",
    )
    args = parser.parse_args()

    if not args.material_id and not args.all:
        parser.print_help()
        print("\n[error] нужно --material-id N или --all")
        return 1

    print("=" * 60)
    print("Sprint 4.1.1 — index_materials.py")
    print("=" * 60)

    started = time.time()

    s = SessionLocal()
    try:
        if args.material_id:
            materials = [s.get(subj_models.LearningMaterial, args.material_id)]
        else:
            materials = (
                s.query(subj_models.LearningMaterial)
                .filter(subj_models.LearningMaterial.status == "published")
                .filter(subj_models.LearningMaterial.file_path.isnot(None))
                .all()
            )
    finally:
        s.close()

    if not materials:
        print("Нет materials для индексации")
        return 1

    results = []
    for mat in materials:
        if mat is None:
            print(f"Material не найден")
            continue
        r = index_material(mat.id, dry_run=args.dry_run)
        results.append(r)
        if not r.get("ok"):
            print(f"  ✗ {r.get('error', 'unknown error')}")

    elapsed = time.time() - started
    print("\n" + "=" * 60)
    print(f"DONE in {elapsed:.1f}s")
    success = sum(1 for r in results if r.get("ok"))
    print(f"  {success}/{len(results)} materials успешно")
    print("=" * 60)

    return 0 if success == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())