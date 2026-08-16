# Stage 26 — Cross-Role Pilot Dress Rehearsal — 2026-08-16

## Scope

Stage 26 goal: run a full cross-role rehearsal before handing the system to Igor for manual testing.

## Production Baseline

```text
production marker: 6e698a0
/ready HTTP=200
/health HTTP=200
backend/frontend/db/redis/prometheus healthy; grafana/proxy running
```

## Dress Rehearsal Coverage

The production rehearsal used the existing cross-role Playwright pilot suite:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts --project=chromium
4 passed (7.4s)
```

Covered flows:

1. Admin login → `/admin` → audit log/filter surface.
2. Parent login → `/parents` → linked children/privacy smoke.
3. Teacher login → `/teacher` → teacher materials/workspace smoke.
4. Student login → `/subjects` → subject/topic → secure v2 exercise no-leak smoke.

## Runtime Note

The first attempt used a foreground timeout of `900s`, which the runtime rejected because the maximum foreground timeout is `600s`. No production action was performed by that rejected command. The same test was rerun with `timeout=600` and passed.

## Admin Realtime / Monitoring Smoke

Admin realtime snapshot after the rehearsal:

```text
REALTIME_HTTP=200
http_total {'2xx': ..., '4xx': ..., '5xx': 0}
breakdown_len observed, with expected/auth-related 4xx details available in snapshot
/ready HTTP=200
```

The important rehearsal criterion is satisfied: no unexpected 5xx were reported after cross-role smoke, and readiness stayed healthy.

## Result

The cross-role pilot rehearsal passed. The system is ready for Igor’s manual testing on the Math MVP pilot scope.

## Remaining Boundaries

- Algebra and Geometry remain preview because verified source/RAG coverage is still `0` for both subjects.
- Production marker remains `6e698a0` because the plan used targeted deploys instead of full marker release workflow.
- Manual testers must use operator-provided credentials and must not put secrets in screenshots or notes.

## Next Stage

Proceed to Stage 27 — Final 3-Month Completion Report.
