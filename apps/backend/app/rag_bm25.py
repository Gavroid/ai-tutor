"""Sprint 57: BM25 keyword search для RAG (без real embeddings).

BM25 (Best Matching 25) — классический ranking function для keyword search.
Используется как fallback когда real embeddings недоступны (4GB RAM limit).

Преимущества перед hash-based cosine similarity:
- ✅ Реальный keyword matching (TF-IDF style)
- ✅ Не требует sentence-transformers (200MB)
- ✅ Russian-friendly tokenization (Unicode word boundaries)
- ✅ Title boost (если material_title содержит query terms)
- ✅ Recency boost (новые материалы выше)
- ✅ Быстрый: O(n_chunks * avg_terms_per_chunk)

Гипотеза Sprint 57: BM25 улучшит Recall@5 с 0% (Sprint 43) до 40-60%.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime, timezone

logger = logging.getLogger(__name__)


# === Tokenization ===

# Russian + English stop words (короткий список — для производительности).
_STOP_WORDS = frozenset(
    {
        # Russian
        "и",
        "в",
        "на",
        "с",
        "по",
        "для",
        "что",
        "это",
        "как",
        "а",
        "но",
        "из",
        "за",
        "к",
        "о",
        "у",
        "от",
        "до",
        "же",
        "бы",
        "ли",
        "ни",
        "он",
        "она",
        "оно",
        "они",
        "мы",
        "вы",
        "я",
        "ты",
        "не",
        "да",
        "нет",
        "так",
        "вот",
        "если",
        "то",
        # English
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "what",
        "which",
        "who",
        "how",
        "when",
        "where",
    }
)


def tokenize(text: str) -> list[str]:
    """Sprint 57: Russian + English tokenization.

    Steps:
    1. Lowercase
    2. Split on non-word chars (Unicode \\w+ includes Russian)
    3. Remove stop words
    4. Remove tokens < 2 chars
    """
    if not text:
        return []
    text = text.lower()
    # \w+ in Python re includes Unicode letters (Russian, etc.)
    tokens = re.findall(r"\w+", text, re.UNICODE)
    # Filter
    return [t for t in tokens if len(t) >= 2 and t not in _STOP_WORDS]


# === BM25 ===

# Standard BM25 parameters (tuned for English; works well for Russian too).
_K1 = 1.5  # term frequency saturation
_B = 0.75  # document length normalization


def _idf(N: int, df: int) -> float:
    """Inverse document frequency: log((N - df + 0.5) / (df + 0.5) + 1)."""
    return math.log(((N - df + 0.5) / (df + 0.5)) + 1)


def bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    avg_dl: float,
    N: int,
    df_map: dict[str, int],
) -> float:
    """Sprint 57: BM25 score для одного документа.

    Args:
        query_tokens: токены запроса
        doc_tokens: токены документа
        avg_dl: средняя длина документа в коллекции
        N: общее число документов
        df_map: term -> document frequency (сколько документов содержат term)

    Returns:
        BM25 score (выше = лучше матч)
    """
    if not query_tokens or not doc_tokens:
        return 0.0

    doc_len = len(doc_tokens)
    doc_term_freqs = Counter(doc_tokens)

    score = 0.0
    for term in query_tokens:
        if term not in doc_term_freqs:
            continue
        tf = doc_term_freqs[term]
        df = df_map.get(term, 0)
        idf = _idf(N, df)
        # BM25 formula
        numerator = tf * (K1 := _K1) + 1
        denominator = tf + _K1 * (1 - _B + _B * doc_len / max(avg_dl, 1e-6))
        score += idf * numerator / denominator
    return score


# === Title boost ===


def title_boost(
    query_tokens: list[str],
    title: str | None,
    base_score: float,
    boost_factor: float = 1.5,
) -> float:
    """Sprint 57: boost score если query terms в title материала.

    Returns:
        base_score * boost_factor если все query terms в title, иначе base_score.
    """
    if not title or not query_tokens:
        return base_score
    title_tokens = set(tokenize(title))
    if not title_tokens:
        return base_score
    # Если ВСЕ query tokens в title — boost
    if all(qt in title_tokens for qt in query_tokens):
        return base_score * boost_factor
    # Если хотя бы 50% query tokens в title — small boost
    matches = sum(1 for qt in query_tokens if qt in title_tokens)
    if matches >= len(query_tokens) * 0.5:
        return base_score * (1 + (boost_factor - 1) * 0.5)
    return base_score


# === Recency boost ===


def recency_boost(
    base_score: float,
    created_at: datetime | None,
    reference_time: datetime | None = None,
    half_life_days: float = 90.0,
) -> float:
    """Sprint 57: boost недавние материалы.

    Args:
        base_score: BM25 score
        created_at: когда chunk был создан
        reference_time: текущее время (default: now)
        half_life_days: через сколько дней decay = 0.5

    Returns:
        base_score * decay_factor (0.5 .. 1.0+)
    """
    if not created_at:
        return base_score
    if reference_time is None:
        # Sprint continuation T1.3b: datetime.utcnow() deprecated в Python 3.12+.
        # Используем timezone-aware now() затем убираем tzinfo, чтобы
        # сохранить naive-UTC семантику сравнения с created_at (sqlite naive).
        reference_time = datetime.now(UTC).replace(tzinfo=None)
    # Если timezone-aware — convert to naive UTC
    if hasattr(created_at, "tzinfo") and created_at.tzinfo is not None:
        created_at = created_at.replace(tzinfo=None)
    age_days = max(0, (reference_time - created_at).total_seconds() / 86400)
    if age_days >= half_life_days * 4:  # way too old
        return base_score * 0.5
    decay = 0.5 ** (age_days / half_life_days)
    # 1.0 для свежих, 0.5 для очень старых
    return base_score * (0.5 + 0.5 * decay)


# === High-level search ===


def bm25_search(
    query: str,
    chunks: Iterable[dict],
    top_k: int = 5,
    title_boost_factor: float = 1.5,
    recency_enabled: bool = True,
) -> list[dict]:
    """Sprint 57: BM25 search по коллекции chunks.

    Args:
        query: поисковый запрос (Russian/English)
        chunks: iterable of dict с keys:
            - text: chunk text
            - material_title: optional, для title boost
            - created_at: optional ISO datetime string
            - (any other fields — pass-through)
        top_k: сколько результатов вернуть
        title_boost_factor: множитель для title match
        recency_enabled: применять recency boost

    Returns:
        list of dicts (chunks) sorted by score (descending).
    """
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    # Materialize chunks list (для multi-pass).
    chunks_list = list(chunks)
    if not chunks_list:
        return []

    # Pre-compute doc tokens + tokenize.
    doc_data: list[tuple[dict, list[str]]] = []
    for chunk in chunks_list:
        text = chunk.get("text", "")
        # Если есть material_title — добавляем в текст для индексации
        title = chunk.get("material_title", "")
        # В BM25 индексируем text + title (title имеет естественный boost через duplication).
        full_text = (title + " " + text) if title else text
        doc_data.append((chunk, tokenize(full_text)))

    # Stats.
    N = len(doc_data)
    if N == 0:
        return []
    avg_dl = sum(len(dt) for _, dt in doc_data) / N

    # Document frequency.
    df_map: dict[str, int] = {}
    for _, dt in doc_data:
        for term in set(dt):
            df_map[term] = df_map.get(term, 0) + 1

    # Score каждый chunk.
    scored: list[tuple[float, dict]] = []
    for chunk, doc_tokens in doc_data:
        score = bm25_score(
            query_tokens=query_tokens,
            doc_tokens=doc_tokens,
            avg_dl=avg_dl,
            N=N,
            df_map=df_map,
        )
        if score <= 0:
            continue
        # Title boost
        if title_boost_factor > 1.0:
            score = title_boost(query_tokens, chunk.get("material_title"), score, title_boost_factor)
        # Recency boost
        if recency_enabled and chunk.get("created_at"):
            try:
                created = datetime.fromisoformat(chunk["created_at"].replace("Z", ""))
                score = recency_boost(score, created)
            except (ValueError, TypeError):
                pass
        scored.append((score, chunk))

    # Sort по score desc.
    scored.sort(key=lambda x: -x[0])
    return [chunk for _, chunk in scored[:top_k]]
