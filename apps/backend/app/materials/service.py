"""Сервис загрузки и поиска учебных материалов (Этап 10, MVP).

Поддерживает:
- TXT/Markdown (нативно)
- PDF (через pypdf)
- DOCX (через python-docx)
- Изображения — только регистрация, OCR TODO

Использует in-memory поиск (substring) — для MVP достаточно.
Полнотекстовый поиск через PostgreSQL tsvector или ElasticSearch — TODO.
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.subjects import models as subj_models

ALLOWED_EXTS = {".txt", ".md", ".pdf", ".docx", ".png", ".jpg", ".jpeg"}
MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB
OCR_LANGS = {"rus", "eng"}


def _safe_filename(name: str) -> str:
    """Удаляем опасные символы из имени файла."""
    name = re.sub(r"[^\w\-. ]", "_", name)
    return name[:200]


def _extract_text(file_path: Path, ext: str, ocr_langs: list[str] | None = None) -> str:
    """Извлекает текст из файла. Для изображений — OCR через pytesseract."""
    if ext in {".txt", ".md"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        chunks = []
        for page in reader.pages:
            try:
                chunks.append(page.extract_text() or "")
            except Exception:
                chunks.append("")
        return "\n".join(chunks)
    if ext == ".docx":
        from docx import Document

        doc = Document(str(file_path))
        return "\n".join(p.text for p in doc.paragraphs)
    if ext in {".png", ".jpg", ".jpeg"}:
        return _ocr_image(file_path, ocr_langs or list(OCR_LANGS))
    return ""


def _ocr_image(file_path: Path, langs: list[str]) -> str:
    """OCR через pytesseract. Если недоступен — fallback.

    Требования:
      - pytesseract
      - tesseract-ocr в системе + языковые пакеты (tesseract-ocr-rus, tesseract-ocr-eng)
    В Docker Alpine: apk add tesseract-ocr tesseract-ocr-data-rus tesseract-ocr-data-eng
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return (
            f"[OCR недоступен: pytesseract или Pillow не установлены. "
            f"Файл {file_path.name} сохранён, но текст не извлечён.]"
        )

    try:
        img = Image.open(file_path)
        # Конвертируем RGBA → RGB (tesseract не любит альфа-канал)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        lang_str = "+".join(langs) if langs else "eng"
        return pytesseract.image_to_string(img, lang=lang_str)
    except Exception as exc:
        return f"[OCR ошибка: {exc!r}]"


def save_uploaded_material(
    db: Session,
    topic: subj_models.Topic,
    uploaded_filename: str,
    content_bytes: bytes,
    source_label: str | None,
    ocr_langs: list[str] | None = None,
) -> subj_models.LearningMaterial:
    """Сохраняет загруженный файл в UPLOAD_DIR и записывает метаданные в БД."""
    if len(content_bytes) > MAX_FILE_BYTES:
        raise ValueError(f"Файл слишком большой: {len(content_bytes)} > {MAX_FILE_BYTES}")

    ext = Path(uploaded_filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise ValueError(f"Неподдерживаемый тип: {ext}. Допустимо: {sorted(ALLOWED_EXTS)}")

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Уникальное имя: hash + оригинал
    digest = hashlib.sha256(content_bytes).hexdigest()[:12]
    safe = _safe_filename(uploaded_filename)
    stored_name = f"{digest}_{safe}"
    full_path = upload_dir / stored_name

    # Защита от path traversal — full_path должен оставаться внутри upload_dir
    full_path = full_path.resolve()
    if not str(full_path).startswith(str(upload_dir.resolve())):
        raise ValueError("Недопустимое имя файла")

    full_path.write_bytes(content_bytes)

    # Извлекаем текст
    text = _extract_text(full_path, ext, ocr_langs)
    if not text.strip():
        text = f"[файл {uploaded_filename} — текст не извлечён, {len(content_bytes)} байт]"

    material = subj_models.LearningMaterial(
        topic_id=topic.id,
        title=uploaded_filename,
        content=text[:50000],  # лимит на контент
        source=source_label or f"upload:{uploaded_filename}",
        file_path=str(full_path.relative_to(Path("/app"))) if str(full_path).startswith("/app/") else str(full_path),
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def search_materials(
    db: Session, query: str, topic_id: int | None = None, limit: int = 10
) -> list[dict]:
    """Простой поиск по подстроке (case-insensitive).

    Для больших объёмов переключаем на PostgreSQL tsvector.
    """
    if not query or len(query) < 2:
        return []

    stmt = select(subj_models.LearningMaterial)
    if topic_id is not None:
        stmt = stmt.where(subj_models.LearningMaterial.topic_id == topic_id)
    materials = db.scalars(stmt.limit(500)).all()  # защита от больших выборок

    q_lower = query.lower()
    results = []
    for m in materials:
        text = m.content.lower()
        idx = text.find(q_lower)
        if idx == -1:
            continue
        snippet_start = max(0, idx - 100)
        snippet_end = min(len(m.content), idx + len(query) + 100)
        snippet = m.content[snippet_start:snippet_end]
        if snippet_start > 0:
            snippet = "…" + snippet
        if snippet_end < len(m.content):
            snippet = snippet + "…"
        results.append(
            {
                "material_id": m.id,
                "topic_id": m.topic_id,
                "title": m.title,
                "snippet": snippet,
                "source": m.source,
            }
        )
        if len(results) >= limit:
            break
    return results