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
