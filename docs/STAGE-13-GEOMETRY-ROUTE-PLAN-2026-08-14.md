# Stage 13 — Geometry Route Plan Report — 2026-08-14

## Scope

Stage 13 goal: create a structured Geometry route-plan equivalent while keeping Geometry in honest preview status.

## Completed

- Added `apps/backend/app/geometry_plan.py`.
- Defined `GEOMETRY_SUBJECT_ID = 5`.
- Added `GEOMETRY_TOPIC_PLAN` covering all 13 production Geometry topics:
  - route order;
  - section;
  - tier (`base`, `medium`, `hard`);
  - focus;
  - checkpoint flag.
- Added `next_geometry_topic_after(...)`.
- Updated `/api/v1/subjects/{subject_id}/route-plan`:
  - Math `3` returns the 42-topic MVP-ready route;
  - Algebra `4` returns the 19-topic preview route;
  - Geometry `5` now returns a 13-topic preview route.
- Added route-plan tests for Geometry preview route.

## Files Changed

- `apps/backend/app/geometry_plan.py`
- `apps/backend/app/subjects/router.py`
- `apps/backend/tests/test_math_route_plan.py`

## TDD Evidence

The new Geometry route test failed before implementation:

```text
ModuleNotFoundError: No module named 'app.geometry_plan'
```

After implementation:

```text
cd apps/backend
.venv/bin/pytest tests/test_math_route_plan.py tests/test_math_plan.py tests/test_health.py -q
14 passed, 3 warnings in 1.25s
```

Final targeted verification:

```text
.venv/bin/pytest tests/test_math_route_plan.py tests/test_health.py -q
11 passed, 3 warnings in 1.20s
```

## Production Backup / Offsite

Required backup was run before production backend deploy:

```text
backup manifest: /opt/ai-tutor/deploy/backup/_out/manifest-20260814T194154Z.md5
OFFSITE OK: hash verified manifest-20260814T194154Z.md5
SMB total after upload: 205 files
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

/api/v1/subjects/5/route-plan => 13 rows
first row: topic_id=53, order=1, tier=base, next_topic_id=54
last row: topic_id=65, order=13, tier=hard, checkpoint=true, next_topic_id=null
```

Production health after deploy:

```text
/ready HTTP=200
backend healthy
```

## Readiness Honesty

Geometry remains preview. Stage 13 only adds route structure; it does not claim source/RAG or practice readiness.

Current known gaps from Stage 11:

- Geometry verified source/RAG coverage: `0/13` topics.
- Geometry deterministic fallback coverage: `0/13` topics.
- Geometry follow-up coverage: `0/13` topics.

## Next Stage

Proceed to Stage 14 — Algebra Source And RAG Readiness Pass.
