# Stage 22 — Manual Testing Harness — 2026-08-15

## Scope

Stage 22 goal: make human testing easy and reproducible.

## Completed

- Created `docs/MANUAL-TESTING-PLAN-2026-08-15.md`.
- Covered manual scenarios for:
  - student;
  - parent;
  - teacher;
  - admin;
  - recovery after errors;
  - mobile.
- Added blocker/high/medium/low severity definitions.
- Added expected results and screenshot checklist.
- Ensured the plan does not include passwords, tokens, `.env`, private keys, cookies, Bearer values, or SMB credentials.

## Production Baseline

```text
production marker: 6e698a0
/ready HTTP=200
/health HTTP=200
backend/frontend/db/redis/prometheus healthy; grafana/proxy running
```

## Dry-Run Automation

Selected production dry-runs:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/mvp-student-flow.spec.ts --grep "student can open topic" --project=chromium
1 passed (34.9s)

BASE_URL=https://192.168.1.86 npx playwright test e2e/parent-dashboard-v2.spec.ts --project=chromium
1 passed (806ms)

BASE_URL=https://192.168.1.86 npx playwright test e2e/teacher-review-v2.spec.ts --project=chromium
1 passed (838ms)

BASE_URL=https://192.168.1.86 npx playwright test e2e/mobile-audit.spec.ts --grep "mobile_iPhone_SE_login" --project=chromium
1 passed (1.5s)

/ready HTTP=200
/health HTTP=200
```

## Notes

- The manual testing plan intentionally references operator-provided accounts rather than writing passwords into the document.
- Parent privacy boundary is explicit: aggregate progress only, no raw AI chat exposure.
- Student safety boundary is explicit: no `correct_answer` exposure before answering.

## Next Stage

Proceed to Stage 23 — Reliability And Alerts Hardening.
