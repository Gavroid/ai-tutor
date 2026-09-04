"""Sprint 57: BM25 keyword search tests."""
from __future__ import annotations

import math
from datetime import datetime, timedelta

import pytest

# === Tokenization tests ===

def test_tokenize_basic_russian():
    """Sprint 57: tokenization работает для русского."""
    from app.rag_bm25 import tokenize

    tokens = tokenize("Что такое переменная в Python?")
    # Ожидаем значимые токены, БЕЗ стоп-слов
    assert "переменная" in tokens
    assert "python" in tokens
    # Без "что", "в", "?" (стоп-слова и punctuation)
    assert "что" not in tokens
    assert "в" not in tokens


def test_tokenize_filters_short_tokens():
    """Sprint 57: tokens < 2 chars удаляются."""
    from app.rag_bm25 import tokenize

    tokens = tokenize("Я в а и")
    # Только "я" (1 char) → empty
    # "в" (1 char) → filtered
    # "а" (1 char) → filtered
    # "и" (1 char) → filtered
    assert tokens == []


def test_tokenize_handles_empty_string():
    """Sprint 57: empty string → empty list."""
    from app.rag_bm25 import tokenize

    assert tokenize("") == []
    assert tokenize(None or "") == []


def test_tokenize_lowercases():
    """Sprint 57: lowercase normalization."""
    from app.rag_bm25 import tokenize

    tokens = tokenize("ПЕРЕМЕННАЯ Variable")
    assert "переменная" in tokens
    assert "variable" in tokens


# === BM25 scoring tests ===

def test_bm25_score_returns_zero_for_no_match():
    """Sprint 57: нет match → 0 score."""
    from app.rag_bm25 import bm25_score

    score = bm25_score(
        query_tokens=["квантовая", "физика"],
        doc_tokens=["алгебра", "уравнения"],
        avg_dl=2.0,
        N=10,
        df_map={"квантовая": 1, "физика": 1, "алгебра": 5},
    )
    assert score == 0.0


def test_bm25_score_positive_for_match():
    """Sprint 57: match → positive score."""
    from app.rag_bm25 import bm25_score

    score = bm25_score(
        query_tokens=["python", "переменная"],
        doc_tokens=["python", "переменная", "типы", "данных"],
        avg_dl=4.0,
        N=10,
        df_map={"python": 5, "переменная": 3, "типы": 4, "данных": 6},
    )
    assert score > 0


def test_bm25_score_higher_for_relevant_doc():
    """Sprint 57: более relevant doc → higher score."""
    from app.rag_bm25 import bm25_score

    df_map = {"python": 5, "переменная": 3, "функция": 4}

    # Doc 1: 2 matches (python + переменная)
    score_high = bm25_score(
        query_tokens=["python", "переменная"],
        doc_tokens=["python", "переменная", "функция"],
        avg_dl=3.0,
        N=10,
        df_map=df_map,
    )

    # Doc 2: 1 match (python only)
    score_low = bm25_score(
        query_tokens=["python", "переменная"],
        doc_tokens=["python", "функция", "класс"],
        avg_dl=3.0,
        N=10,
        df_map=df_map,
    )

    assert score_high > score_low


# === Title boost tests ===

def test_title_boost_full_match():
    """Sprint 57: all query terms в title → boost."""
    from app.rag_bm25 import title_boost

    score = title_boost(
        query_tokens=["python", "переменная"],
        title="Python переменная tutorial",
        base_score=10.0,
        boost_factor=1.5,
    )
    assert score == 15.0  # 10 * 1.5


def test_title_boost_partial_match():
    """Sprint 57: 50% match → small boost (1.25x)."""
    from app.rag_bm25 import title_boost

    score = title_boost(
        query_tokens=["python", "переменная"],
        title="Python tutorial",
        base_score=10.0,
        boost_factor=1.5,
    )
    # 50% match (1 of 2) → 1 + (1.5-1)*0.5 = 1.25
    assert score == 12.5


def test_title_boost_no_match():
    """Sprint 57: no title terms → no boost."""
    from app.rag_bm25 import title_boost

    score = title_boost(
        query_tokens=["python", "переменная"],
        title="Алгебра",
        base_score=10.0,
        boost_factor=1.5,
    )
    assert score == 10.0


def test_title_boost_handles_none():
    """Sprint 57: None title → no boost."""
    from app.rag_bm25 import title_boost

    score = title_boost(
        query_tokens=["python"],
        title=None,
        base_score=10.0,
        boost_factor=1.5,
    )
    assert score == 10.0


# === Recency boost tests ===

def test_recency_boost_fresh_content():
    """Sprint 57: свежий контент → no decay."""
    from app.rag_bm25 import recency_boost

    now = datetime(2024, 6, 1, 12, 0, 0)
    score = recency_boost(
        base_score=10.0,
        created_at=now,
        reference_time=now,
        half_life_days=90.0,
    )
    # age = 0 → decay = 1.0 → multiplier = 0.5 + 0.5*1.0 = 1.0
    assert score == 10.0


def test_recency_boost_old_content():
    """Sprint 57: старый контент (180 дней) → 0.75x boost."""
    from app.rag_bm25 import recency_boost

    now = datetime(2024, 6, 1, 12, 0, 0)
    old = now - timedelta(days=180)
    score = recency_boost(
        base_score=10.0,
        created_at=old,
        reference_time=now,
        half_life_days=90.0,
    )
    # age = 180, half_life = 90 → decay = 0.5^2 = 0.25
    # multiplier = 0.5 + 0.5*0.25 = 0.625
    assert score == pytest.approx(6.25, rel=0.01)


def test_recency_boost_very_old():
    """Sprint 57: очень старый (360 дней, 4x half_life) → 0.5x."""
    from app.rag_bm25 import recency_boost

    now = datetime(2024, 6, 1, 12, 0, 0)
    very_old = now - timedelta(days=360)
    score = recency_boost(
        base_score=10.0,
        created_at=very_old,
        reference_time=now,
        half_life_days=90.0,
    )
    # >= 4x half_life → multiplier = 0.5
    assert score == 5.0


# === High-level bm25_search tests ===

def test_bm25_search_returns_relevant_chunks():
    """Sprint 57: BM25 search возвращает relevant chunks в порядке score."""
    from app.rag_bm25 import bm25_search

    chunks = [
        {"id": "1", "text": "Python — это язык программирования", "material_title": "Python intro"},
        {"id": "2", "text": "Алгебра — раздел математики", "material_title": "Алгебра"},
        {"id": "3", "text": "Переменная в Python", "material_title": "Python variables"},
        {"id": "4", "text": "История России", "material_title": "История"},
    ]

    results = bm25_search(
        query="Python переменная",
        chunks=chunks,
        top_k=3,
        title_boost_factor=1.5,
        recency_enabled=False,  # disable для детерминированности
    )

    # Должны быть 2 chunk'а с match (id=1, 3).
    # id=2 (Алгебра) и id=4 (История) — score=0, не в results.
    assert len(results) == 2
    # Top results должны быть Python-related
    top_ids = [r["id"] for r in results]
    assert "3" in top_ids  # "Переменная в Python"
    assert "1" in top_ids  # "Python — это язык"
    # "Алгебра" или "История" НЕ должны быть в results (score=0)
    assert "2" not in top_ids
    assert "4" not in top_ids


def test_bm25_search_empty_input():
    """Sprint 57: empty input → empty output."""
    from app.rag_bm25 import bm25_search

    assert bm25_search("test", [], top_k=5) == []
    assert bm25_search("", [{"text": "test"}], top_k=5) == []
    # query с только stop words
    assert bm25_search("и в на", [{"text": "test"}], top_k=5) == []


def test_bm25_search_title_boost_works():
    """Sprint 57: title boost действительно поднимает relevant chunks."""
    from app.rag_bm25 import bm25_search

    chunks = [
        {"id": "1", "text": "random text 1", "material_title": "Unrelated title"},
        {"id": "2", "text": "random text 2", "material_title": "Python переменная guide"},
    ]

    results = bm25_search(
        query="Python переменная",
        chunks=chunks,
        top_k=1,
        title_boost_factor=10.0,  # большой boost
        recency_enabled=False,
    )
    # Chunk 2 должен выиграть (title содержит оба query terms)
    assert results[0]["id"] == "2"


def test_bm25_search_recency_boost_works():
    """Sprint 57: свежий контент выше старого при равном BM25 score."""
    # Используем explicit "now" чтобы test был детерминированным.
    from app.rag_bm25 import bm25_search, recency_boost
    now = datetime(2024, 6, 1, 12, 0, 0)
    old = (now - timedelta(days=300)).isoformat()
    fresh = now.isoformat()

    chunks = [
        {"id": "old", "text": "Python переменная", "material_title": "X", "created_at": old},
        {"id": "fresh", "text": "Python переменная", "material_title": "X", "created_at": fresh},
    ]

    # BM25 score для обоих chunks одинаковый (текст идентичный).
    # Recency boost должен сделать "fresh" выше.
    fresh_score = recency_boost(10.0, datetime.fromisoformat(fresh), reference_time=now)
    old_score = recency_boost(10.0, datetime.fromisoformat(old), reference_time=now)
    assert fresh_score > old_score
    # Fresh should be ~10.0, old should be ~5.5 (300/90 = 3.33 half-life)
    assert fresh_score == pytest.approx(10.0, rel=0.01)
    assert old_score == pytest.approx(5.5, rel=0.05)

    # Verify bm25_search uses recency boost.
    # Monkeypatch default reference time для теста.
    import app.rag_bm25 as bm25_module

    original_func = bm25_module.recency_boost
    bm25_module.recency_boost = lambda *a, **kw: original_func(*a, reference_time=now, **kw)
    try:
        results = bm25_search(
            query="Python переменная",
            chunks=chunks,
            top_k=2,
            title_boost_factor=1.0,  # disable title boost
            recency_enabled=True,
        )
        # Fresh должен быть первым
        assert results[0]["id"] == "fresh"
        assert results[1]["id"] == "old"
    finally:
        bm25_module.recency_boost = original_func


# === Integration test: search_bm25_persistent ===

def test_search_bm25_persistent_with_empty_db():
    """Sprint 57: empty DB → empty results."""
    from app.db.session import Base, engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    from app.db.session import SessionLocal
    from app.rag_persist import search_bm25_persistent

    with SessionLocal() as db:
        results = search_bm25_persistent(db, "test query", top_k=5)
        assert results == []


def test_search_bm25_persistent_with_chunks():
    """Sprint 57: BM25 search находит relevant chunks в БД."""
    from app.db.session import Base, engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    import json

    from app.db.session import SessionLocal
    from app.rag_models import RagChunk
    from app.rag_persist import add_chunks_persistent, search_bm25_persistent
    from sqlalchemy import text

    # Insert test chunks напрямую через ORM.
    with SessionLocal() as db:
        chunks_data = [
            {
                "material_id": 1,
                "text": "Python — это язык программирования. Переменная в Python хранит значение.",
                "metadata": {"material_title": "Python intro", "topic_id": 1, "page_number": 1},
            },
            {
                "material_id": 2,
                "text": "Алгебра изучает операции. Уравнения — основа алгебры.",
                "metadata": {"material_title": "Алгебра", "topic_id": 10, "page_number": 5},
            },
            {
                "material_id": 3,
                "text": "Переменная в Python может быть int, str, list. Типы данных важны.",
                "metadata": {"material_title": "Python variables", "topic_id": 1, "page_number": 2},
            },
        ]
        for i, c in enumerate(chunks_data):
            row = RagChunk(
                material_id=c["material_id"],
                hash=f"test-hash-{i}",
                text=c["text"],
                embedding_json="[]",
                metadata_json=json.dumps(c["metadata"]),
            )
            db.add(row)
        db.commit()

    # BM25 search "Python переменная" — должен найти chunks 1 и 3.
    with SessionLocal() as db:
        results = search_bm25_persistent(db, "Python переменная", top_k=3)
        assert len(results) == 2
        # Check that Алгебра (material_id=2) не в results.
        material_ids = [r.material_id for r in results]
        assert 2 not in material_ids
        # Check that Python chunks есть в results.
        assert 1 in material_ids
        assert 3 in material_ids
