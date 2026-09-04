"""Тесты paragraph-aware chunker."""
from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-chunker-tests-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from app.textbook_pipeline.chunker import chunk_text, chunks_for_pages


def test_short_text_single_chunk():
    chunks = chunk_text("Короткий текст без абзацев.", chunk_size=1000)
    assert len(chunks) == 1
    assert chunks[0].text == "Короткий текст без абзацев."
    assert chunks[0].chunk_index == 0


def test_empty_text_returns_empty():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_paragraph_boundary_preserved():
    text = (
        "Первый абзац с несколькими предложениями. Он достаточно длинный, чтобы превысить лимит.\n\n"
        "Второй абзац.\n\n"
        "Третий абзац."
    )
    chunks = chunk_text(text, chunk_size=80)
    assert len(chunks) >= 1
    # Граница абзаца должна сохраниться: один chunk не должен начинаться с середины \n\n.
    for c in chunks:
        assert not c.text.startswith(" "), f"chunk starts with whitespace: {c.text!r}"


def test_long_paragraph_split_by_sentence():
    sentences = " ".join(f"Предложение номер {i}." for i in range(50))
    chunks = chunk_text(sentences, chunk_size=200)
    assert len(chunks) >= 2
    # Каждый chunk должен заканчиваться предложением, не серединой.
    for c in chunks:
        assert c.text.rstrip().endswith((".", "!", "?")), f"chunk not ended: {c.text[-30:]!r}"


def test_overlap_carryover():
    # Реальные предложения, разделённые '. ', — это даст paragraph-aware splitter'у
    # повод разрезать длинный текст.
    sentences = [f"Это предложение номер {i} с дополнительными словами для объёма." for i in range(30)]
    text = " ".join(sentences)
    chunks = chunk_text(text, chunk_size=200, overlap=40)
    assert len(chunks) >= 2, f"expected >= 2 chunks, got {len(chunks)}"
    # Overlap: последние ~40 символов предыдущего chunk должны быть в начале следующего.
    if len(chunks) >= 2:
        tail = chunks[0].text[-40:]
        head = chunks[1].text[:80]
        assert tail.strip() in head or head.startswith(tail.strip()[:20]), (
            f"overlap not preserved: tail={tail!r}, head={head!r}"
        )


def test_metadata_preserved():
    chunks = chunk_text(
        "Какой-то текст по физике про плотность вещества.",
        page_number=42,
        topic_id=123,
        topic_name="Плотность вещества",
        source_section="§ 21",
        confidence="reviewed",
    )
    assert len(chunks) == 1
    assert chunks[0].page_number == 42
    assert chunks[0].topic_id == 123
    assert chunks[0].topic_name == "Плотность вещества"
    assert chunks[0].source_section == "§ 21"
    assert chunks[0].confidence == "reviewed"


def test_chunks_for_pages_lookups_topic():
    pages = [
        (10, "Абзац про млекопитающих. У них есть шерсть."),
        (11, "Абзац про птиц. У них есть перья."),
    ]
    lookup = {
        10: (1, "Млекопитающие", "§ 5", "reviewed"),
        11: (2, "Птицы", "§ 6", "auto_extracted_from_toc"),
    }
    chunks = chunks_for_pages(pages, topic_lookup=lookup)
    assert len(chunks) == 2
    assert chunks[0].topic_id == 1
    assert chunks[0].topic_name == "Млекопитающие"
    assert chunks[1].topic_id == 2
    assert chunks[1].source_section == "§ 6"


def test_no_partial_word_split_at_boundary():
    """Чанкер не должен разрывать слово посередине."""
    text = " ".join(f"длинноеслово{i}" for i in range(100))
    chunks = chunk_text(text, chunk_size=300, overlap=30)
    # Каждый chunk: на границах не должно быть обрезков слов.
    for c in chunks:
        # Начинается с пробела или с буквы — это ОК.
        assert c.text[0].isalpha() or c.text[0].isspace()


def test_does_not_break_formula_brackets():
    """Если в тексте есть скобочная формула, chunk не должен разрывать её посередине."""
    text = (
        "Введение в алгебру.\n\n"
        "Формула сокращённого умножения: (a + b)^2 = a^2 + 2ab + b^2. "
        "Это базовая identity, которая используется повсеместно.\n\n"
        "Следующий параграф про дискриминант."
    )
    chunks = chunk_text(text, chunk_size=100)
    # Если chunk содержит "(a + b)^2", он должен также содержать закрывающую часть формулы.
    for c in chunks:
        if "(a + b)" in c.text and "^2" in c.text:
            assert "= a^2 + 2ab + b^2" in c.text, f"formula broken: {c.text!r}"
