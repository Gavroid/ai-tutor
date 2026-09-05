# Algebra Production Import And Promotion — 2026-08-19

## Scope

This stage completed the Algebra source/RAG production data import and the backend readiness logic needed to show Algebra as `mvp_ready` only after route, source/RAG, and practice coverage are all complete.

It used a targeted data import and a targeted backend deploy. No broad production sync was performed, and `.mvp-rescue-commit` was not advanced because production git marker/tree hygiene remains dirty and misaligned.

## Pre-Import State

Production `/api/v1/subjects` before import:

```text
algebra: mvp_status=preview, route_ready=True, rag_ready=False, practice_ready=True,
         topic_count=19, route_topic_count=19, source_topic_count=0, practice_topic_count=19
math:    mvp_status=mvp_ready, source_topic_count=42/42
geom:    mvp_status=preview, source_topic_count=0/13
```

Production hygiene facts remained:

```text
marker=6e698a0
branch=master
head=cb99f2b
dirty_count=155
```

## Backup / Offsite

Fresh backup was taken immediately before production DB mutation:

```text
RUN_BACKUP_START=2026-08-19T12:36:46+00:00
DB backup: db-20260819T123646Z.sql.gz
Uploads backup: uploads-20260819T123646Z.tar.gz
Manifest: manifest-20260819T123646Z.md5
```

Offsite verification:

```text
OFFSITE: uploaded 123 files (all size-verified)
OFFSITE OK: hash verified manifest-20260819T123646Z.md5 (5b178e4077053917e77e240b822afbe5)
OFFSITE OK: 123 uploaded, 0 deleted, 208 total on SMB
```

## Production Data Import

The first DB connection attempt through a direct SSH tunnel to host port `5432` failed because PostgreSQL is not published on the host. The import was then executed safely via a generated SQL transaction and `docker exec -i deploy-db-1 psql`.

Pre-import DB counts:

```text
before_materials=0
before_chunks=0
```

Production SQL transaction result:

```text
BEGIN
DELETE 0
DELETE 0
38 INSERT statements
COMMIT
algebra_materials_after=19
algebra_chunks_after=19
algebra_source_topic_count_after=19
```

Production RAG metadata audit from DB read-back:

```json
{
  "summary": {
    "rows_checked": 19,
    "ok_rows": 19,
    "bad_rows": 0,
    "problems": {}
  },
  "bad_rows": []
}
```

Redis subjects cache was invalidated after import:

```text
subjects:v3:list:active=True
DEL result=1
```

## Backend Readiness Logic

### Changed

`apps/backend/app/subjects/router.py` now promotes any subject to `mvp_ready` when all three runtime coverage gates are true:

- `route_ready=true`
- `rag_ready=true`
- `practice_ready=true`

Math remains supported as before. Algebra no longer stays hardcoded in `preview` once its route/source/practice coverage is complete.

### TDD Evidence

RED:

```text
test_algebra_becomes_mvp_ready_when_route_source_and_practice_coverage_complete
AssertionError: assert 'preview' == 'mvp_ready'
```

GREEN:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_subjects.py::test_algebra_becomes_mvp_ready_when_route_source_and_practice_coverage_complete \
  apps/backend/tests/test_subjects.py::test_list_subjects_returns_seed -q
2 passed, 3 warnings
```

Regression:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_subjects.py \
  apps/backend/tests/test_algebra_production_import.py \
  apps/backend/tests/test_rag_metadata_audit.py -q
21 passed, 3 warnings
```

Compile:

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/app/subjects/router.py \
  apps/backend/tests/test_subjects.py
exit 0
```

## Targeted Backend Deploy

Only `apps/backend/app/subjects/router.py` was synced to production. Backend was rebuilt/recreated.

Observed during restart:

```text
initial ready_http=502 while backend restarted
final ready_http=200 body={"status":"ready"}
backend healthy
```

Post-deploy health:

```text
READY_HTTP=200
HEALTH_HTTP=200
backend/frontend/db/redis healthy
```

## Final Production State

Production `/api/v1/subjects` after import + deploy:

```text
algebra: mvp_status=mvp_ready, route_ready=True, rag_ready=True, practice_ready=True,
         topic_count=19, route_topic_count=19, source_topic_count=19, practice_topic_count=19
math:    mvp_status=mvp_ready, route_ready=True, rag_ready=True, practice_ready=True,
         source_topic_count=42, practice_topic_count=42
geom:    mvp_status=preview, route_ready=True, rag_ready=False, practice_ready=True,
         source_topic_count=0, practice_topic_count=13
```

Algebra route endpoint:

```text
GET /api/v1/subjects/4/route-plan
route_rows=19
first topic_id=34
```

Student smoke after promotion:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

## Remaining Work

- Geometry remains `preview`: route/practice are present, source/RAG is still `0/13`.
- Production git hygiene remains unresolved: marker `6e698a0`, branch `master`, head `cb99f2b`, dirty count `155`.
- `.mvp-rescue-commit` was intentionally not advanced because this was a targeted data + backend fix, not a full clean release alignment.

## Decision

Algebra is now production `mvp_ready` with route/source/practice coverage complete and smoke verified. The remaining multi-subject blocker is Geometry source/RAG.
