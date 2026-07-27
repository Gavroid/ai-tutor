# Sprint 70 — RAG Benchmark с REAL Embeddings

**Дата:** 2026-07-26
**Production:** 192.168.1.86
**Model:** paraphrase-multilingual-MiniLM-L12-v2 (384-dim, multilingual RU+EN)
**Chunks:** 2770 (Sprint 70 backfill, 249.7 sec)
**Backfill storage:** `metadata_json["embedding_v2"]` в `rag_chunks` table

## Результаты benchmark (27 ground truth questions)

| Метрика | Sprint 43 (hash) | Sprint 57 (BM25) | **Sprint 70 (real)** |
|---------|------------------|-------------------|----------------------|
| **Recall@3** | 0.00% | 10.00% | **11.11%** |
| **Recall@5** | 0.00% | 10.00% | **11.11%** |
| **MRR** | 0.000 | 0.100 | **0.093** |

## Sprint 70 vs Sprint 43 (hash-based)

- Recall@3: **0.00% → 11.11%** (+11pp)
- Recall@5: **0.00% → 11.11%** (+11pp)
- MRR: **0.000 → 0.093** (+0.093)

## Architecture (Sprint 70)

```
User query
  ↓
sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)
  ↓
384-dim vector (normalized)
  ↓
PostgreSQL: SELECT * FROM rag_chunks WHERE metadata_json LIKE '%embedding_v2%'
  ↓
For each chunk: load metadata_json["embedding_v2"], compute dot product
  ↓
Top-K by similarity
```

**Performance:**
- Encoding: ~30ms per query (CPU)
- Search: 2770 chunks × 1 query ≈ 50ms (cosine similarity loop)
- Total: ~80ms per RAG query

## Sprint 70 vs Sprint 57 (BM25)

| Метрика | BM25 (keyword) | Real embeddings (semantic) |
|---------|----------------|------------------------------|
| Recall@3 | 10% | 11% |
| Recall@5 | 10% | 11% |
| MRR | 0.100 | 0.093 |

**Real embeddings** semantic поиск (понимает смысл) vs BM25 keyword поиск (точные слова).
- Real embeddings +11% vs hash (0%)
- Real embeddings примерно равен BM25 (10-11%)
- **Оба НЕ 60-80%** — потому что benchmark methodology ограничивает upper bound

## Почему Recall не 60-80%?

**Benchmark limitation** (не сама RAG):
- Ground truth проверяет `expected_subject` keywords (e.g., "Математика") в `material_title`
- Многие chunks имеют общие titles ("Учебник 6 класс") без subject-specific keywords
- **Реальная польза** (semantic search) не измеряется — пользователь может спросить "как решать дроби" и получить semantic match даже если title не содержит "дроби"

**Следующий шаг** (Sprint 71): использовать `search_persistent` с real embeddings, добавить semantic search как primary, BM25 как fallback.

## 8GB RAM Upgrade (Sprint 70 unlock)

**До (4GB RAM):**
- sentence-transformers не могли быть установлены (200MB wheel + ~500MB модель)
- RAG: hash-based embeddings (Recall@3 = 0%)

**После (8GB RAM):**
- sentence-transformers 5.6.1 + torch 2.10.0 + model loaded
- Real embeddings (384-dim, multilingual)
- Sprint 70 memory: ~700MiB (модель в RAM)
- **6.3GB available** для других нужд

## Backfill results (Sprint 70)

```
2026-07-27 06:10:58,438 [INFO] Processed 0/2770 (0%)
2026-07-27 06:14:42,319 [INFO] Processed 2770/2770 (100%)
2026-07-27 06:14:42,319 [INFO] Backfill DONE: 2770 chunks in 249.7s
```

**Rate: 11.1 chunks/second** (CPU inference)
**Total time: ~4 минуты**

## Sprint 70 deliverables

1. **`apps/backend/app/rag_embeddings.py`** (3.5 KB) — sentence-transformers wrapper
   - Lazy-loaded thread-safe singleton
   - `encode_texts()`, `encode_single()`, `cosine_similarity()`, `is_available()`
2. **`apps/backend/scripts/backfill_embeddings.py`** (3.7 KB) — backfill runner
3. **`apps/backend/scripts/rag_benchmark_real_embeddings.py`** (7.1 KB) — benchmark
4. **`apps/backend/tests/test_sprint70_embeddings.py`** (4.3 KB) — 11 tests (6 fast + 5 slow)

## Production verify

- `is_available(): True` (sentence-transformers loaded)
- `EMBEDDING_DIM: 384`
- 2770/2770 chunks have real embeddings
- Recall@3 improved from 0% → 11%
- Health 200
- Memory: 876MiB / 8GB (10.7%)

## Sprint 71+ (follow-up)

- **Sprint 71**: Update `rag_persist.py` to use real embeddings from `metadata_json["embedding_v2"]` for `search_persistent()` (replace hash-based with cosine on real vectors)
- **Sprint 71**: Add `POST /api/v1/rag/search/real` endpoint
- **Sprint 71**: Hybrid search (BM25 + real embeddings weighted)
- **Sprint 72+**: P1 backlog

## Files modified/created (Sprint 70)

- `apps/backend/requirements.txt` — torch==2.10.0+cpu, torchvision==0.25.0+cpu, sentence-transformers==5.6.1
- `apps/backend/app/rag_embeddings.py` (NEW)
- `apps/backend/scripts/backfill_embeddings.py` (NEW)
- `apps/backend/scripts/rag_benchmark_real_embeddings.py` (NEW)
- `apps/backend/tests/test_sprint70_embeddings.py` (NEW)
- `docs/RAG-BENCHMARK-REAL-EMBEDDINGS.md` (this file)
