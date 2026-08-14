# Math Live Pilot Script — 2026-08-14

## Purpose

Manual live pilot script for the math MVP scope: `Математика (6 класс — повторение пройденного материала)`.

Use this as the human runbook for a student + parent + teacher check. Do not write passwords in this document.

## Preconditions

- Production URL: `https://school.431a.ru`
- LAN URL: `https://192.168.1.86`
- Current pilot subject: `/subjects/3`
- Math route plan API: `/api/v1/subjects/3/route-plan`
- Production health before test: `/ready` should return HTTP 200.
- Parent privacy boundary: parent dashboards show aggregate progress only, not raw AI chat.

## Test Accounts

Use the existing QA/pilot accounts by role. Passwords are intentionally not included here.

- Student: pilot student account.
- Parent: linked parent QA account.
- Teacher: teacher QA account.
- Admin: admin QA account only if needed for health/monitoring checks.

## Scenario A — Student Core Flow

### 1. Login

1. Open `https://school.431a.ru/login`.
2. Login as the student.
3. Expected: redirect to `/subjects` or student landing page.
4. Blocker if: login fails, blank page, visible 5xx, or legacy white UI dominates the page.

### 2. Open Math Subject

1. Open `/subjects`.
2. Click `Математика (6 класс — повторение пройденного материала)`.
3. Expected: open `/subjects/3`.
4. Expected: readiness panel shows math as ready/MVP-ready, route topics visible.
5. Check mobile if possible: no horizontal overflow.

### 3. Open Route Map

1. On `/subjects/3`, review the topic cards.
2. Confirm there are 42 topics in route order.
3. Open the first route topic or a recommended topic.
4. Expected: topic page opens under `/topics/{id}`.

### 4. Start Diagnostic

1. Open `/diagnostic` or diagnostic entry point from the UI.
2. Choose/start math diagnostic if prompted.
3. Answer at least 3 questions.
4. Expected: questions are readable, no raw `correct_answer` visible before submit.
5. Expected: no raw JSON, `<think>`, broken markdown tables, or broken math markers.

### 5. Complete One Easy Topic

1. Open an easy/base topic, for example `/topics/187`.
2. Click the explanation action.
3. Read the explanation.
4. Expected: explanation is readable on mobile and desktop.
5. Expected: follow-up buttons appear where relevant.

### 6. Practice — Wrong Answer

1. Click `Практика` / `Дай задание`.
2. Select an intentionally wrong option.
3. Click `Проверить`.
4. Expected: feedback says there is an error and gives useful guidance.
5. Expected: answer truth is server-owned; no `correct_answer` leaks in generate response/UI before submit.

### 7. Practice — Correct Answer

1. Select the correct answer.
2. Click `Проверить`.
3. Expected: `Верно!` or equivalent success state.
4. Expected: next action is clear: next task, retry, or next topic.

## Scenario B — Parent Dashboard

1. Login as parent.
2. Open `/parents`.
3. Open the linked child dashboard.
4. Confirm weekly/overall summary is understandable in under 1 minute.
5. Confirm weak topics and next recommendation are shown when data exists.
6. Confirm parent does **not** see raw student AI chat or private messages.
7. Blocker if: raw chat is visible, child privacy boundary breaks, or parent can open another child by ID.

## Scenario C — Teacher Readiness

1. Login as teacher.
2. Open `/teacher`.
3. Open topic readiness view, expected route: `/teacher/topics`.
4. Filter/review math topics.
5. Confirm indicators are visible for source, fallback, followup, route/checkpoint status.
6. Open a topic detail page if available.
7. Confirm teacher can review/edit safe content knobs without raw JSON exposure to students.

## Scenario D — Admin Quick Health

1. Login as admin only if necessary.
2. Open `/admin`.
3. Confirm users/invites/audit/realtime are inside the `/admin` frame.
4. Confirm there is no separate legacy `/admin?tab=...` workflow.
5. Confirm monitoring/realtime values do not show obvious stale/failing state.

## Scenario E — Mobile Smoke

Use an iPhone-size viewport.

Check:

- `/subjects`
- `/subjects/3`
- `/topics/187`
- `/topics/200`
- `/topics/228`
- `/diagnostic`

Expected:

- no horizontal overflow;
- no white legacy cards;
- lesson/chat/practice areas readable;
- buttons are finger-sized;
- feedback does not require sideways scrolling.

## Blocker Definitions

- P0 blocker: login impossible, `/ready` fails, student cannot complete lesson, parent sees private chat, production data corruption, 5xx on core route.
- P1 blocker: broken route UI, diagnostic inaccurate, teacher cannot review readiness, mobile core layout unusable.
- P2 issue: typo, minor spacing, cosmetic low-risk bug.

## Evidence To Capture

For each run, record:

- date/time;
- role;
- route tested;
- pass/fail;
- screenshot name if captured;
- blocker severity;
- short note with exact observed behavior.

## Stage 05 Verification

This script intentionally contains no passwords or secret values. Production route checks should verify `/ready`, `/subjects`, `/subjects/3`, `/topics/187`, `/topics/200`, `/topics/228`, `/diagnostic`, and `/teacher/topics` return non-5xx responses before the human pilot.


## Automated Dry-Run Evidence — 2026-08-14

Production route smoke:

```text
/ready HTTP=200
/health HTTP=200
/subjects HTTP=200
/subjects/3 HTTP=200
/topics/187 HTTP=200
/topics/200 HTTP=200
/topics/228 HTTP=200
/diagnostic HTTP=200
/teacher/topics HTTP=200
/parents HTTP=200
/admin HTTP=200
```

Student MVP E2E dry-run against LAN production URL:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/mvp-student-flow.spec.ts --grep "student can open topic" --project=chromium
1 passed (32.1s)
```

Frontend contract verification:

```text
npm run typecheck
exit 0
```

Note: the E2E was updated to expect the current backend-managed follow-up labels: `Ещё пример`, `Проверь меня`, `Дай задачу`.
