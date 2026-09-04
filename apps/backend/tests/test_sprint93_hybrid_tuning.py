"""Sprint 93: hybrid search weight tuning tests."""

from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest

# === Tests: _detect_hybrid_weights ===


def test_detect_short_query_keyword_heavy():
    """Sprint 93: short query → keyword-heavy (0.7/0.3)."""
    from app.rag_router import _detect_hybrid_weights

    bm25, emb = _detect_hybrid_weights("площадь круга")
    assert bm25 == 0.7
    assert emb == 0.3


def test_detect_math_symbols_keyword_heavy():
    """Sprint 93: query с math symbols → keyword-heavy."""
    from app.rag_router import _detect_hybrid_weights

    bm25, emb = _detect_hybrid_weights("a² + b² = c²")
    assert bm25 == 0.7
    assert emb == 0.3


def test_detect_medium_query_balanced():
    """Sprint 93: medium query → balanced (0.5/0.5)."""
    from app.rag_router import _detect_hybrid_weights

    bm25, emb = _detect_hybrid_weights("как найти площадь круга через диаметр")
    # 6 words → medium
    assert bm25 == 0.5
    assert emb == 0.5


def test_detect_long_query_semantic_heavy():
    """Sprint 93: long query (>10 слов) → semantic-heavy (0.3/0.7)."""
    from app.rag_router import _detect_hybrid_weights

    long_q = (
        "объясни пожалуйста подробно как решать такие задачи по алгебре "
        "в восьмом классе с использованием дискриминанта"
    )
    bm25, emb = _detect_hybrid_weights(long_q)
    assert bm25 == 0.3
    assert emb == 0.7


def test_detect_exactly_3_words_keyword_heavy():
    """Sprint 93: ровно 3 слова → keyword-heavy."""
    from app.rag_router import _detect_hybrid_weights

    bm25, emb = _detect_hybrid_weights("теорема Пифагора")
    assert bm25 == 0.7


def test_detect_exactly_10_words_semantic_heavy():
    """Sprint 93: ровно 10 слов → semantic-heavy."""
    from app.rag_router import _detect_hybrid_weights

    q = "один два три четыре пять шесть семь восемь девять десять"  # 10 words
    bm25, emb = _detect_hybrid_weights(q)
    assert bm25 == 0.3
    assert emb == 0.7


def test_detect_with_digit_keyword_heavy():
    """Sprint 93: query с цифрой → keyword-heavy (has_math trigger)."""
    from app.rag_router import _detect_hybrid_weights

    # 6 words but contains digit
    bm25, emb = _detect_hybrid_weights("чему равно 42 в квадрате плюс пять")
    assert bm25 == 0.7
    assert emb == 0.3


def test_weights_sum_to_one():
    """Sprint 93: weights всегда sum to 1.0."""
    from app.rag_router import _detect_hybrid_weights

    test_queries = [
        "короткий",
        "это запрос средней длины",
        "длинный запрос который содержит много слов и должен попасть в semantic категорию",
        "x² + y²",
        "ABC",  # English short
    ]
    for q in test_queries:
        bm25, emb = _detect_hybrid_weights(q)
        assert abs(bm25 + emb - 1.0) < 1e-9, f"Query '{q}': weights don't sum to 1.0"


def test_detect_function_exists_in_router():
    """Sprint 93: _detect_hybrid_weights function exported."""
    import app.rag_router

    assert hasattr(app.rag_router, "_detect_hybrid_weights")
    assert callable(app.rag_router._detect_hybrid_weights)


def test_hybrid_endpoint_uses_detected_weights():
    """Sprint 93: hybrid endpoint вызывает _detect_hybrid_weights."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "app",
            "rag_router.py",
        )
    ) as f:
        content = f.read()
    assert "_detect_hybrid_weights(payload.query)" in content
    assert "Sprint 93: heuristic" in content
