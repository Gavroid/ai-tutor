# AI-Tutor Current Handoff — MVP pilot manual QA ready

Date: 2026-08-12 09:39 MSK
Workspace: `/root/workspace/ai-tutor`
Branch: `mvp-rescue`
Remote: `git@github.com:Gavroid/ai-tutor.git`
Production: `https://school.431a.ru` / LAN `https://192.168.1.86`
Prod SSH: `root@192.168.1.86` with key `/root/.ssh/id_ed25519_kirill_ai`
Current deployed app commit: `8674981`
Current prod marker: `8674981`
Note: this handoff may be followed by a docs-only commit that does not change production runtime.

> Prompt for the next agent/window: **Continue from this handoff. Do not ask Igor for context unless a command is blocked. Do not expose secrets. Verify every claim with commands. The remaining work is manual QA follow-up and bug fixing, not broad redesign.**

## 0. Hard Rules

- Work in `/root/workspace/ai-tutor` unless explicitly told otherwise.
- Do not print secrets, token values, private keys, `.env` contents, SMB credentials, or login response JWTs.
- Nightscout is unrelated here and remains read-only.
- Do not resume visual design work unless Igor reports a concrete UI bug.
- If a check fails, debug root cause before patching.
- Use evidence before saying something is done.
- Do not mutate production DB unless explicitly needed and backed up.

## 1. Skills To Load First

Load these skills before continuing:

- `ai-tutor-deploy`
- `ai-tutor-mvp-stage-execution`
- `verification-before-completion`
- `systematic-debugging` if a check fails
- `test-driven-development` if changing behavior/tests
- `webapp-testing` if doing browser audits

## 2. Access Map

### Local Repo

```bash
cd /root/workspace/ai-tutor
git status --short --branch
git log --oneline -12
```

Expected at handoff time:

```text
HEAD 8674981
tracked working tree clean
only this handoff file may be untracked/changed until committed
```

### Production SSH

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 'hostname && cat /opt/ai-tutor/.mvp-rescue-commit'
```

Expected marker:

```text
8674981
```

### Production Health

```bash
curl -sk -w '\nHTTP=%{http_code}\n' https://192.168.1.86/ready
curl -sk -w '\nHTTP=%{http_code}\n' https://192.168.1.86/health
```

Expected:

```text
/ready  -> {"status":"ready"}, HTTP=200
/health -> {"status":"ok", ... "env":"production" ...}, HTTP=200
```

### Docker Status

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
  'cd /opt/ai-tutor/deploy && docker compose ps'
```

Expected:

- backend healthy;
- db healthy;
- frontend healthy;
- redis healthy;
- proxy running;
- prometheus healthy;
- grafana running.

### Production DB Access

Use the db container, not host psql:

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
  'cd /opt/ai-tutor/deploy && docker compose exec -T db psql -U tutor -d tutor'
```

Safe read-only examples:

```sql
select id,email,display_name,role,is_active from users where role in ('parent','student') order by role,email;
select * from parent_student_links order by id;
```

### Backup / Offsite

Authoritative cron:

```text
/etc/cron.d/ai-tutor-backup
/etc/cron.d/ai-tutor-backup-verify
```

Logs:

```text
/var/log/ai-tutor-backup.log
/var/log/ai-tutor-backup-verify.log
/var/log/ai-tutor-restore-drill.log
```

Do not print SMB credentials.

## 3. Current State

### Design / UI

Status: complete.

Do not continue design polish unless Igor reports a concrete bug.

Final design state:

- single fixed dark theme;
- no theme toggle;
- mobile Split Coach tabs;
- desktop three-panel lesson layout;
- `/subjects`, `/subjects/[id]`, `/topics/[id]`, `/register`, `/forgot-password`, `/diagnostic`, `/link-parent`, `/parents` restyled to dark Prism/Split style;
- pause menu changed to 5 / 15 / 30 minutes;
- action buttons idle dark/outlined and glow only on hover/focus;
- skip-link removed;
- chat composer fixed.

Old `design-renders/` concept artifacts were moved out of git noise to:

```text
.hermes/artifacts/design-renders-2026-08-11
```

That directory is ignored by `.gitignore` through `.hermes/`.

### Stage 5 Parent Flow

Status: complete for MVP.

Relevant files:

- `apps/frontend/app/parents/page.tsx`
- `apps/frontend/e2e/parent-console.spec.ts`
- `docs/STAGE-5-PARENT-FLOW-AUDIT-REPORT.md`

Verified earlier:

- `/parents` HTTP 200;
- no old white/slate classes;
- no white panels;
- no horizontal overflow desktop/mobile;
- parent invite endpoint HTTP 200;
- parent-console E2E passes.

Known limitation:

- `parent-e2e@example.com` is linked to `student-e2e@example.com` for manual QA;
- `/parent/dashboard/20` is expected to load for that account;
- pre-mutation backup exists at `/opt/ai-tutor/deploy/backup/_manual/qa-parent-link-pre-20260811.sql`;
- historical `parent-e2e -> parent-e2e` rows remain pending and are ignored by service logic.

### Stage 6 Reliability / Ops

Status: complete.

Key commits:

- `7f17646 fix: trust proxy network for auth rate limits`
- `6f74300 fix: align ops preflight with container-visible paths`
- `8a14fac fix: harden restore drill scheduling and readiness`
- `0dd3779 docs: close stage 6 ops hardening report`

Current report:

```text
docs/STAGE-6-RELIABILITY-OPS-MVP-REPORT.md
```

Verified current production facts:

- `/ready` HTTP 200;
- `/health` HTTP 200;
- `/api/v1/admin/ops/status` returns `ok=true`;
- ops endpoint sees DB, Redis, backup paths, and commit marker;
- current marker: `8674981`;
- disk after cleanup: about `49G 29G 18G 62% /`;
- restore drill passed on `2026-08-11T15:12:01+00:00`:
  - backup `db-20260811T030001Z.sql.gz`;
  - size `12715463` bytes;
  - table count `32`;
  - user count `14`.

Restore drill fixes:

- first-Monday cron guard;
- `flock -n` non-overlap;
- per-run temp dir/log;
- trap cleanup;
- target DB readiness probe via `psql SELECT 1`.

### Stage 7 Multi-Subject Expansion MVP

Status: complete for MVP-preview expansion.

Key commit:

```text
d764115 test: cover multi-subject readiness
```

Current report:

```text
docs/STAGE-7-MULTI-SUBJECT-EXPANSION-MVP-REPORT.md
```

What Stage 7 means now:

- all 12 seeded subjects are visible;
- only `Математика (6 класс - повторение пройденного материала)` is `mvp_ready`;
- all other seeded subjects are `preview`;
- preview subjects are navigation-visible only and must not imply RAG/source readiness.

New regression:

```text
apps/frontend/e2e/multi-subject-readiness.spec.ts
```

Also fixed in `d764115`:

- dangling raw `$$` display-math markers in student-facing AI output are stripped by sanitizer;
- regression added in `apps/backend/tests/test_ai_output_contract.py`.

## 4. Fresh Verification Evidence

Latest local gates run after `d764115`:

```bash
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest tests/test_ai_output_contract.py tests/test_subjects.py -q
# 57 passed

cd /root/workspace/ai-tutor/apps/frontend
npm run typecheck
# tsc --noEmit passed

BASE_URL=https://192.168.1.86 npx playwright test e2e/multi-subject-readiness.spec.ts e2e/mvp-student-flow.spec.ts --reporter=line --workers=1
# 3 passed
```

Latest production smoke after deploy:

```text
prod marker: d764115
/ready HTTP=200
/health HTTP=200
ops status ok=true, database_ok=true, redis_ok=true, commit_marker.ok=true, commit=8674981
```

## 5. Remaining Work

There is no known blocking code/ops task left from the handoff plan.

What remains is manual QA and follow-up bug fixing:

1. Run manual student flow on phone and desktop:
   - login;
   - `/subjects`;
   - prepared math subject;
   - topic lesson;
   - explain;
   - practice;
   - wrong answer;
   - correct answer;
   - chat;
   - clear/reset;
   - pause menu.
2. Run manual parent flow:
   - `/parents`;
   - invite/link parent if needed;
   - dashboard summary/recommendations/privacy note.
3. Run teacher/admin smoke:
   - `/teacher/topics`;
   - one topic detail;
   - followups/fallbacks/status save only on safe test topic or revert immediately;
   - `/api/v1/admin/ops/status`.
4. Record manual findings in:
   - `docs/pilot-topic-matrix.md` for topic-specific results;
   - `docs/pilot-walkthrough-notes.md` if more than 3 issues are found.
5. Fix only blockers found during manual QA.

## 6. Useful Manual QA Guide

Current manual test guide:

```text
docs/MVP-MANUAL-TESTING-HANDOFF-STAGES-4-7.md
```

Note: this file was refreshed after Stage 6 visibility fixes; backup/marker checks are now expected to be visible from ops/status.

## 7. Known Test/Runtime Pitfalls

- Prod login rate-limit can be consumed by repeated E2E runs from the same origin IP. If E2E login gets `429`, inspect Redis first:

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
  'cd /opt/ai-tutor/deploy && docker compose exec -T redis redis-cli --scan --pattern "login_rl:*"'
```

- If clearly blocked only by the local E2E-origin bucket, clear only that bucket, not all production rate limits. In the last session the E2E-origin key was `login_rl:192.168.1.35:*`.
- Browser/service-worker self-signed certificate warnings can appear in Playwright console and are not by themselves a product failure.
- Old duplicate restore-drill lines remain in historical logs, but new script no longer double-writes.

## 8. Files To Know

Frontend:

- `apps/frontend/app/subjects/page.tsx`
- `apps/frontend/app/subjects/[id]/page.tsx`
- `apps/frontend/app/topics/[id]/page.tsx`
- `apps/frontend/app/parents/page.tsx`
- `apps/frontend/e2e/mvp-student-flow.spec.ts`
- `apps/frontend/e2e/multi-subject-readiness.spec.ts`
- `apps/frontend/e2e/parent-console.spec.ts`

Backend/ops:

- `apps/backend/app/ai/sanitize.py`
- `apps/backend/app/admin/router.py`
- `apps/backend/app/subjects/router.py`
- `apps/backend/tests/test_ai_output_contract.py`
- `apps/backend/tests/test_stage6_ops_status.py`
- `apps/backend/tests/test_subjects.py`
- `deploy/docker-compose.yml`
- `scripts/restore_drill.sh`
- `deploy/monitoring/cron/ai-tutor-backup-verify.cron`

Docs:

- `docs/STAGE-5-PARENT-FLOW-AUDIT-REPORT.md`
- `docs/STAGE-6-RELIABILITY-OPS-MVP-REPORT.md`
- `docs/STAGE-7-MULTI-SUBJECT-EXPANSION-MVP-REPORT.md`
- `docs/MVP-MANUAL-TESTING-HANDOFF-STAGES-4-7.md`
- `docs/pilot-topic-matrix.md`
- `docs/PILOT_PLAN.md`

## 9. What Not To Do Next

- Do not resume visual design work unless Igor reports a concrete bug.
- Do not mark preview subjects as RAG-ready without real materials and topic-scoped verification.
- Do not mutate production DB during smoke unless explicitly needed and backed up.
- Do not reveal credentials.
- Do not treat old handoff notes that mention `7f17646` / `8a14fac` as current; this file supersedes them.
