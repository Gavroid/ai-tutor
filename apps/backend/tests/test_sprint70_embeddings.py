"""Sprint 70: real RAG embeddings tests."""

from __future__ import annotations

import os

# Sprint 64: disable OpenTelemetry для tests
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import numpy as np
import pytest

# === Module-level tests (без DB) ===


def test_rag_embeddings_module_imports():
    """Sprint 70: rag_embeddings module imports."""
    from app import rag_embeddings

    assert rag_embeddings.MODEL_NAME == "paraphrase-multilingual-MiniLM-L12-v2"
    assert rag_embeddings.EMBEDDING_DIM == 384


def test_rag_embeddings_is_available():
    """Sprint 70: sentence-transformers установлен."""
    from app import rag_embeddings

    # Должен быть True (мы установили torch + sentence-transformers)
    assert rag_embeddings.is_available() is True


def test_cosine_similarity_identical_vectors():
    """Sprint 70: identical vectors → cosine=1.0."""
    from app.rag_embeddings import cosine_similarity

    v = [1.0, 0.0, 0.0]
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-6


def test_cosine_similarity_orthogonal_vectors():
    """Sprint 70: orthogonal vectors → cosine=0.0."""
    from app.rag_embeddings import cosine_similarity

    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert abs(cosine_similarity(a, b)) < 1e-6


def test_cosine_similarity_opposite_vectors():
    """Sprint 70: opposite vectors → cosine=-1.0."""
    from app.rag_embeddings import cosine_similarity

    a = [1.0, 0.0, 0.0]
    b = [-1.0, 0.0, 0.0]
    assert abs(cosine_similarity(a, b) - (-1.0)) < 1e-6


def test_cosine_similarity_normalized_vectors():
    """Sprint 70: для normalized vectors → cosine=dot product."""
    from app.rag_embeddings import cosine_similarity

    # Normalized vectors (length=1)
    a = [0.6, 0.8, 0.0]  # length=1
    b = [0.8, 0.6, 0.0]  # length=1
    # cos = 0.6*0.8 + 0.8*0.6 = 0.96
    assert abs(cosine_similarity(a, b) - 0.96) < 1e-6


# === Real encoding tests (требует ~500MB RAM для model) ===


@pytest.mark.slow
def test_encode_texts_russian():
    """Sprint 70: Russian text encoding (multilingual model)."""
    from app.rag_embeddings import encode_texts

    vectors = encode_texts(["Привет, мир!", "Как дела?"])
    assert vectors is not None
    assert vectors.shape == (2, 384)
    # Similar texts → higher similarity
    sim = float(np.dot(vectors[0], vectors[1]))
    assert 0.3 < sim < 1.0  # Russian texts related


@pytest.mark.slow
def test_encode_texts_english():
    """Sprint 70: English text encoding."""
    from app.rag_embeddings import encode_texts

    vectors = encode_texts(["Hello world!", "How are you?"])
    assert vectors is not None
    assert vectors.shape == (2, 384)


@pytest.mark.slow
def test_encode_single():
    """Sprint 70: encode_single returns list of 384 floats."""
    from app.rag_embeddings import encode_single

    vec = encode_single("test text")
    assert vec is not None
    assert isinstance(vec, list)
    assert len(vec) == 384
    # All values должны быть floats
    assert all(isinstance(x, float) for x in vec)


@pytest.mark.slow
def test_semantic_similarity_related_vs_unrelated():
    """Sprint 70: related texts > similarity than unrelated."""
    from app.rag_embeddings import encode_texts

    related = ["Кошка ест рыбу", "Кот любит морепродукты"]
    unrelated = ["Кошка ест рыбу", "Машина едет быстро"]

    v_related = encode_texts(related)
    v_unrelated = encode_texts(unrelated)

    sim_related = float(np.dot(v_related[0], v_related[1]))
    sim_unrelated = float(np.dot(v_unrelated[0], v_unrelated[1]))

    # Related texts должны быть more similar
    assert sim_related > sim_unrelated, (
        f"Related similarity {sim_related:.3f} should be > " f"unrelated {sim_unrelated:.3f}"
    )


@pytest.mark.slow
def test_normalized_vectors_unit_length():
    """Sprint 70: output vectors нормализованы (unit length)."""
    from app.rag_embeddings import encode_texts

    vectors = encode_texts(["test 1", "test 2", "test 3"])
    for v in vectors:
        length = float(np.linalg.norm(v))
        # normalize_embeddings=True → length ≈ 1.0
        assert abs(length - 1.0) < 0.01, f"Vector length {length} should be ≈1.0"
