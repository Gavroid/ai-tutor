# Geometry Production Import And Promotion — 2026-08-19

## Scope

This stage completed Geometry source/RAG production import using project-owned internal Geometry source notes.

It avoids unverified external textbook scans and avoids diagram extraction dependency. No broad production sync was performed. `.mvp-rescue-commit` was not advanced because production git marker/tree hygiene remains dirty and misaligned.

## Pre-Import State

Production `/api/v1/subjects` before Geometry import:

```text
math:    mvp_status=mvp_ready, route/source/practice complete
algebra: mvp_status=mvp_ready, route/source/practice complete
geom:    mvp_status=preview, route_ready=True, rag_ready=False, practice_ready=True,
         topic_count=13, route_topic_count=13, source_topic_count=0, practice_topic_count=13
```

## Source Choice

Geometry old blocker was diagram-heavy external source extraction. Instead of importing unverified PDFs or diagram-dependent chunks, this stage used the allowed fallback path documented in earlier Geometry audits: project-owned internally authored source notes.

The manifest uses:

```text
source=internal_geometry_notes
license=Project-owned internal notes
attribution=AI-Tutor project-authored Geometry notes, created for this pilot curriculum.
```

## Added

- `apps/backend/scripts/geometry_internal_source_manifest.py`
- `apps/backend/tests/test_geometry_internal_source_manifest.py`
- `apps/backend/scripts/geometry_production_import.py`
- `apps/backend/tests/test_geometry_production_import.py`

## TDD / Local Verification

RED:

```text
ModuleNotFoundError: No module named 'scripts.geometry_internal_source_manifest'
ModuleNotFoundError: No module named 'scripts.geometry_production_import'
```

GREEN:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_geometry_internal_source_manifest.py \
  apps/backend/tests/test_geometry_production_import.py -q
7 passed, 3 warnings
```

Broader targeted regression:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_geometry_internal_source_manifest.py \
  apps/backend/tests/test_geometry_production_import.py \
  apps/backend/tests/test_geometry_fallback_seed.py \
  apps/backend/tests/test_subjects.py \
  apps/backend/tests/test_rag_metadata_audit.py -q
26 passed, 3 warnings
```

Compile:

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/scripts/geometry_internal_source_manifest.py \
  apps/backend/scripts/geometry_production_import.py \
  apps/backend/tests/test_geometry_internal_source_manifest.py \
  apps/backend/tests/test_geometry_production_import.py
exit 0
```

SQLite staging-shaped rehearsal:

```text
geometry manifest: topic_count=13, source=internal_geometry_notes
staging import: material_count=13, chunk_count=13, rows_written=26
metadata_audit: rows_checked=13, ok_rows=13, bad_rows=0
sqlite counts: 13 materials, 13 chunks, 13 topics
```

## Backup / Offsite

Fresh backup was taken immediately before Geometry production DB mutation:

```text
RUN_BACKUP_START=2026-08-19T13:06:10+00:00
DB backup: db-20260819T130610Z.sql.gz
Uploads backup: uploads-20260819T130610Z.tar.gz
Manifest: manifest-20260819T130610Z.md5
```

Offsite verification:

```text
OFFSITE: uploaded 126 files (all size-verified)
OFFSITE OK: hash verified manifest-20260819T130610Z.md5 (89a9cfcad8a066c1372979547567662f)
OFFSITE OK: 126 uploaded, 0 deleted, 211 total on SMB
```

## Production Data Import

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
26 INSERT statements
COMMIT
geometry_materials_after=13
geometry_chunks_after=13
geometry_source_topic_count_after=13
```

Production RAG metadata audit from DB read-back:

```json
{
  "summary": {
    "rows_checked": 13,
    "ok_rows": 13,
    "bad_rows": 0,
    "problems": {}
  },
  "bad_rows": []
}
```

## Final Production State

Production `/api/v1/subjects` after Geometry import:

```text
math:    mvp_status=mvp_ready, route_ready=True, rag_ready=True, practice_ready=True,
         topic_count=42, route_topic_count=42, source_topic_count=42, practice_topic_count=42
algebra: mvp_status=mvp_ready, route_ready=True, rag_ready=True, practice_ready=True,
         topic_count=19, route_topic_count=19, source_topic_count=19, practice_topic_count=19
geom:    mvp_status=mvp_ready, route_ready=True, rag_ready=True, practice_ready=True,
         topic_count=13, route_topic_count=13, source_topic_count=13, practice_topic_count=13
```

Geometry route endpoint:

```text
GET /api/v1/subjects/5/route-plan
geom_route_rows=13
first topic_id=53
```

Student smoke after Geometry promotion:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health:

```text
READY_HTTP=200
HEALTH_HTTP=200
backend/frontend/db/redis healthy
```

## Remaining Work

- Production git hygiene remains unresolved:

```text
marker=6e698a0
branch=master
head=cb99f2b
dirty_count=155
```

- `.mvp-rescue-commit` was intentionally not advanced because this was a targeted data import on an already dirty/misaligned production tree.
- Other non-math subjects remain preview-only; this stage closes the Math/Algebra/Geometry readiness trio.

## Decision

Geometry is now production `mvp_ready` with route/source/practice coverage complete and smoke verified. Math, Algebra, and Geometry are all production `mvp_ready`.
