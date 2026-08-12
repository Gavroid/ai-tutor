# Pilot Walkthrough Notes

## 2026-08-11 22:17 MSK — Manual QA / smoke continuation

Scope: continued `docs/HANDOFF-QA-BUGFIX-NEXT-CONTEXT-2026-08-11.md` from top to bottom. No secrets printed; production DB checks were read-only except the documented E2E rate-limit bucket reset below.

### Operator preflight

- Repo on `mvp-rescue`, HEAD before fixes: `351c22f`.
- Production marker before fixes: `351c22f`.
- `docker compose ps`: backend/db/frontend/redis/prometheus healthy; proxy/grafana running.
- `https://192.168.1.86/ready`: `HTTP=200`, `{"status":"ready"}`.
- `https://192.168.1.86/health`: `HTTP=200`, `{"status":"ok","env":"production",...}`.
- Edge hardening: `/docs`, `/openapi.json`, `/graphql`, `/metrics` returned `HTTP=404` on both LAN and `school.431a.ru`.
- Internal Prometheus scrape from Docker returned Python metrics from `backend:8000/metrics`.
- Backup/offsite log: latest `2026-08-11T03:00:18Z offsite backup done: uploaded=23 deleted=0 total=201`.
- Restore drill log: latest `2026-08-11T15:12:01Z ✓✓✓ RESTORE DRILL PASSED`, backup `db-20260811T030001Z.sql.gz`, `32` tables, `14` users.
- Admin ops status checked inside backend container with generated in-process admin token: `http_status=200`, `ok=true`, DB/Redis/uploads/teacher_registry/commit_marker OK.

### Student / multi-subject smoke

- `BASE_URL=https://192.168.1.86 npx playwright test e2e/multi-subject-readiness.spec.ts e2e/mvp-student-flow.spec.ts --project=chromium --reporter=line --workers=1` passed: `3 passed`.
- Full post-fix production E2E pack passed: `7 passed (31.4s)` for `multi-subject-readiness`, `mvp-student-flow`, and `pilot.spec.ts`.
- Student flow coverage verified login, subjects, topic, explain, clean AI output contract, practice, wrong/correct feedback, chat, reset, and budget message behavior through existing E2E.
- Multi-subject coverage verified MVP-ready math vs preview subjects and no misleading preview RAG/source readiness.

### Parent flow finding

- Read-only DB query showed corrupted production links for `parent-e2e@example.com`: multiple active `parent_student_links` rows where `parent_id=19` and `student_id=19`, and the linked row points to a user with `role=parent`, not `student`.
- Production API before code fix confirmed `parent-e2e@example.com` `/api/v1/parents/children` returned `[]` despite those corrupted active rows.
- Existing valid Stage 5 linked pair remains: `stage5-parent-1785514575@example.com` -> `stage5-student-1785514575@example.com`.
- Root cause in code: parent service reused active links without checking that linked user is a real student; corrupted active parent→parent placeholders could be reused for new invites and could be exposed as children in tests.
- Fix applied locally: `create_invite_for_parent()` and `list_linked_students()` now require `student_id != parent.id` and `User.role == STUDENT` for active child/reuse logic.
- Regression tests added in `tests/test_sprint59_multi_child.py`:
  - `test_active_links_to_non_student_users_are_ignored`
  - `test_parent_invite_does_not_reuse_corrupted_active_self_link`
- TDD RED confirmed both tests failed before fix; GREEN confirmed after service patch.

### Teacher/admin smoke

- Production E2E `pilot.spec.ts` admin and teacher flows passed after rate-limit reset.
- `pilot.spec.ts` student scenario was stale against current UI labels (`Практика` instead of `Дай задание`, and updated task label DOM); selectors were updated only in the test.
- No destructive teacher/admin save actions were performed.

### Rate-limit handling

- Repeated manual/E2E login attempts hit production login rate limit.
- Redis inspection showed one bucket only: `login_rl:192.168.1.35:1984972`, `VAL=30`, short TTL.
- Cleared only that E2E-origin bucket with `redis-cli del login_rl:192.168.1.35:1984972`; follow-up scan returned no login buckets.

### Verification commands

- Backend targeted gates: `.venv/bin/pytest tests/test_sprint59_multi_child.py tests/test_parents_materials.py tests/test_parent_dashboard.py tests/test_health.py -q` -> `42 passed, 55 warnings`.
- Frontend typecheck: `npm run typecheck` -> `tsc --noEmit` passed.
- Production E2E pack: `BASE_URL=https://192.168.1.86 npx playwright test e2e/multi-subject-readiness.spec.ts e2e/mvp-student-flow.spec.ts e2e/pilot.spec.ts --project=chromium --reporter=line --workers=1` -> `7 passed (31.4s)`.

### Open follow-up

- Local backend/frontend fixes are verified but still need commit/deploy verification in this session.
- Production DB still contains historical corrupted `parent-e2e` self-link rows. The code fix prevents reuse/exposure, but cleaning those rows would be a production data mutation and was not performed during this QA pass.

## 2026-08-12 09:39 MSK — Final pilot-test readiness closeout

Scope: prepared the pilot environment for Igor's manual testing after the QA bugfix pass.

### Parent test account readiness

- Verified `parent-e2e@example.com` has a known test password slot and role `parent` without printing the password.
- Verified `stage5-parent-1785514575@example.com` remains a valid linked data pair but has no known UI-login password slot.
- Created a narrow production DB backup before parent-link mutation: `/opt/ai-tutor/deploy/backup/_manual/qa-parent-link-pre-20260811.sql` (`4.1K`).
- Used the app's parent invite service flow to link `parent-e2e@example.com` to `student-e2e@example.com`.
- Post-link DB check shows `parent-e2e@example.com -> student-e2e@example.com` as `active`; older `parent-e2e -> parent-e2e` rows remain `pending` and are ignored by the fixed code.
- Parent API verification for `parent-e2e@example.com`:
  - `/api/v1/parents/children` -> HTTP 200 with `Student E2E`;
  - `/api/v1/parents/children/20` -> HTTP 200;
  - `/api/v1/parents/students/20/dashboard` -> HTTP 200;
  - dashboard response includes `privacy_note`;
  - dashboard recommendations count: `1`.

### Additional invite-flow bugfix

- Found another concrete edge-case before manual testing: when a parent already had an active child, `/api/v1/parents/invite` could return a code for the active child link, which cannot be accepted by another child because `accept_invite()` only accepts `pending` links.
- Added regression test: `test_parent_with_existing_child_gets_pending_invite_for_another_child`.
- Fixed `create_invite_for_parent()` to reuse only existing pending placeholder links, otherwise create a fresh pending placeholder.

### Verification

- Backend parent/health slice: `.venv/bin/pytest tests/test_sprint59_multi_child.py tests/test_parents_materials.py tests/test_parent_dashboard.py tests/test_health.py -q` -> `43 passed, 56 warnings`.

### Manual test notes for Igor

- Parent UI can now be tested with `parent-e2e@example.com`; it should show linked child `Student E2E` and open `/parent/dashboard/20`.
- Historical pending self-link rows are intentionally not deleted; they are harmless after the service fix and retained for auditability unless a separate cleanup is requested.

## 2026-08-12 19:30 MSK — Manual QA status update after user walkthrough

Scope: incorporated Igor's latest manual testing results and fixed the actionable blockers found in Parent/Admin surfaces.

### Manual testing status

| # | Area | Status | Notes |
|---:|---|---|---|
| 0 | Быстрый Smoke | OK | Manual pass confirmed. |
| 1 | Student Flow | OK | Manual pass confirmed. |
| 2 | Mobile Student Flow | Not run | Deferred; no result claimed. |
| 3 | Parent Flow | Fixed follow-ups | Parent console buttons compacted; parent console now prefers a linked child with real attempts so `Сводка` is not stuck on an empty E2E child; parent dashboard top spacing reduced. |
| 4 | Teacher Flow | OK | Manual pass confirmed. |
| 5 | Admin Flow | Fixed follow-up | Prometheus scrape was healthy; UI realtime issue was WebSocket auth using the `cookie` sentinel as a JWT. Backend WS now falls back to httpOnly access cookie. |
| 6 | Multi-Subject Smoke | OK | Manual pass confirmed. |
| 7 | Visual / UX Sweep | Desktop OK | Manual desktop sweep confirmed after final dark Prism palette pass. |

### Fixes applied

- `/parents`: child cards no longer use full-width long dashboard buttons; action is compact (`Дашборд`) and aligned to the right on desktop.
- `/parents`: overview data is prefetched for linked children and the default selection prefers the child with activity (`total_attempts > 0`) over a persisted empty E2E selection.
- `/parents`: child list now shows attempt count next to linked date when overview data is available.
- `/parent/dashboard/[studentId]`: reduced top spacing in hero/KPI/recommendation blocks to make the dashboard more compact above the fold.
- `/admin` Realtime: production Prometheus itself was healthy and scraping `backend:8000/metrics`; the UI showed disconnected because WebSocket auth expected a JWT query token while frontend cookie auth sends the sentinel `cookie`. WS now reads `ai_tutor_access` from the WebSocket handshake when token is omitted or equals `cookie`.

### Verification before deploy

- Frontend typecheck: `npm run typecheck` passed.
- Frontend build: `npm run build` passed.
- Backend slice: `.venv/bin/pytest tests/test_parent_dashboard.py tests/test_health.py -q` -> `21 passed, 23 warnings`.
- Production Prometheus health checked read-only before code change:
  - `prometheus /-/healthy` returned healthy;
  - internal scrape `http://backend:8000/metrics` returned Prometheus text metrics.

