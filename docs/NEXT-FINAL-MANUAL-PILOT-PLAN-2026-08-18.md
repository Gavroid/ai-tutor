# Next Final Manual Pilot Plan — 2026-08-18

## Purpose

This is the current manual pilot plan after the second autonomous AI-Tutor MVP execution pass.

Use this file to run the next supervised Math-only manual pilot wave without reading the full stage history first.

## Production Target

```text
Primary URL: https://school.431a.ru
LAN URL:     https://192.168.1.86
Branch:      mvp-rescue
Marker:      6e698a0
Checked:     2026-08-18 13:49 MSK
```

Use the LAN URL inside the local network if public DNS/proxy is not needed.

## Secret Hygiene

Do not paste or screenshot:

- passwords;
- tokens;
- cookies;
- JWTs;
- Bearer headers;
- `.env` values;
- private keys;
- SMB credentials;
- provider API keys.

Screenshots should show product UI only, not DevTools request headers or credential fields.

## Current Pilot Scope

| Subject | Status | Route | Source/RAG | Practice | Manual Pilot Decision |
|---|---|---:|---:|---:|---|
| Math | `mvp_ready` | 42/42 | 42/42 | 42/42 | Use for supervised pilot. |
| Algebra | `preview` | 19/19 | 0/19 | 19/19 | Do not pilot; navigation/practice preview only. |
| Geometry | `preview` | 13/13 | 0/13 | 13/13 | Do not pilot; navigation/practice preview only. |

Hard rule: if Algebra or Geometry appears as pilot-ready, treat that as a blocker. They must remain preview until verified source/RAG coverage exists and passes the RAG metadata contract.

## Pre-Flight Checklist

Run before a child session:

1. Open `/ready`.
   - Expected: HTTP 200, `status=ready`.
2. Open `/health`.
   - Expected: HTTP 200, `status=ok`.
3. Open `/api/v1/subjects`.
   - Expected: JSON list loads.
4. Confirm readiness:
   - Math: `mvp_ready`, route/source/practice all `42/42`.
   - Algebra: `preview`, source/RAG `0/19`.
   - Geometry: `preview`, source/RAG `0/13`.
5. Confirm no active incident:
   - login is not rate-limited;
   - `/subjects` loads quickly;
   - no visible legacy white/green UI blocks.

Blocker if `/ready` fails, Math is not `mvp_ready`, or student output shows raw JSON / `<think>` / hidden answers.

## Auth Rate-Limit Caution

Production login rate limiting is active and was observed during Stage 26 when too many real-auth Playwright suites ran together.

Manual testers should:

- avoid repeated wrong passwords;
- avoid quickly logging in/out across many roles in parallel;
- wait if the UI says: `Слишком много попыток входа. Подождите 15 минут.`

For automated testing, run the canonical cross-role suite serially or split role suites with delays. This is expected protection, not a product failure.

## Severity Definitions

| Severity | Meaning | Examples | Action |
|---|---|---|---|
| Blocker | Pilot cannot continue or safety/privacy boundary is broken | `/ready` fails; student sees `correct_answer`; parent sees raw AI chat; Math practice cannot be checked | Stop pilot, fix before continuing |
| High | Core role cannot complete its main job | Teacher cannot save QA status; parent dashboard fails; admin audit inaccessible; student cannot finish a Math topic | Fix before next pilot session |
| Medium | Workaround exists but confidence is reduced | Slow route, confusing copy, repeated practice, unclear preview/ready copy | Batch into polish pass |
| Low | Cosmetic issue | Typo, spacing, minor visual inconsistency | Fix opportunistically |

## Student Scenario — Math Learning Loop

Goal: verify the child-facing Math pilot path.

1. Log in as Student.
2. Open `/subjects`.
   - Expected: Prism dark UI, Math visible, Algebra/Geometry preview not promoted.
3. Open Math subject `/subjects/3`.
   - Expected: topic route visible, no mobile overflow.
4. Open first Math topic, or `/topics/187` if direct routing is preferred.
   - Expected: topic page loads.
5. Request explanation.
   - Expected: readable explanation.
   - Must not show raw JSON, `<think>`, `$$`, `\frac`, `\text`, broken table separators, or fenced JSON.
6. Generate practice.
   - Expected: task visible, answer controls usable.
7. Before submitting, inspect visible UI.
   - Expected: no `correct_answer` or hidden answer.
8. Submit a deliberately wrong answer.
   - Expected: clear feedback and recovery/try-again path.
9. Submit a correct answer or continue to another task.
   - Expected: positive feedback and next action.
10. Ask one chat-style follow-up if time permits.
   - Expected: readable response, no provider artifacts.
11. Open `/student/badges` if available.
   - Expected: page loads without pressure-heavy copy.

Blockers:

- hidden answer visible before submit;
- raw JSON or `<think>` visible;
- practice cannot be generated or checked;
- mobile layout requires horizontal scrolling;
- AI output is unreadable to a child.

## Parent Scenario — Aggregate Privacy

Goal: verify useful parent visibility without exposing raw child content.

1. Log in as Parent.
2. Open `/parents`.
   - Expected: linked child list or clear invite/empty state.
3. Open linked child dashboard.
   - Expected: aggregate cards and recommendations.
4. Confirm visible aggregate sections:
   - attempts;
   - accuracy;
   - mastery;
   - weak topics;
   - recommendations;
   - privacy note.
5. Confirm parent does not see:
   - raw AI chat;
   - `question_text`;
   - `user_answer`;
   - `correct_answer`;
   - raw `feedback`;
   - unrelated child data.
6. Try an unrelated child dashboard URL only if testing privacy explicitly.
   - Expected: 404, no private data.

Blockers:

- parent sees raw AI chat or raw attempt fields;
- parent can access unrelated child;
- dashboard fails to load aggregate data.

## Teacher Scenario — Analytics / Readiness / QA

Goal: verify teacher can operate the content quality workflow.

1. Log in as Teacher.
2. Open `/teacher`.
   - Expected: teacher workspace loads.
3. Confirm Learning Analytics surface.
   - Expected: aggregate attempts, accuracy, mastery, weak topics; no raw student chat.
4. Open `/teacher/topics`.
   - Expected: readiness matrix with route metadata and filters.
5. Filter by route tier/checkpoint if visible.
   - Expected: results update without raw JSON.
6. Open a topic detail.
   - Expected: follow-up/fallback/status areas load.
7. If editable material exists, open `/teacher/materials/{materialId}`.
8. Test QA workflow:
   - set `Needs review` with note;
   - set `Blocked` with note;
   - set `Approved` only after review.
9. Confirm `blocked` and `needs_review` materials cannot publish.
10. Confirm teacher cannot view/edit another teacher’s unpublished material if that scenario is available.

Blockers:

- teacher can publish blocked/needs-review material;
- QA status does not save;
- teacher can mutate another teacher’s unpublished draft;
- teacher UI exposes raw JSON to normal users.

## Admin Scenario — Audit / Ops / Monitoring

Goal: verify operator view is usable without SSH for common checks.

1. Log in as Admin.
2. Open `/admin`.
3. Check Audit tab.
   - Expected: audit log loads.
4. Filter audit by a recent action if available:
   - `material.quality_status.update`;
   - `user.register`;
   - `material.publish`.
5. Check Users tab.
   - Expected: user list loads, no password/hash/secret values.
6. Check Stats tab.
   - Expected: counts render.
7. Check Realtime tab.
   - Expected: DB/Redis/backup/disk or clear non-secret status.
8. Confirm no tokens/secrets/env values appear.
9. Confirm `/ready` and `/health` remain green after testing.

Blockers:

- audit inaccessible to admin;
- audit shows secrets;
- realtime hides an actual readiness failure;
- admin endpoints are accessible to parent/student/teacher.

## Mobile Scenario

Goal: verify core pilot surfaces on a phone-sized viewport.

Use approximately iPhone SE viewport: `375 × 667`.

1. Open `/login`.
2. Log in as Student.
3. Open `/subjects`.
4. Open `/subjects/3`.
5. Open a Math topic.
6. Request explanation or generate practice.
7. Check:
   - no horizontal overflow;
   - buttons tappable;
   - text readable;
   - answer controls usable;
   - no broken math markers.
8. If time permits, repeat `/parents` quickly.

Blockers:

- horizontal scrolling on core student pages;
- practice controls unusable;
- explanation/practice unreadable on mobile.

## Recovery / Error Scenario

Goal: verify failures are safe and understandable.

1. Open `/login`.
2. Try one wrong password only.
   - Expected: readable error, no stack trace.
3. Do not repeat many failed attempts unless testing auth rate-limit specifically.
4. Open invalid topic URL such as `/topics/999999`.
   - Expected: safe not-found state, no backend internals.
5. Open teacher/admin filters with no matching results.
   - Expected: empty state or no rows, no crash.

Blockers:

- stack trace visible;
- raw backend exception visible;
- rate-limit message unclear;
- page stuck with no recovery path.

## Automation Evidence Available

Recent automation evidence from this execution pass:

```text
Stage 22 student-output safety backend slice: 83 passed
Stage 22 LAN student Playwright smoke: 2 passed
Stage 23 parent privacy backend: 7 passed
Stage 23 LAN parent privacy Playwright: 1 passed
Stage 24 teacher/admin RBAC backend: 10 passed
Stage 24 LAN teacher/admin RBAC Playwright: 3 passed
Stage 25 restore drill: RESTORE DRILL PASSED
Stage 26 canonical cross-role Playwright: 4 passed
Production READY_HTTP=200
Production HEALTH_HTTP=200
```

## Screenshot Checklist

Capture screenshots only with no secrets visible:

- `/subjects` readiness cards showing Math ready and Algebra/Geometry preview.
- Math topic explanation.
- Math practice before submit, proving no hidden answer visible.
- Math feedback after wrong answer.
- Parent dashboard privacy note.
- Teacher Learning Analytics panel.
- Teacher readiness matrix.
- Teacher Content QA panel if editable material exists.
- Admin audit tab.
- Admin realtime snapshot.
- Mobile `/subjects` or Math topic page.

## Feedback Intake Template

Use `docs/MATH-PILOT-FEEDBACK-INTAKE-2026-08-16.md` as the primary log.

Copyable row format:

```text
Date/time MSK:
Reporter:
Role:
Route/page:
Scenario:
Step:
Expected:
Actual:
Severity:
Evidence path:
Reproducible? yes/no:
Owner:
Decision:
Status:
```

Use these scenario tags:

- `student-login`
- `student-subjects`
- `student-topic-explain`
- `student-practice-generate`
- `student-practice-check`
- `parent-dashboard`
- `parent-privacy`
- `teacher-analytics`
- `teacher-readiness`
- `teacher-qa-workflow`
- `admin-audit`
- `admin-realtime`
- `mobile`
- `recovery-error`

## Stop / Continue Decision

Start manual pilot with Math only if:

- `/ready` and `/health` are 200;
- Math is `mvp_ready`;
- student can complete explain → practice → answer check;
- parent dashboard remains aggregate-only;
- teacher/admin boundaries remain intact.

Stop and fix first if any blocker appears.

Do not expand pilot scope to Algebra or Geometry until verified source/RAG coverage exists and promotion decision changes in a future evidence-backed stage.

## Final Stage 28 Decision

This plan is current as of `2026-08-18` and can be handed to Igor for the next supervised Math-only manual pilot wave.
