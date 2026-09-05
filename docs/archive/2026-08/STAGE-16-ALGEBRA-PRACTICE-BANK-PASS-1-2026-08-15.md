# Stage 16 — Algebra Practice Bank Pass 1 — 2026-08-15

## Scope

Stage 16 goal: create deterministic, checkable Algebra fallback practice tasks. The plan required P0/pilot topics first; this stage completed the full Algebra preview route (`19/19`) to reduce future gaps.

## Completed

- Added `apps/backend/scripts/algebra_fallback_seed.py`.
- Added `apps/backend/tests/test_algebra_fallback_seed.py`.
- Created one hand-authored first fallback task for every Algebra route topic `34–52`.
- Each task is:
  - `single` choice;
  - checkable;
  - has at least four options;
  - includes `correct_answer` in `options`;
  - includes explanation;
  - includes typical mistakes;
  - avoids raw model output, raw JSON, markdown tables, or unsafe free-text checking.

## Coverage

| Subject | Topics | Deterministic fallback first variants |
|---|---:|---:|
| Algebra | 19 | 19 |

## Local Verification

TDD evidence: the first test failed before implementation because the seed module did not exist:

```text
ModuleNotFoundError: No module named 'scripts.algebra_fallback_seed'
```

After implementation:

```text
cd apps/backend
.venv/bin/pytest tests/test_algebra_fallback_seed.py tests/test_health.py -q
11 passed, 3 warnings in 1.03s
```

## Production Backup / Offsite

Required backup was run before production registry mutation:

```text
backup manifest: /opt/ai-tutor/deploy/backup/_out/manifest-20260814T214053Z.md5
OFFSITE OK: hash verified manifest-20260814T214053Z.md5
SMB total after upload: 211 files
```

## Production Application

Safe narrow registry mutation was used:

```text
docker compose cp /opt/ai-tutor/apps/backend/scripts/algebra_fallback_seed.py backend:/app/scripts/algebra_fallback_seed.py
docker compose exec -T backend python -m scripts.algebra_fallback_seed
```

Seed result:

```text
updated: 19 topic IDs
missing: []
```

## Production Smoke

Registry verification:

```text
{'topics': 19, 'fallback_topics': 19, 'failures': []}
/ready HTTP=200
```

## Readiness Honesty

Algebra remains preview. This stage prepares deterministic practice, but Algebra still lacks verified source/RAG coverage (`0/19` after Stage 14 cleanup).

## Next Stage

Proceed to Stage 17 — Geometry Practice Bank Pass 1.
