# Next Stage 01 — Release Hygiene And Marker Recovery Report — 2026-08-16

## Scope

Stage 01 goal: make production marker and release state trustworthy again without unsafe broad deploys.

## Evidence Collected

```text
local branch: mvp-rescue
local HEAD: 5f572c3
production branch: master
production HEAD: cb99f2b
production marker: 6e698a0
production /ready: HTTP 200
production /health: HTTP 200
production services: backend/frontend/db/redis/prometheus healthy; grafana/proxy running
production git dirty count: 85 modified, 69 untracked
```

## Finding

Production runtime is healthy, but production release state is not clean enough for a full marker advancement or broad `rsync --delete` deploy.

The production marker remains `6e698a0` because the previous plan intentionally used targeted deploys and narrow data/script syncs while production working tree was dirty and on `master`.

## Decision

Do **not** advance `.mvp-rescue-commit` and do **not** run broad deploy until production tree hygiene is resolved.

Safe path remains:

1. production backup + offsite verification;
2. targeted sync only for files required by a stage;
3. rebuild/restart only affected services;
4. `/ready`, `/health`, service health, endpoint/browser smoke;
5. stage report documents marker unchanged.

## Marker Advancement Requirements

Marker can be advanced only when all are true:

- production tree is clean or its dirty state is fully explained and snapshotted;
- production branch and intended deploy commit are aligned;
- backup/offsite verification completed immediately before deploy;
- deploy path is tested with no destructive `--delete` surprises;
- backend/frontend services are rebuilt from the intended source;
- `/ready HTTP=200`, `/health HTTP=200`, cross-role smoke pass;
- marker update is part of the controlled release, not a manual guess.

## Runbook Created

See `docs/NEXT-RELEASE-MARKER-ADVANCEMENT-RUNBOOK-2026-08-16.md`.

## Verification

```text
production marker: 6e698a0
/ready HTTP=200
/health HTTP=200
backend/frontend/db/redis/prometheus healthy
```

## Done When

A future operator can understand exactly why marker remains unchanged and what must happen before it can be advanced.
