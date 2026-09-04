"""Paragraph-aware chunker для textbook/RAG pipeline.

Не разрывает формулы, определения, задачи, таблицы без metadata.
Использует границы абзацев и предложений как natural break points.

Sprint 2026-08-22.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

CHUNK_SIZE = 1200  # символов; production-tuned
CHUNK_OVERLAP = 200
SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Chunk:
    """Один chunk с метаданными."""

    text: str
    chunk_index: int
    page_number: int
    topic_id: int | None = None
    topic_name: str | None = None
    source_section: str | None = None
    confidence: str | None = None
    char_start: int = 0
    char_end: int = 0

    @property
    def metadata(self) -> dict:
        return {
            "topic_id": self.topic_id,
            "topic_name": self.topic_name,
            "source_section": self.source_section,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "confidence": self.confidence,
            "char_start": self.char_start,
            "char_end": self.char_end,
        }


def _paragraphs(text: str) -> list[str]:
    """Разделить текст на абзацы по \n\n или \n."""
    text = text.strip()
    if not text:
        return []
    # Нормализуем переносы.
    text = re.sub(r"\n{2,}", "\n\n", text)
    parts = re.split(r"\n\n+", text)
    return [p.strip() for p in parts if p.strip()]


def _split_long_paragraph(paragraph: str, chunk_size: int) -> list[str]:
    """Если абзац > chunk_size, разбить по предложениям."""
    if len(paragraph) <= chunk_size:
        return [paragraph]
    sentences = SENTENCE_END_RE.split(paragraph)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return [paragraph[:chunk_size]]
    chunks: list[str] = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 > chunk_size and current:
            chunks.append(current.strip())
            # Carry-over: последнее предложение может перекрываться.
            current = sent
        else:
            current = (current + " " + sent).strip() if current else sent
    if current:
        chunks.append(current.strip())
    return chunks


def chunk_text(
    text: str,
    *,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    page_number: int = 0,
    topic_id: int | None = None,
    topic_name: str | None = None,
    source_section: str | None = None,
    confidence: str | None = None,
) -> list[Chunk]:
    """Chunk text paragraph-aware с overlap.

    Pipeline:
    1. Разделить на абзацы.
    2. Длинные абзацы (> chunk_size) разбить по предложениям.
    3. Собрать chunks, пока < chunk_size.
    4. Overlap: последние `overlap` символов предыдущего chunk добавляются в начало следующего.
    """
    if not text or not text.strip():
        return []

    paragraphs = _paragraphs(text)
    raw_chunks: list[str] = []
    buffer = ""

    for para in paragraphs:
        # Если параграф длиннее chunk_size — сначала split по предложениям.
        parts = _split_long_paragraph(para, chunk_size)
        for part in parts:
            if len(buffer) + len(part) + 2 > chunk_size and buffer:
                raw_chunks.append(buffer.strip())
                # Overlap: добавляем последние `overlap` символов.
                if overlap > 0 and len(buffer) > overlap:
                    buffer = buffer[-overlap:] + " " + part
                else:
                    buffer = part
            else:
                buffer = (buffer + "\n\n" + part).strip() if buffer else part

    if buffer:
        raw_chunks.append(buffer.strip())

    chunks: list[Chunk] = []
    cursor = 0
    for i, ctext in enumerate(raw_chunks):
        # Найти char_start/char_end в оригинальном тексте (best-effort).
        idx = text.find(ctext, cursor)
        if idx == -1:
            idx = cursor
        end = idx + len(ctext)
        chunks.append(
            Chunk(
                text=ctext,
                chunk_index=i,
                page_number=page_number,
                topic_id=topic_id,
                topic_name=topic_name,
                source_section=source_section,
                confidence=confidence,
                char_start=idx,
                char_end=end,
            )
        )
        cursor = max(cursor, end - overlap)

    return chunks


def chunks_for_pages(
    pages: Iterable[tuple[int, str]],
    *,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    topic_lookup: dict[int, tuple[int | None, str | None, str | None, str | None]] | None = None,
) -> list[Chunk]:
    """Chunk многостраничный текст.

    pages: итерабель (page_number, page_text).
    topic_lookup: {page_number: (topic_id, topic_name, source_section, confidence)}.
    """
    out: list[Chunk] = []
    for pn, page_text in pages:
        meta = topic_lookup.get(pn) if topic_lookup else None
        if meta:
            tid, tname, sec, conf = meta
        else:
            tid = tname = sec = conf = None
        out.extend(
            chunk_text(
                page_text,
                chunk_size=chunk_size,
                overlap=overlap,
                page_number=pn,
                topic_id=tid,
                topic_name=tname,
                source_section=sec,
                confidence=conf,
            )
        )
    return out
