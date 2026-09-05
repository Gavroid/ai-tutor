# Stage 06 — Student Lesson Loop Polish Report — 2026-08-14

## Scope

Stage 06 goal: make the student lesson loop feel guided rather than like a generic chat.

## Completed

- Improved `/topics/[id]` next-step panel from passive text to an actionable guided CTA.
- Added state-specific next actions:
  - before explanation: `Начать объяснение`;
  - after explanation: `Перейти к практике`;
  - after wrong answer: `Попробовать ещё раз`;
  - after correct answer: `Следующая тема` when route has `next_topic_id`;
  - route end fallback: `Следующее задание`.
- Wired math route-plan lookup for the current pilot scope (`subject_id=3`) so correct answers can point to the next math route topic.
- Preserved Prism/Split UI classes and dark layout.
- Kept student-facing safety rules: no copy button, no raw JSON, no `correct_answer` leak before submit.

## Files Changed

- `apps/frontend/app/topics/[id]/page.tsx`
- `apps/frontend/app/topics/[id]/components.tsx`
- `apps/frontend/e2e/mvp-student-flow.spec.ts`

## Local Verification

```text
cd apps/frontend
npm run typecheck
exit 0

npm run build
Compiled successfully
```

## Production Backup / Offsite

Required backup was run before frontend production deploy:

```text
backup manifest: /opt/ai-tutor/deploy/backup/_out/manifest-20260814T154640Z.md5
OFFSITE OK: hash verified manifest-20260814T154640Z.md5
SMB total after upload: 187 files
```

## Production Deploy

The production host does not have `npm` in PATH, so host-level npm commands were not used. Frontend deploy used the Docker path:

```text
cd /opt/ai-tutor/deploy
docker compose build frontend
docker compose up -d --no-deps frontend
```

Docker build result:

```text
Next.js 16.2.10
Compiled successfully
Finished TypeScript
Generated static pages 21/21
Image deploy-frontend Built
```

Production health after deploy:

```text
frontend_health=healthy
/ready HTTP=200
```

## Production Smoke

Student MVP E2E against LAN production URL:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/mvp-student-flow.spec.ts --grep "student can open topic" --project=chromium
1 passed (36.1s)
```

Mobile topic smoke:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/mobile-audit.spec.ts --grep "topic_detail" --project=chromium
3 passed (6.1s)
```

## Notes

- The first E2E run after deploy failed only because the assertion used a strict locator matching both new valid buttons (`Следующая тема` and `Следующее задание`). The UI state was correct; the test was updated to assert the first matching guided action.
- Production marker was not advanced because this was a targeted frontend container rebuild rather than a full release marker workflow.

## Remaining Non-Blockers

- Stage 06 currently uses the math pilot route plan (`subject_id=3`) explicitly. Later multi-subject stages should generalize this after Algebra/Geometry route readiness is added.
