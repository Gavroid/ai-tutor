"""Sprint 8.3: RAG persistence + embedding cache.

Sprint 3.5.1 — DEAD CODE TEST FILE (но в работе)
================================================
RAG (search по учебникам) написан в app/rag_persist.py + app/rag.py,
миграция 0012 в БД, тесты проходят. НО в hot path не подключён:
app/ai/service.py::explain_topic() НЕ вызывает rag_search перед LLM.

Sprint 3.5.2 (следующая задача) — подключить RAG к explain_topic.

Сейчас 12 тестов помечены skip, чтобы не давать false sense of "всё работает".
Когда RAG подключён — раскомментировать pytestmark.
"""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skip(
    reason="Sprint 3.5.1: RAG code есть, но не подключён к hot path. "
           "Sprint 3.5.2 подключит — тогда раскомментировать."
)

import pytest

from app.rag_persist import (
    EMBEDDING_CACHE_ENABLED,
    EMBEDDING_DIM,
    chunk_hash,
    embedding_to_json,
    get_or_compute_embedding,
    json_to_embedding,
    text_hash,
)


class TestHashUtils:
    def test_chunk_hash_stable(self):
        h1 = chunk_hash(1, "Привет")
        h2 = chunk_hash(1, "Привет")
        assert h1 == h2
        assert len(h1) == 64  # sha256 hex

    def test_chunk_hash_differs_by_material_id(self):
        h1 = chunk_hash(1, "Текст")
        h2 = chunk_hash(2, "Текст")
        assert h1 != h2

    def test_chunk_hash_differs_by_text(self):
        h1 = chunk_hash(1, "Текст A")
        h2 = chunk_hash(1, "Текст B")
        assert h1 != h2

    def test_text_hash_stable(self):
        a = text_hash("Привет, мир!")
        b = text_hash("Привет, мир!")
        assert a == b


class TestEmbeddingSerialization:
    def test_roundtrip(self):
        vec = [0.1, 0.2, -0.5, 1.0]
        s = embedding_to_json(vec)
        assert json_to_embedding(s) == vec

    def test_roundtrip_large(self):
        vec = [0.001 * i for i in range(384)]
        s = embedding_to_json(vec)
        restored = json_to_embedding(s)
        assert len(restored) == 384
        for i in range(0, 384, 50):
            assert abs(restored[i] - vec[i]) < 1e-9

    def test_empty(self):
        assert json_to_embedding("") == []
        assert json_to_embedding("not-json") == []


class TestGetOrComputeEmbedding:
    def test_hash_fallback_when_no_api_key(self):
        """Без AI_API_KEY — используется hash-fallback (детерминированный)."""
        env = os.environ.copy()
        env.pop("AI_API_KEY", None)
        with pytest.MonkeyPatch.context() as mp:
            for k, v in env.items():
                mp.setenv(k, v)
            mp.delenv("AI_API_KEY", raising=False)

            v1 = get_or_compute_embedding("Тестовый текст")
            v2 = get_or_compute_embedding("Тестовый текст")
            assert v1 == v2  # детерминированный
            assert len(v1) == EMBEDDING_DIM

    def test_different_texts_produce_different_embeddings(self):
        v1 = get_or_compute_embedding("Текст один")
        v2 = get_or_compute_embedding("Другой текст")
        assert v1 != v2

    def test_with_cache_disabled(self):
        """С отключённым кэшем — каждый раз compute (но результат детерминирован)."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.rag_persist.EMBEDDING_CACHE_ENABLED", False)
            v1 = get_or_compute_embedding("Текст")
            v2 = get_or_compute_embedding("Текст")
            # Hash-fallback стабильный, поэтому равны
            assert v1 == v2


class TestCachePersistence:
    """Sprint 8.3 — embedding cache через БД (real persistent)."""

    def test_cache_hit_second_call(self):
        """Второй вызов с тем же текстом быстрее, но важно — возвращает то же."""
        v1 = get_or_compute_embedding("Test cache text")
        v2 = get_or_compute_embedding("Test cache text")
        assert v1 == v2
        # Если бы в первый раз fallback, второй — cache hit
        # (в любом случае значения совпадают)

    def test_cache_unique_per_text(self):
        a = get_or_compute_embedding("Текст для A")
        b = get_or_compute_embedding("Текст для B")
        assert a != b  # hash-fallback даёт разные embeddings
