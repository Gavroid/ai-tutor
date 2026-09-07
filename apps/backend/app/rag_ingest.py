"""Sprint 4 RAG (MVP): PDF → text → chunks → embed → persist.

Scope (минимальный, НЕ включает admin UI / batch uploads):
- extract_text_from_pdf(path: str) -> list[PageText]
  Возвращает список (page_number, text) из PDF.
- chunk_text_into_rag(text: str, max_chars: int = 800) -> list[str]
  Простой paragraph-based chunking с max_chars limit.
- ingest_pdf(material_id: int, pdf_path: str, db: Session) -> int
  Полный pipeline: extract → chunk → embed → save в rag_chunks.

Reuses:
- app.rag_embeddings.encode_single() — single text embedding (с fallback на hash)
- app.rag_persist.add_chunks_persistent() — сохранение в БД

Out of scope (требует отдельный sprint + UI решения владельца):
- Admin UI для batch uploads
- OCR для scanned PDFs (pytesseract integration)
- Automatic material detection (subject_id / topic_id assignment)
- Reindex existing materials
- Async background processing (RQ/Celery)
- Monitoring dashboard

Это MVP — для production data ingestion нужен полный sprint с владельцем.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.rag_embeddings import encode_single, is_available
from app.rag_models import RagChunk
from app.rag_persist import add_chunks_persistent

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# Sprint 4 RAG: константы для chunking (вынесены для testability).
DEFAULT_MAX_CHARS = 800  # ~200-300 слов (хорошо для embedding моделей)
DEFAULT_OVERLAP = 100  # overlap между чанками (контекст не теряется)


@dataclass
class PageText:
    """Sprint 4 RAG: текст одной страницы PDF."""

    page_number: int  # 1-indexed
    text: str


def extract_text_from_pdf(pdf_path: str | Path) -> list[PageText]:
    """Извлекает текст из PDF, возвращает список (page_number, text).

    Использует pypdf 5.x API. Поддерживает encrypted PDFs (None для пустого текста).

    Args:
        pdf_path: путь к PDF файлу.

    Returns:
        list[PageText] с page_number (1-indexed) и text.
        Пустой список если файл не читается или пустой.

    Raises:
        FileNotFoundError: если файл не существует.
        ValueError: если файл не PDF (pypdf.PdfReader raise).
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF не найден: {path}")

    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[PageText] = []
    for idx, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            logger.warning("Sprint 4 RAG: page %d extract failed: %s", idx, exc)
            text = ""
        pages.append(PageText(page_number=idx, text=text.strip()))

    logger.info(
        "Sprint 4 RAG: extracted %d pages from %s (total chars: %d)",
        len(pages),
        path.name,
        sum(len(p.text) for p in pages),
    )
    return pages


def chunk_text_into_rag(
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """Простой paragraph-based chunking с overlap.

    Стратегия:
    1. Split по \n\n (paragraph boundary).
    2. Если paragraph > max_chars → split по предложениям (. ! ?).
    3. Если предложение > max_chars → split по словам.
    4. Accumulate в chunks с overlap (последние `overlap` chars повторяются).

    Args:
        text: полный текст для chunking.
        max_chars: максимальная длина chunk (default 800).
        overlap: overlap между соседними chunks (default 100).

    Returns:
        list[str] — non-empty chunks.
    """
    if not text or not text.strip():
        return []

    # Step 1: paragraph split.
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []

    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Если paragraph помещается целиком — append.
        if len(current_chunk) + len(para) + 2 <= max_chars:
            current_chunk = f"{current_chunk}\n\n{para}".strip() if current_chunk else para
            continue

        # Иначе flush current_chunk (если есть) и обработать overflow.
        if current_chunk:
            chunks.append(current_chunk)

        # Если para > max_chars — split по предложениям.
        if len(para) > max_chars:
            sub_chunks = _split_long_paragraph(para, max_chars, overlap)
            chunks.extend(sub_chunks[:-1])  # всё кроме последнего
            current_chunk = sub_chunks[-1] if sub_chunks else ""
        else:
            # Overlap: оставляем хвост current_chunk (последние overlap chars).
            current_chunk = (
                current_chunk[-overlap:] + "\n\n" + para
                if overlap and current_chunk
                else para
            )

    if current_chunk:
        chunks.append(current_chunk)

    # Filter пустые.
    return [c for c in chunks if c.strip()]


def _split_long_paragraph(text: str, max_chars: int, overlap: int) -> list[str]:
    """Split paragraph > max_chars по предложениям или словам."""
    # Sentence split: . ! ? followed by space или end of string.
    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks: list[str] = []
    current = ""

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue

        if len(current) + len(sent) + 1 <= max_chars:
            current = f"{current} {sent}".strip() if current else sent
        else:
            if current:
                chunks.append(current)
            # Если предложение > max_chars — split по словам.
            if len(sent) > max_chars:
                word_chunks = _split_by_words(sent, max_chars)
                chunks.extend(word_chunks[:-1])
                current = word_chunks[-1] if word_chunks else ""
            else:
                current = sent

    if current:
        chunks.append(current)
    return chunks


def _split_by_words(text: str, max_chars: int) -> list[str]:
    """Hard split по словам для очень длинных предложений."""
    words = text.split()
    chunks: list[str] = []
    current = ""

    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = f"{current} {word}".strip() if current else word
        else:
            if current:
                chunks.append(current)
            current = word

    if current:
        chunks.append(current)
    return chunks


def ingest_pdf(material_id: int, pdf_path: str | Path, db: Session) -> int:
    """Полный pipeline: PDF → text → chunks → embed → persist.

    Args:
        material_id: LearningMaterial.id (foreign key).
        pdf_path: путь к PDF.
        db: SQLAlchemy session.

    Returns:
        int — количество chunks создано (или обновлено, если hash уже был).

    Raises:
        FileNotFoundError: если PDF не существует.
        ValueError: если PDF некорректный.

    Note:
        Если chunks с таким hash уже существуют — они перезаписываются
        (idempotent re-index).
    """
    pages = extract_text_from_pdf(pdf_path)
    if not pages:
        logger.warning("Sprint 4 RAG: PDF %s содержит 0 страниц", pdf_path)
        return 0

    # Собираем все chunks (с metadata: page_number).
    all_chunks: list[tuple[int, str]] = []  # (page_number, chunk_text)
    for page in pages:
        chunks = chunk_text_into_rag(page.text)
        for chunk in chunks:
            all_chunks.append((page.page_number, chunk))

    if not all_chunks:
        logger.warning("Sprint 4 RAG: 0 chunks после chunking PDF %s", pdf_path)
        return 0

    # Embeddings (с fallback на hash-based).
    use_real = is_available()
    logger.info(
        "Sprint 4 RAG: embedding mode = %s",
        "real (sentence-transformers)" if use_real else "hash-based fallback",
    )

    chunk_records: list[tuple[str, list[float], dict]] = []  # (text, embedding, metadata)
    for page_num, text in all_chunks:
        embedding: list[float] | None = None
        if use_real:
            try:
                embedding = encode_single(text)
            except Exception as exc:
                logger.warning("Sprint 4 RAG: encode_single failed, using hash: %s", exc)
        if embedding is None:
            embedding = _hash_embedding(text)

        metadata = {"page_number": page_num, "source": "pdf"}
        chunk_records.append((text, embedding, metadata))

    # Persist через существующий add_chunks_persistent (сигнатура: db, material_id, chunks, embeddings).
    texts = [c[0] for c in chunk_records]
    embeddings_list = [c[1] for c in chunk_records]
    n_saved = add_chunks_persistent(db, material_id, texts, embeddings_list)
    db.commit()
    logger.info("Sprint 4 RAG: persisted %d chunks for material_id=%d", len(n_saved), material_id)
    return len(n_saved)


def _hash_embedding(text: str) -> list[float]:
    """Fallback: hash-based embedding (если sentence-transformers недоступен)."""
    import struct

    # 384-dim vector (как real model).
    h = hashlib.sha512(text.encode("utf-8")).digest()
    # Expand hash до 384 * 4 bytes (float32).
    repeats = (384 * 4) // len(h) + 1
    expanded = (h * repeats)[: 384 * 4]
    return [v / 255.0 - 0.5 for v in struct.unpack(f"{384}f", expanded)]
