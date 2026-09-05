# Final Manual Testing Plan For Igor — 2026-08-16

## Production Target

Primary URL: `https://school.431a.ru`  
LAN URL: `https://192.168.1.86`  
Branch: `mvp-rescue`  
Production marker: `6e698a0`

Use the LAN URL if you are testing inside the local network or need to bypass public DNS/proxy routing.

## Test Accounts

Use the operator-provided pilot accounts for these roles:

- Student
- Parent
- Teacher
- Admin

Passwords, tokens, cookies, `.env`, private key contents, JWTs, Bearer values, and SMB credentials must not be written into this document, screenshots, bug reports, or chat.

## Exact Route List

### Public / unauthenticated checks

- `/login`
- `/register`
- `/forgot-password`
- `/ready`
- `/health`
- `/api/v1/subjects`

### Student routes

- `/subjects`
- `/subjects/3`
- `/topics/187` or first visible Math topic
- `/diagnostic`
- `/student/badges`

### Parent routes

- `/parents`
- `/parent/dashboard/{studentId}`
- `/link-parent`

### Teacher routes

- `/teacher`
- `/teacher/topics`
- `/teacher/topics/{topicId}`
- `/teacher/generate`
- `/teacher/materials/{materialId}` if an editable material exists

### Admin routes

- `/admin`
- `/admin?tab=audit`
- `/admin?tab=users`
- `/admin?tab=stats`
- `/admin?tab=tools`
- `/admin?tab=invites`
- `/admin?tab=realtime`

## Severity Definitions

| Severity | Meaning | Examples |
|---|---|---|
| Blocker | Manual pilot cannot continue or privacy/safety boundary is broken | `/ready` fails, student sees `correct_answer`, parent sees raw AI chat, Math practice cannot be checked |
| High | Core flow works partially but a role cannot complete its main job | Teacher cannot save QA status, parent dashboard does not load, admin audit inaccessible |
| Medium | Workaround exists but confidence is reduced | Slow page, confusing preview/ready copy, non-critical metric missing |
| Low | Cosmetic issue | Typo, spacing, minor visual inconsistency |

## Pre-Flight

1. Open `/ready`.
   - Expected: HTTP 200 and `status=ready`.
2. Open `/health`.
   - Expected: HTTP 200 and `status=ok`.
3. Open `/api/v1/subjects`.
   - Expected: JSON list loads.
4. Confirm subject readiness:
   - Math: `mvp_ready`, route `42/42`, sources `42/42`, practice `42/42`.
   - Algebra: `preview`, route `19/19`, sources `0/19`, practice `19/19`.
   - Geometry: `preview`, route `13/13`, sources `0/13`, practice `13/13`.

Blocker if `/ready` fails or Math is not shown as ready.

## Student Scenario

Goal: verify the child-facing Math pilot loop.

1. Log in as Student.
2. Open `/subjects`.
   - Expected: dark Prism UI, no white legacy cards, Math visible.
3. Open Math subject `/subjects/3`.
   - Expected: route/topic list visible.
4. Open first Math topic.
   - Expected: topic page loads, no horizontal overflow.
5. Request topic explanation.
   - Expected: readable formatted explanation; no raw JSON, no `<think>`, no broken markdown table, no broken math markers.
6. Generate a practice task.
   - Expected: task visible, answer controls usable.
7. Before answering, inspect visible UI and, if possible, browser Network response.
   - Expected: no visible `correct_answer` before answer submission.
8. Submit an intentionally wrong answer.
   - Expected: readable feedback and next-step guidance.
9. Submit or attempt a correct answer if another task is available.
   - Expected: positive feedback and next action.
10. Open `/student/badges`.
   - Expected: badges page loads; no pressure-heavy “streak lost” style.

Blockers:

- `correct_answer` visible before submit.
- Raw JSON appears in student-facing output.
- Practice generation/checking fails for Math.
- Mobile layout requires horizontal scrolling.

## Parent Scenario

Goal: verify privacy and useful aggregate reporting.

1. Log in as Parent.
2. Open `/parents`.
   - Expected: linked child list or clear empty/invite state.
3. Open child dashboard.
   - Expected: aggregate report cards visible.
4. Confirm these sections exist:
   - `Что улучшилось`;
   - `Где нужна помощь`;
   - `Что сделать завтра`;
   - `Маршрут`.
5. Confirm privacy note is visible.
6. Confirm parent sees aggregate progress only:
   - attempts;
   - accuracy;
   - mastery;
   - weak topics;
   - recommendations.
7. Confirm parent does not see raw AI chat or private student messages.

Blockers:

- Parent sees raw AI chat/messages.
- Parent can access another child dashboard.
- Parent dashboard fails to load aggregate data.

## Teacher Scenario

Goal: verify readiness, analytics, and repeatable content QA.

1. Log in as Teacher.
2. Open `/teacher`.
   - Expected: teacher workspace loads.
3. Confirm Learning Analytics panel is visible.
   - Expected: attempts, correct, accuracy, mastery, weak topics.
4. Open `/teacher/topics`.
   - Expected: readiness matrix with route metadata and filters.
5. Filter by route tier or checkpoint.
   - Expected: table/card updates without raw JSON.
6. Open a topic detail.
   - Expected: follow-up/fallback/status sections load.
7. If an editable material exists, open `/teacher/materials/{materialId}`.
8. Use `Content QA Workflow`:
   - set `Needs review` with a short note;
   - set `Blocked` with a short note;
   - set `Approved` after review.
9. Confirm status changes are saved.
10. Confirm blocked/needs-review content cannot be published until approved.

Blockers:

- Teacher can publish blocked or needs-review material.
- QA status changes are not saved.
- Teacher can view/edit another teacher’s unpublished material.
- Teacher UI exposes raw JSON to normal users.

## Admin Scenario

Goal: verify audit, ops, monitoring, and user-management surfaces.

1. Log in as Admin.
2. Open `/admin`.
3. Check `Audit` tab.
   - Expected: audit log loads.
4. Filter audit by `material.quality_status.update` after Teacher scenario.
   - Expected: QA status change appears.
5. Check `Users` tab.
   - Expected: users list loads, no secrets displayed.
6. Check `Stats` tab.
   - Expected: counts render.
7. Check `Realtime` tab.
   - Expected: snapshot loads or shows clear non-secret error.
8. Confirm HTTP 5xx count is zero or explainable.
9. Confirm no tokens/secrets are visible.

Blockers:

- Admin audit inaccessible.
- QA status changes are missing from audit.
- UI displays tokens/secrets/env values.
- Realtime/ops surface hides current `/ready` failure.

## Mobile Scenario

Goal: verify pilot pages are usable on a phone.

Use viewport around iPhone SE: `375 × 667`.

1. Open `/login`.
2. Log in as Student.
3. Open `/subjects`.
4. Open `/subjects/3`.
5. Open a Math topic.
6. Request explanation or generate practice.
7. Confirm no horizontal overflow.
8. Confirm buttons are tappable and text is readable.
9. Repeat parent dashboard quickly if time permits.

Blockers:

- Horizontal overflow on core pages.
- Practice answer controls unusable on mobile.
- Student explanation/practice unreadable.

## Recovery / Error Scenario

Goal: verify failures are safe and understandable.

1. Open `/login`.
2. Try one wrong password.
   - Expected: login remains on `/login`, error is readable.
3. Do not repeat many failed logins; avoid triggering rate-limit unless testing auth specifically.
4. Open an invalid topic URL such as `/topics/999999`.
   - Expected: no stack trace or raw backend internals.
5. Open teacher/admin filters with no matching results.
   - Expected: empty state or no rows; no crash.

Blockers:

- Stack trace visible to user.
- Raw backend exception visible.
- Rate-limit message is unclear.
- Page stuck with no recovery path.

## Screenshot Checklist

Capture screenshots only with no secrets visible:

- `/subjects` readiness cards.
- Math topic explanation/practice after answer check.
- Parent dashboard privacy note.
- Teacher Learning Analytics panel.
- Teacher Content QA Workflow panel.
- Admin audit filtered by `material.quality_status.update`.
- Admin Realtime snapshot.
- Mobile `/subjects` or Math topic page.

## Feedback Template

```text
Date/time:
Tester:
Browser/device:
URL used:
Role:
Scenario:
Step number:
Expected result:
Actual result:
Severity:
Screenshot/video path:
Can reproduce? yes/no:
Notes:
```

## Automation Evidence Already Collected

- Cross-role pilot suite: `4 passed`.
- Student MVP flow: passed.
- Parent dashboard privacy/actionability: passed.
- Teacher review no raw JSON: passed.
- Mobile iPhone SE login: passed.
- Security/privacy backend subset: `27 passed`.
- Latest broad backend subset: `34 passed`.
- Production `/ready`: `200`.
- Production `/health`: `200`.

## Final Manual Testing Decision

Start manual testing with Math only. Keep Algebra and Geometry visible as preview, not pilot-ready.
