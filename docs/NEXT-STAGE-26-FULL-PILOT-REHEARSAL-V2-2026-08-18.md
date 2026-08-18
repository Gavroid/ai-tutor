# Next Stage 26 — Full Pilot Rehearsal V2 — 2026-08-18

## Decision

Stage 26 is complete. The canonical cross-role pilot rehearsal passed after avoiding repeated real-auth login bursts that trigger production login rate limits.

System is ready for the next manual Math pilot wave, with Algebra and Geometry still preview-only.

## Scope

Rehearsal covered the four pilot roles:

- Admin: `/admin`, audit log, filters, health.
- Parent: `/parents`, linked children, privacy boundary route check.
- Teacher: `/teacher`, own materials surface.
- Student: `/subjects`, topic open, secure v2 exercise path.

Stage 23 and Stage 24 standalone privacy/RBAC suites remain the dedicated deeper boundary checks for parent/teacher/admin. Stage 26 uses the canonical `pilot.spec.ts` as the cross-role dress rehearsal to avoid turning production auth rate limits into false product failures.

## Initial Broad Batch Finding

An initial oversized Playwright batch tried to run many real-auth suites together and caused production login rate limiting:

```text
POST /api/v1/auth/login -> 429 Too Many Requests
UI alert: Слишком много попыток входа. Подождите 15 минут.
```

This was an operational test-harness issue, not a product 5xx. It confirmed the login rate limiter is active. After the rate-limit window cleared, the canonical cross-role rehearsal was re-run serially.

## Cross-Role Rehearsal Result

Command:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts --project=chromium --workers=1
```

Result:

```text
2026-08-18 12:42:41 MSK
Running 4 tests using 1 worker

✓ Pilot admin flow   — admin login → /admin → audit log → filter
✓ Pilot parent flow  — parent login → /parents → linked children list
✓ Pilot teacher flow — teacher login → /teacher → own materials list
✓ Pilot student flow — student login → /subjects → /topics/[id] → secure v2 exercise

4 passed (9.6s)
```

## Boundary Suites Already Established

The following deeper suites were already added and passed in adjacent stages:

```text
Stage 22 student output contract:
- backend safety slice: 83 passed
- LAN production student smoke: 2 passed

Stage 23 parent privacy:
- backend: 7 passed
- LAN production parent privacy smoke: 1 passed

Stage 24 teacher/admin RBAC:
- backend: 10 passed
- LAN production teacher/admin RBAC smoke: 3 passed
```

Stage 26 does not duplicate those long-running suites in one parallel auth burst because the production login limiter is intentionally active.

## Production Health After Rehearsal

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
backend healthy
frontend healthy
db healthy
redis healthy
prometheus healthy
grafana/proxy running
```

## 5xx Check After Run

Prometheus 10-minute 5xx checks after the rehearsal:

```json
{
  "http_5xx_10m": [],
  "http_5xx_by_path_10m": []
}
```

Observed 429s in the 20-minute window were from the earlier oversized auth batch:

```json
{
  "auth_429_20m": [
    { "value": "6.07593911233905" }
  ]
}
```

Interpretation: no product 5xx after rehearsal; auth rate-limit behavior is active and should be respected by future E2E orchestration.

## Production Impact

None.

- No runtime code changes.
- No deploy.
- No DB migration.
- No production data mutation.
- No backup/offsite required for Stage 26 because production was not mutated.
- No Nightscout or external medical system touched.

## Rehearsal Guidance Going Forward

Use one of these patterns:

1. Run `e2e/pilot.spec.ts --workers=1` as the canonical cross-role real-auth rehearsal.
2. Run deeper role suites separately with enough delay or mocked auth where the goal is UI/RBAC behavior rather than auth itself.
3. Do not run many real-auth suites in one parallel batch against production; the login limiter will correctly return `429`.

## Done Criteria

- Cross-role Playwright suite: complete (`4 passed`).
- `/ready HTTP=200` after run: complete.
- No 5xx after run: complete.
- Auth limiter behavior documented as test-harness caveat: complete.
- System ready for next manual pilot wave: complete.
- Commit: pending at report creation.
