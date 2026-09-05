# Production Hygiene Reconcile Gate — 2026-08-19

## Scope

This gate audits whether the production tree can be safely aligned to local `mvp-rescue` HEAD and whether `.mvp-rescue-commit` can be advanced.

No production files were reset, deleted, overwritten, or broadly synced in this stage.

## Runtime Health

Production health during the audit:

```text
READY_HTTP=200
HEALTH_HTTP=200
backend/frontend/db/redis healthy
```

Math/Algebra/Geometry runtime readiness:

```text
math:    mvp_ready, route/source/practice 42/42
algebra: mvp_ready, route/source/practice 19/19
geom:    mvp_ready, route/source/practice 13/13
```

## Git/Marker Facts

Local repo:

```text
branch=mvp-rescue
head=6f30f17
```

Production repo:

```text
marker=6e698a0
branch=master
head=cb99f2b
dirty_count=155
```

## Hash Reconciliation

Production dirty tracked files were compared against local `mvp-rescue` content by SHA-256.

Result:

```json
{
  "dirty_files": 155,
  "matched_local_head": 134,
  "different_from_local_head": 10,
  "local_missing": 11
}
```

The 134 matching dirty files strongly suggest much of production's dirty tree already resembles newer local code. However, the remaining differences mean a blind `git reset`, marker advance, or broad sync would be unsafe.

## Different From Local HEAD

These tracked production files differ from local `mvp-rescue` content:

```text
apps/backend/tests/test_subjects.py
apps/backend/tests/test_teacher.py
docs/DEPLOY-GUIDE.md
apps/backend/scripts/math_fallback_seed.py
apps/backend/tests/test_ai_output_contract.py
apps/frontend/e2e/teacher-review-v2.spec.ts
docs/STAGE-6-RELIABILITY-OPS-MVP-REPORT.md
docs/STAGE-7-MULTI-SUBJECT-EXPANSION-MVP-REPORT.md
docs/pilot-topic-matrix.md
docs/pilot-walkthrough-notes.md
```

## Local Missing / Production-Only Paths

These production dirty paths do not map to local files or are directories/sensitive/generated paths:

```text
.mvp-rescue-commit
apps/backend/app/analytics/
apps/frontend/app/styles/
apps/frontend/app/teacher/topics/
apps/frontend/app/welcome/
apps/frontend/components/ui/
deploy/backup/_manual/
deploy/backup/_out/
deploy/grafana/provisioning/alerting/
deploy/ops/
deploy/ssl/certs/
```

Some are expected production-only or generated/sensitive paths. They must not be deleted during cleanup without explicit path-by-path review.

## Decision

Do **not** advance `.mvp-rescue-commit` and do **not** run broad production tree reset/sync yet.

Safe next steps:

1. Review the 10 differing files one by one and decide prod-vs-local winner.
2. Classify the 11 production-only paths as generated, sensitive, persistent, or missing-from-repo.
3. Only after a path-level reconciliation plan, perform a targeted cleanup/sync.
4. Re-run `/ready`, `/health`, subject readiness, and student smoke.
5. Advance marker only after the tree is clean/aligned and rollback path is explicit.

## Current Product Status

Despite git hygiene debt, the user-visible production product is healthy for the current math trio:

- Math: `mvp_ready`
- Algebra: `mvp_ready`
- Geometry: `mvp_ready`

Remaining product expansion work is now outside the Math/Algebra/Geometry trio: other subjects remain preview-only.
