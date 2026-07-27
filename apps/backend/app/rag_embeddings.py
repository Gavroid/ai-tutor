"""Sprint 70: Real RAG embeddings via sentence-transformers.

Использует модель paraphrase-multilingual-MiniLM-L12-v2 (384 dim,
multilingual RU+EN, ~500MB RAM, ~1 сек на encoding).

Recall@3: 10% (hash-based) → 60-80% (real embeddings, ожидается).

Usage:
    from app.rag_embeddings import get_embedder

    embedder = get_embedder()
    vectors = embedder.encode(["text 1", "text 2"])  # numpy array (N, 384)
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Lazy loading (model ~500MB, загружаем только при первом использовании)
_MODEL = None
_MODEL_LOCK = threading.Lock()
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384
# Fallback: HF_HOME для локального cache
os.environ.setdefault("HF_HOME", "/tmp/hf_cache")


def get_embedder():
    """Sprint 70: lazy-load sentence-transformer model (thread-safe singleton).

    Returns:
        SentenceTransformer instance или None если sentence-transformers
        не установлен (graceful fallback).
    """
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    with _MODEL_LOCK:
        if _MODEL is not None:
            return _MODEL
        try:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading sentence-transformer model: %s", MODEL_NAME)
            _MODEL = SentenceTransformer(MODEL_NAME)
            logger.info("Model loaded: dim=%s", _MODEL.get_sentence_embedding_dimension())
            return _MODEL
        except ImportError as e:
            logger.warning("sentence-transformers not available: %s", e)
            return None
        except Exception as e:
            logger.error("Failed to load model: %s", e)
            return None


def encode_texts(texts: list[str]) -> Optional[np.ndarray]:
    """Sprint 70: encode list of texts → numpy array (N, 384).

    Args:
        texts: list of strings для encoding.

    Returns:
        numpy array shape (N, EMBEDDING_DIM) или None если model unavailable.
    """
    embedder = get_embedder()
    if embedder is None:
        return None
    try:
        # normalize=True → cosine similarity = dot product
        vectors = embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return vectors
    except Exception as e:
        logger.error("Encoding failed: %s", e)
        return None


def encode_single(text: str) -> Optional[list[float]]:
    """Sprint 70: encode single text → list of floats (для БД).

    Returns:
        list of 384 floats или None.
    """
    result = encode_texts([text])
    if result is None or len(result) == 0:
        return None
    return result[0].tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Sprint 70: cosine similarity между двумя vectors.

    Args:
        a, b: list of 384 floats.

    Returns:
        float в [-1, 1] (обычно [0, 1] для normalized vectors).
    """
    a_np = np.array(a)
    b_np = np.array(b)
    # For normalized vectors, cosine = dot product
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))


def is_available() -> bool:
    """Sprint 70: check если sentence-transformers установлен."""
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False
