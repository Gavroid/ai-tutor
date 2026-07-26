# Sprint 57 — RAG BM25 Quality Improvements

**Дата:** 2026-07-26
**Production:** 192.168.1.86 (LXC, 4GB RAM)
**RAG mode:** BM25 keyword search (без real embeddings)

## 🎯 Проблема (Sprint 43)

Hash-based pseudo-embeddings не работают для semantic search:
- **Recall@3: 0.00%**
- **Recall@5: 0.00%**
- **MRR: 0.000**

Sprint 20 был SKIPPED (4GB RAM недостаточно для sentence-transformers ~200MB).

## ✅ Sprint 57 решение: BM25

**Алгоритм:** BM25 (Best Matching 25) — классический ranking function для keyword search.

**Преимущества:**
- ✅ Реальный keyword matching (TF-IDF style)
- ✅ Не требует sentence-transformers (200MB)
- ✅ Russian-friendly tokenization (`re.findall(r"\w+", text, re.UNICODE)`)
- ✅ Title boost (если material_title содержит query terms)
- ✅ Recency boost (новые материалы выше)
- ✅ Быстрый: ~10s для 30 queries на 2770 chunks (vs 50ms+ для embedding)

**Результаты на production:**

| Метрика | Sprint 43 (hash) | Sprint 57 (BM25) | Δ |
|---------|------------------|------------------|---|
| **Recall@3** | 0.00% | **10.00%** | +10pp |
| **Recall@5** | 0.00% | **10.00%** | +10pp |
| **MRR** | 0.000 | **0.100** | +0.100 |

**Per-subject:**
| Subject | Recall@3 | Notes |
|---------|----------|-------|
| **Math** | **100%** | ✅ Perfect (text содержит direct keywords) |
| History | 0% | ground truth issue (subject in title неявно) |
| Biology, Chemistry, etc. | 0% | нужна better ground truth |

## 🏗️ Architecture

### Files added (Sprint 57)
- `apps/backend/app/rag_bm25.py` (NEW, 8.8 KB)
  - `tokenize()` — Russian + English tokenization
  - `bm25_score()` — pure BM25 algorithm
  - `title_boost()` — 1.5x boost если all query terms в title
  - `recency_boost()` — 0.5x для очень старых, 1.0x для свежих
  - `bm25_search()` — high-level search с pre-computed df_map
- `apps/backend/scripts/rag_benchmark_bm25.py` (NEW, 10 KB)
  - Real production benchmark с 30 ground truth questions
- `apps/backend/tests/test_sprint57_bm25.py` (NEW, 9.6 KB)
  - 20 тестов (tokenization, scoring, title boost, recency, integration)

### Files modified
- `apps/backend/app/rag_persist.py` — `search_bm25_persistent()` function
- `apps/backend/app/rag_router.py` — `POST /api/v1/rag/search/bm25` endpoint

## 🔌 API

### POST /api/v1/rag/search/bm25

**Request:**
```json
{
  "query": "Python переменная",
  "top_k": 5,
  "material_id": null  // optional filter
}
```

**Response:**
```json
{
  "query": "Python переменная",
  "hits": [
    {
      "chunk_id": "...",
      "material_id": 1,
      "text": "...",
      "score": 0.0,
      "metadata": {"material_title": "Python intro", "topic_id": 1, "page_number": 1}
    },
    ...
  ]
}
```

**Auth:** required (cookie or Bearer)

## 🧪 Tests (20/20 passed)

- `test_tokenize_basic_russian` — Russian tokenization
- `test_tokenize_filters_short_tokens` — min 2 chars
- `test_tokenize_handles_empty_string` — edge case
- `test_tokenize_lowercases` — case normalization
- `test_bm25_score_returns_zero_for_no_match` — non-match → 0
- `test_bm25_score_positive_for_match` — match → positive
- `test_bm25_score_higher_for_relevant_doc` — TF-IDF ordering
- `test_title_boost_full_match` — 1.5x boost
- `test_title_boost_partial_match` — 1.25x boost
- `test_title_boost_no_match` — no boost
- `test_title_boost_handles_none` — None safe
- `test_recency_boost_fresh_content` — fresh = 1.0x
- `test_recency_boost_old_content` — 300 days = 0.55x
- `test_recency_boost_very_old` — 360 days = 0.5x (cap)
- `test_bm25_search_returns_relevant_chunks` — integration
- `test_bm25_search_empty_input` — edge cases
- `test_bm25_search_title_boost_works` — boost integration
- `test_bm25_search_recency_boost_works` — recency integration
- `test_search_bm25_persistent_with_empty_db` — empty DB
- `test_search_bm25_persistent_with_chunks` — real DB integration

## 🔍 Algorithm details

### BM25 formula
```
score(D, Q) = Σ (idf(qi) · (tf(qi, D) · (k1 + 1)) / 
                (tf(qi, D) + k1 · (1 - b + b · |D| / avgdl)))
```

Where:
- `k1 = 1.5` (term frequency saturation)
- `b = 0.75` (document length normalization)
- `idf(q) = log((N - df(q) + 0.5) / (df(q) + 0.5) + 1)`

### Tokenization
- Lowercase normalization
- `re.findall(r"\w+", text, re.UNICODE)` — Russian + English
- Stop words filter (RU + EN)
- Min 2 chars

### Title boost
- 100% match (all query terms in title): ×1.5
- 50%+ match: ×1.25
- 0% match: ×1.0

### Recency boost
- 0 days: ×1.0 (fresh)
- 90 days (half_life): ×0.75
- 180 days: ×0.625
- 360+ days: ×0.5 (cap)

## 📊 Production verify

✅ `POST /api/v1/rag/search/bm25` → 200
✅ Recall@3: 10% (vs 0% in Sprint 43)
✅ Math subject: 100% (perfect)
✅ All 20 tests passed
✅ Coverage 78% (unchanged)

## 🎯 Sprint 57 results

| Показатель | Значение |
|---|---|
| **pytest passed** | +20 (621 → 641) |
| **New files** | 3 (rag_bm25, benchmark, tests) |
| **Modified files** | 2 (rag_persist, rag_router) |
| **Recall@5 improvement** | 0% → 10% (+10pp) |
| **MRR improvement** | 0.000 → 0.100 |
| **Math subject** | 100% perfect |
| **Production deploy** | ✅ Health 200 |

## 🔮 Sprint 58+ (backlog)

- **Sprint 58**: Coverage 78% → 85% (+50 tests)
- **Sprint 59**: Multi-child support
- **Sprint 60**: Voice input (Whisper)
- **Sprint 61**: Adaptive difficulty
- **Sprint 62**: OpenTelemetry
- **Sprint 63**: Admin guide docs
- **Sprint 64**: Performance optimization
- **Sprint 65**: Final report (Sprint 57-65)

## 🔗 См. также

- [docs/RAG-BENCHMARK.md](RAG-BENCHMARK.md) — Sprint 43 (hash-based, Recall=0%)
- [docs/ARCHITECTURE-ADDENDUM.md](ARCHITECTURE-ADDENDUM.md) — Sprint 54
- [docs/CHANGELOG-SPRINT-16-56.md](CHANGELOG-SPRINT-16-56.md) — full archive