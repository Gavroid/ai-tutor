# Next Stage 18 — Multi-Subject Promotion Decision Gate — 2026-08-17

## Decision

**Do not promote Algebra or Geometry beyond `preview`.**

Only Math remains `mvp_ready`. Algebra and Geometry both have route and deterministic practice coverage, but both have `source_topic_count=0` and `rag_ready=false`. Promotion would create false readiness.

## Promotion Criteria

A subject may move beyond `preview` only when all criteria pass:

1. Route coverage is complete.
2. Source/RAG coverage is complete and topic-scoped.
3. Practice coverage is complete.
4. RAG metadata audit returns `bad_rows=0`.
5. Teacher readiness counts match subject coverage.
6. Student smoke is run if promotion changes student-facing behavior.

## Production `/api/v1/subjects` Readiness Evidence

Read-only production API snapshot:

```json
[
  {
    "code": "math",
    "mvp_status": "mvp_ready",
    "route_ready": true,
    "rag_ready": true,
    "practice_ready": true,
    "topic_count": 42,
    "route_topic_count": 42,
    "source_topic_count": 42,
    "practice_topic_count": 42
  },
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
  },
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
]
```

## Production DB Source/RAG Evidence

Read-only production DB query:

```text
algebra|19|0|0
geom|13|0|0
math|42|42|20289
```

Interpretation:

| Subject | Topics | Materials | RAG Chunks | Decision |
|---|---:|---:|---:|---|
| Math | 42 | 42 | 20,289 | Keep `mvp_ready`. |
| Algebra | 19 | 0 | 0 | Keep `preview`; RAG blocked. |
| Geometry | 13 | 0 | 0 | Keep `preview`; RAG blocked and diagram extraction unresolved. |

## Route Evidence

- Algebra route-plan: `GET /api/v1/subjects/4/route-plan` returned `HTTP=200` with `19` route rows.
- Geometry route-plan: `GET /api/v1/subjects/5/route-plan` returned `HTTP=200` with `13` route rows.

Routes are not the blocker; source/RAG is.

## Production Health

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Tests

```text
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest \
  tests/test_subjects.py::test_list_subjects_returns_seed \
  tests/test_math_route_plan.py::test_algebra_route_plan_endpoint_returns_preview_route \
  tests/test_math_route_plan.py::test_geometry_route_plan_endpoint_returns_preview_route \
  tests/test_rag_metadata_audit.py -q
9 passed, 3 warnings
```

## Student Smoke Decision

No student smoke was run for Algebra or Geometry because no promotion occurred. Running student smoke for promoted flows would be required only if a subject moved beyond preview or changed student-facing availability.

## Promotion Outcome

| Subject | Promotion Outcome | Reason |
|---|---|---|
| Math | Keep `mvp_ready` | Route, source/RAG, and practice coverage are complete. |
| Algebra | Keep `preview` | Route and practice are ready, but source/RAG coverage is `0/19`. |
| Geometry | Keep `preview` | Route and practice are ready, but source/RAG coverage is `0/13`; diagram extraction remains unresolved. |

## Production Impact

None.

- No code changes.
- No production deploy.
- No production data mutation.
- No backup/offsite required because no mutation occurred.
- No Nightscout or external medical system touched.

## Done Criteria

- `/api/v1/subjects` readiness fields checked: complete.
- Teacher/source readiness counts compared via DB/API evidence: complete.
- Student smoke decision documented: complete.
- Promotion/no-promotion decision explicit: complete.
- Algebra/Geometry remain preview: complete.
- Commit: pending at report creation.
