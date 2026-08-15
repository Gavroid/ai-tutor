# Manual Testing Plan — 2026-08-15

## Scope

This is the Stage 22 manual testing harness for AI-Tutor MVP. It is written so a human tester can execute the pilot without reading chat history.

Primary production URL: `https://school.431a.ru`  
LAN production URL: `https://192.168.1.86`

Use LAN URL if DNS or TLS routing is being inspected directly. Do not write passwords, tokens, cookies, `.env`, private keys, or Bearer values into screenshots or notes.

## Severity Definitions

| Severity | Meaning | Examples |
|---|---|---|
| Blocker | Pilot cannot continue or privacy/safety boundary is broken | Login impossible for core role, raw AI chat shown to parent, `correct_answer` exposed to student before answer, `/ready` fails |
| High | Core role works but major learning flow is broken | Student cannot generate/check practice, teacher cannot change QA status, parent report missing aggregate progress |
| Medium | Workaround exists but tester confidence is reduced | Slow page, confusing label, missing non-critical metric, mobile layout cramped but usable |
| Low | Cosmetic or copy issue | Typo, spacing, non-blocking visual inconsistency |

## Global Pre-Checks

1. Open `/ready` and confirm `HTTP 200` / `{"status":"ready"}`.
2. Open `/health` and confirm `HTTP 200` / `status=ok`.
3. Open `/subjects` and confirm the page loads without console errors.
4. Confirm subject readiness labels:
   - Math: `MVP-ready`, route `42/42`, sources `42/42`, practice `42/42`.
   - Algebra: `Preview`, route `19/19`, sources `0/19`, practice `19/19`.
   - Geometry: `Preview`, route `13/13`, sources `0/13`, practice `13/13`.

## Scenario 1 — Student Learning Flow

Goal: verify the main child-facing learning loop is clean, mobile-readable, and does not expose answers early.

1. Log in as the pilot student account provided by the operator.
2. Open `/subjects`.
3. Open Math subject.
4. Open the first Math topic.
5. Click/request topic explanation.
6. Confirm explanation renders as readable formatted text:
   - no raw JSON;
   - no broken markdown tables;
   - no broken math markers;
   - no code fences shown as accidental UI.
7. Generate practice.
8. Before submitting an answer, inspect visible UI and Network response if available.
9. Confirm `correct_answer` is not visible to the student before answering.
10. Submit a wrong answer.
11. Confirm feedback is readable and gives a next step.
12. Submit/try a correct answer if the UI offers another task.
13. Confirm next-step buttons do not require copying raw prompts.

Blockers:

- raw JSON or `correct_answer` visible before answering;
- practice cannot be generated for Math pilot topics;
- answer check fails silently;
- mobile content overflows horizontally.

## Scenario 2 — Parent Privacy And Progress

Goal: verify parent gets aggregate progress only, not raw AI chat.

1. Log in as parent account provided by the operator.
2. Open `/parents`.
3. Confirm linked child list is visible.
4. Open a child dashboard.
5. Confirm report cards are visible:
   - `Что улучшилось`;
   - `Где нужна помощь`;
   - `Что сделать завтра`;
   - `Маршрут`.
6. Confirm progress is aggregate only:
   - attempts;
   - accuracy;
   - mastery;
   - weak topics;
   - recommendations.
7. Confirm raw AI chat messages are not visible.
8. Confirm privacy note is visible.

Blockers:

- parent sees raw AI chat content;
- child private answers/messages appear in parent UI;
- dashboard cannot load aggregate progress.

## Scenario 3 — Teacher Content Quality Workflow

Goal: verify teacher can identify weak content and manage QA status repeatably.

1. Log in as teacher account provided by the operator.
2. Open `/teacher`.
3. Confirm Learning Analytics panel is visible:
   - attempts;
   - correct;
   - accuracy;
   - mastery;
   - weak topics.
4. Open `/teacher/topics`.
5. Confirm readiness matrix shows route metadata and filters.
6. Open a topic detail.
7. Confirm followups/fallback editor is usable without raw JSON requirement for the common path.
8. Open a material detail if an editable material exists.
9. Use `Content QA Workflow`:
   - set `Needs review` with a note;
   - set `Blocked` with a note;
   - set `Approved` after review.
10. Confirm blocked/needs-review content is not published until approved.

Blockers:

- teacher can publish `needs_review` or `blocked` material;
- QA status changes are not saved;
- teacher can edit another teacher’s unpublished material;
- raw JSON leaks into normal student-facing output.

## Scenario 4 — Admin Ops And Audit

Goal: verify admin can inspect users/audit/ops without SSH for common pilot checks.

1. Log in as admin account provided by the operator.
2. Open `/admin`.
3. Confirm Audit, Users, Stats, Tools, Invites, Realtime tabs are reachable.
4. Filter audit log by `material.quality_status.update`.
5. Confirm recent QA changes appear after teacher scenario.
6. Open Stats and confirm user counts render.
7. Open Realtime and confirm snapshot loads or shows a clear non-secret error.
8. Confirm no secrets/tokens are displayed in UI.

Blockers:

- admin cannot open audit log;
- audit omits sensitive teacher QA transitions;
- UI displays secrets, tokens, or raw env values;
- `/ready` is failing while UI appears healthy.

## Scenario 5 — Recovery After Errors

Goal: verify user-facing failures are understandable and safe.

1. Open `/login`.
2. Try a wrong password once.
3. Confirm login stays on `/login` and shows a human-readable error.
4. Do not repeat many failed logins; avoid triggering rate-limit unnecessarily.
5. Open a non-existent topic URL such as `/topics/999999`.
6. Confirm the UI does not expose stack traces or raw backend internals.
7. Trigger a recoverable teacher/admin filter with no results.
8. Confirm empty state is clear and not a crash.

Blockers:

- stack trace visible to user;
- raw backend exception shown;
- login rate-limit gives generic/unclear failure;
- page gets stuck with no recovery path.

## Scenario 6 — Mobile Smoke

Goal: verify iPhone-size layout remains usable.

1. Use mobile viewport around 375 × 667.
2. Open `/login`.
3. Log in as student.
4. Open `/subjects`.
5. Open Math topic.
6. Generate or view a practice task.
7. Confirm no horizontal overflow.
8. Confirm main CTA buttons remain tappable.
9. Repeat parent dashboard on mobile if time allows.

Blockers:

- horizontal overflow requiring side-scroll on core pages;
- answer buttons unusable on mobile;
- practice/explanation unreadable on phone.

## Screenshot Checklist

Capture screenshots only without secrets visible:

- `/subjects` readiness cards.
- Student topic explanation/practice after answer check.
- Parent dashboard privacy note.
- Teacher Learning Analytics panel.
- Teacher QA workflow panel.
- Admin audit filtered by QA status action.
- Mobile `/subjects` or topic page.

## Dry-Run Evidence From Automation

Selected Stage 22 dry-run scenarios passed on production LAN URL:

```text
Student MVP flow: 1 passed
Parent dashboard V2 privacy/actionability: 1 passed
Teacher review mode V2: 1 passed
Mobile iPhone SE login: 1 passed
/ready HTTP=200
/health HTTP=200
```

## Tester Notes Template

```text
Date/time:
Tester:
Browser/device:
URL used:
Scenario:
Step number:
Expected:
Actual:
Severity:
Screenshot/video path:
Notes:
```
