# All Subjects Production Readiness — 2026-08-19

## Scope

This stage expanded production readiness from Math/Algebra/Geometry to all seeded 7th-grade subjects.

The implementation used project-owned internal source notes and simple checkable fallback practice for the remaining preview-only subjects. No external textbook scans or unverified source material were imported.

## Subjects Covered

Remaining subjects before this stage:

```text
rus, lit, phys, inf, hist, soc, geo, bio, eng
```

New manifest/import scope:

```text
151 remaining-subject topics
151 learning_materials rows
151 rag_chunks rows
151 fallback-practice topic entries
```

## Added / Changed

- `apps/backend/scripts/remaining_subjects_internal_source_manifest.py`
- `apps/backend/scripts/remaining_subjects_production_import.py`
- `apps/backend/tests/test_remaining_subjects_internal_source_manifest.py`
- `apps/backend/tests/test_remaining_subjects_production_import.py`
- `apps/backend/app/subjects/router.py`
  - generic route-plan support for every seeded subject
  - route readiness for every subject with seeded topics
- `apps/backend/tests/test_subjects.py`
  - all seeded subjects have route coverage
  - generic route-plan returns curriculum topics

## TDD Evidence

RED:

```text
ModuleNotFoundError: No module named 'scripts.remaining_subjects_internal_source_manifest'
ModuleNotFoundError: No module named 'scripts.remaining_subjects_production_import'
route_ready false for non-math subjects
route-plan returned [] for Russian subject
```

GREEN / regression:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_remaining_subjects_internal_source_manifest.py \
  apps/backend/tests/test_remaining_subjects_production_import.py \
  apps/backend/tests/test_subjects.py \
  apps/backend/tests/test_rag_metadata_audit.py -q
24 passed, 3 warnings
```

Compile:

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/scripts/remaining_subjects_internal_source_manifest.py \
  apps/backend/scripts/remaining_subjects_production_import.py \
  apps/backend/app/subjects/router.py \
  apps/backend/tests/test_remaining_subjects_internal_source_manifest.py \
  apps/backend/tests/test_remaining_subjects_production_import.py \
  apps/backend/tests/test_subjects.py
exit 0
```

## Staging-Shaped Rehearsal

SQLite rehearsal:

```text
manifest topic_count=151
staging import material_count=151
staging import chunk_count=151
rows_written=302
metadata_audit bad_rows=0
sqlite counts: 151 materials, 151 chunks, 151 topics
```

## Backup / Offsite

Fresh backup was taken immediately before production DB mutation:

```text
RUN_BACKUP_START=2026-08-19T16:45:55+00:00
DB backup: db-20260819T164555Z.sql.gz
Uploads backup: uploads-20260819T164555Z.tar.gz
Manifest: manifest-20260819T164555Z.md5
```

Offsite verification:

```text
OFFSITE: uploaded 123 files (all size-verified)
OFFSITE OK: hash verified manifest-20260819T164555Z.md5 (63463c40e604302b9b97980df752c8d5)
OFFSITE OK: 123 uploaded, 3 deleted, 211 total on SMB
```

## Production Import

The first import attempt used local sequential topic IDs and resulted in partial coverage for `inf` and `phys`. This was corrected by rebuilding the import SQL from actual production topic IDs.

Corrected production import result:

```text
remaining_materials_after=151
remaining_chunks_after=151
remaining_source_topic_count_after=151
fallback_topics_updated=151
```

Generic route fix was deployed by targeted backend rebuild/recreate. Initial `502` responses occurred during backend restart; final readiness was healthy.

## Final Production State

All 12 subjects are now production `mvp_ready`:

```text
algebra  19/19 route/source/practice
bio      19/19 route/source/practice
eng      16/16 route/source/practice
geo      16/16 route/source/practice
geom     13/13 route/source/practice
hist     10/10 route/source/practice
inf      21/21 route/source/practice
lit      17/17 route/source/practice
math     42/42 route/source/practice
phys     24/24 route/source/practice
rus      13/13 route/source/practice
soc      15/15 route/source/practice
```

Sample route endpoint:

```text
GET /api/v1/subjects/1/route-plan
rus_route_rows=13
first topic_id=1
```

Student smoke:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health:

```text
READY_HTTP=200
HEALTH_HTTP=200
```

## Remaining Work

- The source/practice for non-math subjects is safe project-owned MVP content, not full textbook-grade curriculum depth.
- Production git hygiene remains unresolved and marker was not advanced:

```text
marker=6e698a0
branch=master
head=cb99f2b
dirty_count=155+
```

- Old local untracked stakeholder decks and `tmp/` remain intentionally untouched.

## Decision

All seeded subjects are now production `mvp_ready` with route/source/practice coverage complete and student smoke verified.
