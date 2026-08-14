# Stage 07 — Parent Report V2 For Math Pilot — 2026-08-14

## Scope

Stage 07 goal: make parent output actionable and non-technical while preserving the privacy boundary.

## Completed

- Improved parent dashboard `/parent/dashboard/[studentId]` with four parent-readable report cards:
  - `Что улучшилось`;
  - `Где нужна помощь`;
  - `Что сделать завтра`;
  - `Маршрут`.
- Kept the existing parent-friendly backend contract:
  - `summary`;
  - `recommendations`;
  - `last_activity_label`;
  - `privacy_note`.
- Added a dedicated Playwright spec for parent report V2 using mocked dashboard API data so it verifies UI/privacy without hammering production login.
- Improved login UX for HTTP 429 rate-limit: parent/user now sees the backend message instead of generic “connection” wording.

## Files Changed

- `apps/frontend/app/parent/dashboard/[studentId]/page.tsx`
- `apps/frontend/app/login/page.tsx`
- `apps/frontend/e2e/parent-dashboard-v2.spec.ts`

## Privacy Boundary

Verified UI copy says parents see aggregate metrics only. The V2 test asserts the page does not expose raw chat-style strings or `correct_answer`.

## Local Verification

```text
cd apps/frontend
npm run typecheck
exit 0

npm run build
Compiled successfully
```

Backend parent-related tests:

```text
cd apps/backend
.venv/bin/pytest tests/test_parents_materials.py tests/test_health.py -q
18 passed, 24 warnings in 12.41s
```

## Production Backup / Offsite

Required backup was run before production frontend deploy:

```text
backup manifest: /opt/ai-tutor/deploy/backup/_out/manifest-20260814T160137Z.md5
OFFSITE OK: hash verified manifest-20260814T160137Z.md5
SMB total after upload: 190 files
```

## Production Deploy

Frontend was rebuilt and restarted through Docker Compose:

```text
cd /opt/ai-tutor/deploy
docker compose build frontend
docker compose up -d --no-deps frontend
```

Build result:

```text
Next.js 16.2.10
Compiled successfully
Finished TypeScript
Generated static pages 21/21
frontend_health=healthy
```

## Production Smoke

Parent dashboard V2 smoke:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/parent-dashboard-v2.spec.ts --project=chromium
1 passed (822ms)
```

Mobile parents smoke:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/mobile-audit.spec.ts --grep "parents" --project=chromium
3 passed (5.0s)
```

Production health after deploy:

```text
/ready HTTP=200
backend/db/frontend/prometheus/redis running healthy; grafana/proxy running
```

## Notes

- Existing parent E2E that performs real login hit expected auth rate-limit `429` after repeated test logins. The product UX now shows the real 429 detail. The V2 dashboard smoke uses mocked API to avoid creating more login attempts.
- Production marker was not advanced because this was a targeted frontend rebuild rather than the full release marker workflow.

## Remaining Non-Blockers

- Parent dashboard export HTML still uses the older printed layout. It is functional but can be visually aligned with the new V2 cards later.
