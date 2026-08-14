# Stage 12 — Algebra Route Plan Report — 2026-08-14

## Scope

Stage 12 goal: create a structured Algebra route-plan equivalent while keeping Algebra in honest preview status.

## Completed

- Added `apps/backend/app/algebra_plan.py`.
- Defined `ALGEBRA_SUBJECT_ID = 4`.
- Added `ALGEBRA_TOPIC_PLAN` covering all 19 production Algebra topics:
  - route order;
  - section;
  - tier (`base`, `medium`, `hard`);
  - focus;
  - checkpoint flag.
- Added `next_algebra_topic_after(...)`.
- Updated `/api/v1/subjects/{subject_id}/route-plan`:
  - Math `3` still returns the 42-topic MVP-ready math route;
  - Algebra `4` now returns a 19-topic preview route;
  - Geometry `5` remains `[]` until Stage 13.
- Added route-plan tests for Algebra preview route and Geometry remaining empty.

## Files Changed

- `apps/backend/app/algebra_plan.py`
- `apps/backend/app/subjects/router.py`
- `apps/backend/tests/test_math_route_plan.py`

## TDD Evidence

The new Algebra route test failed before implementation:

```text
ModuleNotFoundError: No module named 'app.algebra_plan'
```

After implementation:

```text
cd apps/backend
.venv/bin/pytest tests/test_math_route_plan.py tests/test_math_plan.py tests/test_health.py -q
14 passed, 3 warnings in 1.22s
```

Final targeted verification:

```text
.venv/bin/pytest tests/test_math_route_plan.py tests/test_health.py -q
11 passed, 3 warnings in 1.27s
```

## Production Backup / Offsite

Required backup was run before production backend deploy:

```text
backup manifest: /opt/ai-tutor/deploy/backup/_out/manifest-20260814T184623Z.md5
OFFSITE OK: hash verified manifest-20260814T184623Z.md5
SMB total after upload: 202 files
```

## Production Deploy

Backend targeted rebuild/restart:

```text
cd /opt/ai-tutor/deploy
docker compose build backend
docker compose up -d --no-deps backend
backend_health=healthy
/ready HTTP=200
```

## Production Smoke

Route-plan smoke:

```text
/api/v1/subjects/4/route-plan => 19 rows
first row: topic_id=34, order=1, tier=base, next_topic_id=35
last row: topic_id=52, order=19, tier=hard, checkpoint=true, next_topic_id=null

/api/v1/subjects/5/route-plan => 0 rows
```

Production health after deploy:

```text
/ready HTTP=200
backend healthy
```

## Readiness Honesty

Algebra remains preview. Stage 12 only adds route structure; it does not claim source/RAG or practice readiness.

Current known gaps from Stage 11:

- Algebra verified source/RAG coverage: only `1/19` topics have any material/chunk.
- Algebra deterministic fallback coverage: `0/19` topics.
- Algebra follow-up coverage: partial only.

## Next Stage

Proceed to Stage 13 — Geometry Route Plan, same preview-only pattern.
