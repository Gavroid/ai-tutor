# Stage 09 — Adaptive Progression Pass 1 Report — 2026-08-14

## Scope

Stage 09 goal: use student data to guide next topic selection for the math pilot route.

## Completed

- Updated `/api/v1/progress/recommend-next` to accept `subject_id`.
- Added math-route-aware behavior for `subject_id=3`:
  - no attempts → first math route topic `187`;
  - weak math topic → recommend weakest attempted math topic first;
  - mastered current route topic → next route topic;
  - all 42 math route topics mastered → `all_mastered` for math.
- Preserved legacy generic behavior when `subject_id` is not provided.
- Updated frontend callers that are math-pilot scoped to call `api.recommendNext(3)`:
  - topic page recovery badge path;
  - student badges/next-topic card.

## Files Changed

- `apps/backend/app/progress/router.py`
- `apps/backend/tests/test_sprint8_recommend_next.py`
- `apps/frontend/lib/api.ts`
- `apps/frontend/app/topics/[id]/page.tsx`
- `apps/frontend/app/student/badges/client.tsx`

## TDD Evidence

New Stage 09 tests were added first and failed before implementation:

```text
FAILED test_recommend_next_math_route_no_attempts_starts_at_first_route_topic
assert 1 == 187

FAILED test_recommend_next_math_route_mastered_current_moves_to_next_route_topic
assert 1 == 188
```

After implementation:

```text
cd apps/backend
.venv/bin/pytest tests/test_sprint8_recommend_next.py -q
13 passed, 15 warnings in 8.37s
```

## Local Verification

Backend regression set:

```text
.venv/bin/pytest tests/test_sprint8_recommend_next.py tests/test_math_route_plan.py tests/test_health.py -q
23 passed, 15 warnings in 8.64s
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

Required backups were run before production mutations:

```text
backend deploy backup: /opt/ai-tutor/deploy/backup/_out/manifest-20260814T164757Z.md5
OFFSITE OK: hash verified manifest-20260814T164757Z.md5

frontend deploy backup: /opt/ai-tutor/deploy/backup/_out/manifest-20260814T165300Z.md5
OFFSITE OK: hash verified manifest-20260814T165300Z.md5
```

## Production Deploy

Backend targeted rebuild/restart:

```text
cd /opt/ai-tutor/deploy
docker compose build backend
docker compose up -d --no-deps backend
backend_health=healthy
/ready HTTP=200
```

Frontend targeted rebuild/restart after `recommendNext(3)` caller update:

```text
docker compose build frontend
docker compose up -d --no-deps frontend
frontend_health=healthy
/ready HTTP=200
```

## Production Smoke

Authenticated API smoke without exposing token:

```text
/api/v1/progress/recommend-next?subject_id=3 HTTP=200
response subset: {'topic_id': 203, 'subject_id': 3, 'reason': 'weak_topic', 'mastery_score': 0.16666666666666666}
```

Student MVP smoke:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/mvp-student-flow.spec.ts --grep "student can open topic" --project=chromium
1 passed (25.2s)
```

## Notes

- The production user currently has a weak math topic (`203`) so production correctly returned `weak_topic` instead of first/new route topic.
- Production marker was not advanced because this was a targeted rebuild rather than the full release marker workflow.

## Remaining Non-Blockers

- Algebra/Geometry route-aware progression should be added after their route plans/readiness stages exist.
