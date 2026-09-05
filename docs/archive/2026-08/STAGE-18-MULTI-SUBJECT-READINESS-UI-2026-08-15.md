# Stage 18 — Multi-Subject Readiness UI / Honest Preview State — 2026-08-15

## Scope

Stage 18 goal: make multi-subject readiness explicit and honest across API and UI.

## Completed

- Extended `SubjectOut` with readiness coverage fields:
  - `route_ready`;
  - `topic_count`;
  - `route_topic_count`;
  - `source_topic_count`;
  - `practice_topic_count`.
- Versioned `/api/v1/subjects` cache keys from `subjects:v2:*` to `subjects:v3:*` so production does not serve stale response shapes.
- Updated subject gallery UI to show readiness lines on every card:
  - `Маршрут`;
  - `Источники`;
  - `Практика`.
- Preserved honest subject states:
  - Math = `mvp_ready`;
  - Algebra = `preview`, route/practice partial-ready, sources not ready;
  - Geometry = `preview`, route/practice partial-ready, sources not ready.

## Files Changed

- `apps/backend/app/subjects/router.py`
- `apps/backend/app/subjects/schemas.py`
- `apps/backend/tests/test_subjects.py`
- `apps/frontend/app/subjects/page.tsx`
- `apps/frontend/types/index.ts`

## TDD Evidence

The first Stage 18 backend test failed before implementation because `/subjects` did not expose `route_ready`:

```text
KeyError: 'route_ready'
```

After implementation and test adjustment for local registry-free unit DB:

```text
cd apps/backend
.venv/bin/pytest tests/test_subjects.py tests/test_math_route_plan.py tests/test_health.py -q
20 passed, 3 warnings in 2.08s
```

Frontend gates:

```text
cd apps/frontend
npm run typecheck
npm run build
Compiled successfully
```

## Production Backup / Offsite

Required backup was run before production backend/frontend deploy:

```text
backup manifest: /opt/ai-tutor/deploy/backup/_out/manifest-20260814T220831Z.md5
OFFSITE OK: hash verified manifest-20260814T220831Z.md5
SMB total after upload: 217 files
```

## Production Deploy

Targeted Docker Compose rebuild/restart:

```text
docker compose build backend frontend
docker compose up -d --no-deps backend frontend
backend_health=healthy
frontend_health=healthy
/ready HTTP=200
```

## Production API Smoke

`/api/v1/subjects` now returns explicit readiness coverage:

```text
math:    mvp_ready, route=42/42, sources=42/42, practice=42/42
algebra: preview,   route=19/19, sources=0/19,  practice=19/19
geom:    preview,   route=13/13, sources=0/13,  practice=13/13
```

Raw smoke subset:

```text
{"id": 4, "code": "algebra", "mvp_status": "preview", "route_ready": true, "rag_ready": false, "practice_ready": true, "topic_count": 19, "route_topic_count": 19, "source_topic_count": 0, "practice_topic_count": 19}
{"id": 5, "code": "geom", "mvp_status": "preview", "route_ready": true, "rag_ready": false, "practice_ready": true, "topic_count": 13, "route_topic_count": 13, "source_topic_count": 0, "practice_topic_count": 13}
{"id": 3, "code": "math", "mvp_status": "mvp_ready", "route_ready": true, "rag_ready": true, "practice_ready": true, "topic_count": 42, "route_topic_count": 42, "source_topic_count": 42, "practice_topic_count": 42}
```

## Production E2E Smoke

Student flow still passes after subject UI change:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/mvp-student-flow.spec.ts --grep "student can open topic" --project=chromium
1 passed (22.5s)
```

## Readiness Honesty

This stage intentionally does not mark Algebra/Geometry as ready. Their practice banks exist, but verified source/RAG coverage is `0` for both after Stages 14–15.

## Next Stage

Proceed to Stage 19 — Adaptive Progression Multi-Subject Guardrails / Recommendation Honesty.
