# Stage 17 — Geometry Practice Bank Pass 1 — 2026-08-15

## Scope

Stage 17 goal: create deterministic, checkable Geometry fallback practice tasks. The stage completed the full Geometry preview route (`13/13`).

## Completed

- Added `apps/backend/scripts/geometry_fallback_seed.py`.
- Added `apps/backend/tests/test_geometry_fallback_seed.py`.
- Created one hand-authored first fallback task for every Geometry route topic `53–65`.
- Each task is:
  - `single` choice;
  - checkable without drawings or free-form construction;
  - has at least four options;
  - includes `correct_answer` in `options`;
  - includes explanation;
  - includes typical mistakes;
  - avoids raw model output, raw JSON, markdown tables, broken math markers, and visual-only instructions.

## Coverage

| Subject | Topics | Deterministic fallback first variants |
|---|---:|---:|
| Geometry | 13 | 13 |

## Local Verification

TDD evidence: the first test failed before implementation because the seed module did not exist:

```text
ModuleNotFoundError: No module named 'scripts.geometry_fallback_seed'
```

After implementation:

```text
cd apps/backend
.venv/bin/pytest tests/test_geometry_fallback_seed.py tests/test_health.py -q
11 passed, 3 warnings in 1.02s
```

## Production Backup / Offsite

Required backup was run before production registry mutation:

```text
backup manifest: /opt/ai-tutor/deploy/backup/_out/manifest-20260814T215652Z.md5
OFFSITE OK: hash verified manifest-20260814T215652Z.md5
SMB total after upload: 214 files
```

## Production Application

Safe narrow registry mutation was used:

```text
docker compose cp /opt/ai-tutor/apps/backend/scripts/geometry_fallback_seed.py backend:/app/scripts/geometry_fallback_seed.py
docker compose exec -T backend python -m scripts.geometry_fallback_seed
```

Seed result:

```text
updated: 13 topic IDs
missing: []
```

## Production Smoke

Registry verification:

```text
{'topics': 13, 'fallback_topics': 13, 'failures': []}
/ready HTTP=200
```

## Readiness Honesty

Geometry remains preview. This stage prepares deterministic practice, but Geometry still lacks verified source/RAG coverage (`0/13` from Stage 15).

## Next Stage

Proceed to Stage 18 — Multi-Subject Readiness UI / Honest Preview State.
