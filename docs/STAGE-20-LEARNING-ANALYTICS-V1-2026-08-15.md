# Stage 20 — Learning Analytics V1 — 2026-08-15

## Scope

Stage 20 goal: show useful learning data without overwhelming users.

## Completed

- Added backend Learning Analytics V1 endpoint:
  - `GET /api/v1/analytics/learning?days=30`
  - role-gated to teacher/admin;
  - returns aggregate learning metrics only;
  - does not expose raw AI chat content.
- Added analytics types and API client method on frontend.
- Added a teacher dashboard analytics panel showing:
  - total attempts;
  - correct attempts;
  - accuracy;
  - average mastery;
  - subject aggregates;
  - weak topics.

## Backend Contract

Endpoint: `GET /api/v1/analytics/learning`

Response groups:

- `totals`: attempts, correct, accuracy, active topics, weak topics, average mastery;
- `subjects`: attempts/accuracy/mastery/weak topic count per subject;
- `weak_topics`: weakest topics, ordered by low mastery;
- `recent_activity`: aggregate attempts/correct by recent active date.

Access control:

- student: `403`;
- teacher/admin: `200`.

## TDD Evidence

RED before implementation:

```text
GET /api/v1/analytics/learning
student expected 403 but got 404
teacher expected 200 but got 404
```

GREEN after implementation:

```text
cd apps/backend
.venv/bin/pytest tests/test_learning_analytics.py -q
2 passed, 5 warnings
```

## Local Gates

```text
cd apps/backend
.venv/bin/pytest tests/test_learning_analytics.py tests/test_health.py -q
10 passed, 5 warnings

cd apps/frontend
npm run typecheck
npm run build
Compiled successfully
```

Final local regression subset before report:

```text
cd apps/backend
.venv/bin/pytest tests/test_learning_analytics.py tests/test_subjects.py tests/test_health.py -q
19 passed, 5 warnings

cd apps/frontend
npm run typecheck
exit 0
```

## Production Backup / Offsite

Required backup was run before production backend/frontend deploy:

```text
backup manifest: /opt/ai-tutor/deploy/backup/_out/manifest-20260814T224352Z.md5
OFFSITE OK: hash verified manifest-20260814T224352Z.md5
SMB total after upload: 220 files
```

## Production Deploy

Targeted backend/frontend deploy:

```text
docker compose build backend frontend
docker compose up -d --no-deps backend frontend
backend_health=healthy
frontend_health=healthy
/ready HTTP=200
```

## Production Smoke

Teacher/admin UI smoke:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/teacher-review-v2.spec.ts --project=chromium
1 passed
```

Analytics API smoke:

```text
GET /api/v1/analytics/learning
ANALYTICS_HTTP=200
{'attempts': 339, 'correct': 170, 'accuracy': 0.5015, 'active_topics': 27, 'weak_topics': 17}
subjects 7 weak 10 activity 11
```

Production health:

```text
/ready HTTP=200
backend/frontend/db/redis/prometheus healthy
```

## Privacy Boundary

The analytics endpoint and UI panel use aggregate learning records only. It does not return raw AI chat messages, raw answers, or private parent-facing chat data.

## Known Limitations

- `recent_activity` is based on `Progress.updated_at` aggregates, not a full historical time-series for every raw attempt. This is sufficient for V1 and stable across old/migrated data.
- Admin dashboard still has existing engagement metrics; the new Learning Analytics V1 panel is currently surfaced in the teacher dashboard. Admin can access the endpoint, and a later admin-specific UX pass can embed it in `/admin?tab=stats` if needed.

## Next Stage

Proceed to Stage 21 — Content Quality Workflow V1.
