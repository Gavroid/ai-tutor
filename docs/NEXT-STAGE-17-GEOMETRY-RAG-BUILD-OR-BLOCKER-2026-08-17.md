# Next Stage 17 — Geometry RAG Build Or Blocker Closure — 2026-08-17

## Decision

Geometry RAG remains **blocked**. Do not mark Geometry as `rag_ready` or `mvp_ready`.

Reason: Geometry has route and practice coverage, but production has no Geometry learning materials and no Geometry RAG chunks. Stage 14 created a local dry-run manifest only; it deliberately did not import sources, write DB rows, create RAG chunks, or validate diagram extraction.

## Production Evidence

Read-only production DB query:

```text
algebra|19|0|0
geom|13|0|0
math|42|42|20289
```

Per-topic Geometry production counts:

```text
53|Прямая, отрезок, луч, угол|0|0
54|Измерение отрезков и углов|0|0
55|Смежные и вертикальные углы|0|0
56|Перпендикулярные прямые|0|0
57|Признаки равенства треугольников|0|0
58|Медиана, биссектриса, высота|0|0
59|Равнобедренный треугольник|0|0
60|Окружность. Задачи на построение|0|0
61|Признаки параллельности прямых|0|0
62|Свойства параллельных прямых|0|0
63|Сумма углов треугольника|0|0
64|Внешний угол треугольника|0|0
65|Неравенство треугольника|0|0
```

Production `/api/v1/subjects` shows Geometry remains preview:

```json
{
  "code": "geom",
  "mvp_status": "preview",
  "route_ready": true,
  "rag_ready": false,
  "practice_ready": true,
  "topic_count": 13,
  "route_topic_count": 13,
  "source_topic_count": 0,
  "practice_topic_count": 13
}
```

Production route-plan smoke:

```text
GET /api/v1/subjects/5/route-plan
HTTP=200
13 route rows returned
```

Production health:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Local Dry-Run Evidence

Stage 14 manifest can map all route topics but does not import:

```json
{
  "topic_count": 13,
  "source_counts": {
    "im_geometry": 9,
    "euclid_redux": 4
  },
  "requires_diagram_review": true,
  "db_import": false,
  "rag_chunk_creation": false,
  "production_mutation": false
}
```

This is useful input for a future importer, not source/RAG readiness.

## Diagram Caveat

Geometry is more fragile than Algebra because source quality depends on diagrams and geometric notation. Every Stage 14 manifest row has `diagram_review_required=true`. Text-only extraction is not sufficient to count Geometry as source/RAG-ready.

## Metadata Contract

Stage 15 RAG metadata audit is ready and must be run after any future Geometry RAG build. Since there are currently `0` Geometry chunks, there is nothing meaningful to audit in production for Geometry yet. The blocker is upstream: no imported Geometry source materials and no diagram extraction validation.

## Tests

```text
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest \
  tests/test_rag_metadata_audit.py \
  tests/test_geometry_source_import_dry_run.py \
  tests/test_geometry_fallback_seed.py \
  tests/test_subjects.py::test_list_subjects_returns_seed \
  tests/test_math_route_plan.py::test_geometry_route_plan_endpoint_returns_preview_route -q
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

## Required Next Steps Before Geometry RAG Can Build

1. Fetch exact approved IM Geometry lesson pages locally.
2. Validate text extraction and diagram/image extraction separately.
3. Decide whether diagram-heavy content is imported, manually summarized, or deferred.
4. Verify page/section anchors and attribution for images as well as text.
5. Use Euclid Redux only after page-level license/share-alike/readability review.
6. Run `scripts.rag_metadata_audit --subject-code geometry` and require `bad_rows=0` after any chunk build.
7. Only then consider a targeted production import with backup/offsite.

## Done Criteria

- Geometry RAG chunk counts by topic: complete (`0/13`, blocked).
- Teacher/subject readiness evidence: complete (`source_topic_count=0`, `rag_ready=false`).
- Metadata quality contract considered: complete (blocked by zero chunks).
- Diagram/source caveats documented: complete.
- Production backup before mutation: not applicable; no mutation occurred.
- Geometry RAG status honestly blocked: complete.
- Commit: pending at report creation.
