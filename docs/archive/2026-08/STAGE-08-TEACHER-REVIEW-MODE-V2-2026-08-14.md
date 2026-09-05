# Stage 08 — Teacher Review Mode V2 Report — 2026-08-14

## Scope

Stage 08 goal: make teacher/admin topic review faster and clearer for the math pilot.

## Completed

- Extended `GET /api/v1/teacher/topics/readiness` with route metadata:
  - `route_order`;
  - `route_tier`;
  - `route_focus`;
  - `route_checkpoint`.
- Added backend filters:
  - `route_tier=base|medium|hard`;
  - `checkpoint=true|false`;
  - `manual_qa_status=...`.
- Updated `/teacher/topics` UI:
  - route tier filter;
  - manual status filter;
  - checkpoints-only filter;
  - route order/tier/checkpoint columns in desktop table;
  - route metadata in mobile cards.
- Added `teacher-review-v2.spec.ts` to verify route metadata/filter UI without raw JSON exposure.

## Files Changed

- `apps/backend/app/teacher/router.py`
- `apps/backend/app/teacher/schemas.py`
- `apps/backend/tests/test_teacher.py`
- `apps/frontend/app/teacher/topics/page.tsx`
- `apps/frontend/lib/api.ts`
- `apps/frontend/types/index.ts`
- `apps/frontend/e2e/teacher-review-v2.spec.ts`

## Local Verification

Backend teacher tests:

```text
cd apps/backend
.venv/bin/pytest tests/test_teacher.py tests/test_health.py -q
45 passed, 66 warnings in 55.54s
```

Frontend gates:

```text
cd apps/frontend
npm run typecheck
exit 0

npm run build
Compiled successfully
```

## Production Backup / Offsite

Required backup was run before backend/frontend production deploy:

```text
backup manifest: /opt/ai-tutor/deploy/backup/_out/manifest-20260814T161507Z.md5
OFFSITE OK: hash verified manifest-20260814T161507Z.md5
SMB total after upload: 193 files
```

## Production Deploy

Targeted backend + frontend rebuild/restart:

```text
cd /opt/ai-tutor/deploy
docker compose build backend frontend
docker compose up -d --no-deps backend frontend
```

Deploy health:

```text
deploy-backend-1 health=healthy
deploy-frontend-1 health=healthy
/ready HTTP=200
```

## Production Smoke

Teacher review V2 smoke:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/teacher-review-v2.spec.ts --project=chromium
1 passed (943ms)
```

Final quick gates after smoke:

```text
npm run typecheck
exit 0

.venv/bin/pytest tests/test_health.py -q
8 passed, 3 warnings in 1.04s
```

## Notes

- The first smoke attempts failed only due to duplicate visible/hidden text from desktop+mobile responsive DOM. The product UI was working; selectors were narrowed to desktop table links.
- Production marker was not advanced because this was a targeted rebuild rather than the full release marker workflow.

## Remaining Non-Blockers

- Quick status updates are still on topic detail pages; inline row actions can be added later if teacher feedback shows the extra click is too slow.
