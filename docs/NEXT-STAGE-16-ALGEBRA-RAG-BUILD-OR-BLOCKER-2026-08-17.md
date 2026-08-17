# Next Stage 16 — Algebra RAG Build Or Blocker Closure — 2026-08-17

## Decision

Algebra RAG remains **blocked**. Do not mark Algebra as `rag_ready` or `mvp_ready`.

Reason: Algebra has route and practice coverage, but production has no Algebra learning materials and no Algebra RAG chunks. Stage 13 created a local dry-run manifest only; it deliberately did not import sources, write DB rows, or create RAG chunks.

## Production Evidence

Read-only production DB query:

```text
algebra|19|0|0
math|42|42|20289
```

Per-topic Algebra production counts:

```text
34|Числовые выражения|0|0
35|Буквенные выражения (переменная)|0|0
36|Преобразование буквенных выражений|0|0
37|Линейное уравнение с одной переменной|0|0
38|Понятие функции|0|0
39|Линейная функция y = kx + b|0|0
40|Прямая пропорциональность|0|0
41|Определение степени|0|0
42|Свойства степени|0|0
43|Одночлены|0|0
44|Понятие многочлена|0|0
45|Сложение и вычитание многочленов|0|0
46|Умножение одночлена на многочлен|0|0
47|Умножение многочлена на многочлен|0|0
48|Формулы сокращённого умножения|0|0
49|Линейное уравнение с двумя переменными|0|0
50|Графический способ решения|0|0
51|Способ подстановки|0|0
52|Способ сложения|0|0
```

Production `/api/v1/subjects` shows Algebra remains preview:

```json
{
  "code": "algebra",
  "mvp_status": "preview",
  "route_ready": true,
  "rag_ready": false,
  "practice_ready": true,
  "topic_count": 19,
  "route_topic_count": 19,
  "source_topic_count": 0,
  "practice_topic_count": 19
}
```

Production route-plan smoke:

```text
GET /api/v1/subjects/4/route-plan
HTTP=200
19 route rows returned
```

Production health:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Local Dry-Run Evidence

Stage 13 manifest can map all route topics but does not import:

```json
{
  "topic_count": 19,
  "source_counts": {
    "wallace_algebra": 12,
    "im_first_edition": 7
  },
  "db_import": false,
  "rag_chunk_creation": false,
  "production_mutation": false
}
```

This is useful input for a future importer, not source/RAG readiness.

## Metadata Contract

Stage 15 RAG metadata audit is ready and must be run after any future Algebra RAG build. Since there are currently `0` Algebra chunks, there is nothing meaningful to audit in production for Algebra yet. The blocker is upstream: no imported Algebra source materials.

## Tests

```text
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest \
  tests/test_rag_metadata_audit.py \
  tests/test_algebra_source_import_dry_run.py \
  tests/test_algebra_fallback_seed.py \
  tests/test_subjects.py::test_list_subjects_returns_seed \
  tests/test_math_route_plan.py::test_algebra_route_plan_endpoint_returns_preview_route -q
15 passed, 3 warnings
```

## Production Impact

None.

- No source import.
- No DB/RAG writes.
- No production deploy.
- No production data mutation.
- No backup/offsite required because no mutation occurred.
- No Nightscout or external medical system touched.

## Required Next Steps Before Algebra RAG Can Build

1. Fetch exact approved source pages/sections locally.
2. Validate extraction for a small subset first.
3. Create actual local `learning_materials` + `rag_chunks` fixture/import path.
4. Run `scripts.rag_metadata_audit --subject-code algebra` and require `bad_rows=0`.
5. Only then consider a targeted production import with backup/offsite.

## Done Criteria

- Algebra RAG chunk counts by topic: complete (`0/19`, blocked).
- Teacher/subject readiness evidence: complete (`source_topic_count=0`, `rag_ready=false`).
- Metadata quality contract considered: complete (blocked by zero chunks).
- Production backup before mutation: not applicable; no mutation occurred.
- Algebra RAG status honestly blocked: complete.
- Commit: pending at report creation.
