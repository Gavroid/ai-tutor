# AI-Tutor — Handoff Prompt For Manual QA, Bug Fixing, And Development Continuation

Date: 2026-08-11 21:31 MSK
Workspace: `/root/workspace/ai-tutor`
Branch: `mvp-rescue`
Current HEAD: `351c22f`
Production marker: `351c22f`
Production URL: `https://school.431a.ru`
LAN URL: `https://192.168.1.86`
Prod SSH: `root@192.168.1.86` with key `/root/.ssh/id_ed25519_kirill_ai`
Remote: `git@github.com:Gavroid/ai-tutor.git`

## Copy-Paste Prompt For The Next Context Window

```text
Open and follow `/root/workspace/ai-tutor/docs/HANDOFF-QA-BUGFIX-NEXT-CONTEXT-2026-08-11.md` from top to bottom.

Goal: run the remaining manual QA / smoke testing for the AI-Tutor MVP pilot, record findings, and fix only real blockers or concrete bugs found during testing. Do not ask me for context unless a command is blocked. Do not expose secrets. Verify every claim with commands.

Current state:
- Workspace: /root/workspace/ai-tutor
- Branch: mvp-rescue
- Current code HEAD: 351c22f
- Production marker: 351c22f
- Production: https://school.431a.ru / LAN https://192.168.1.86
- SSH: root@192.168.1.86 using /root/.ssh/id_ed25519_kirill_ai

Hard rules:
- No broad redesign. Design is considered finished; touch UI only for concrete bugs.
- Nightscout is unrelated and read-only.
- Do not print secrets, private keys, JWTs, `.env`, SMB credentials, or token values.
- Do not mutate production DB unless explicitly needed, backed up, and narrowly scoped.
- If a check fails, debug root cause before patching.
- Use TDD for behavior/code changes: add/adjust failing test first, then fix, then verify.
- Before saying “done”, run fresh verification commands and report exact outputs.

Start by running:
cd /root/workspace/ai-tutor
git status --short --branch
git log --oneline -8
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 'cat /opt/ai-tutor/.mvp-rescue-commit; cd /opt/ai-tutor/deploy && docker compose ps'

Then execute the QA plan in the handoff file:
1. Operator preflight.
2. Student MVP flow on desktop and mobile viewport.
3. Parent flow.
4. Teacher/admin smoke.
5. Multi-subject readiness smoke.
6. Record findings in docs.
7. Fix only bugs found, with tests and deploy verification.
```

## Current Proven State

Latest committed work:

```text
351c22f fix: restrict public docs and metrics endpoints
9dffcda docs: refresh mvp manual qa handoff
d764115 test: cover multi-subject readiness
0dd3779 docs: close stage 6 ops hardening report
8a14fac fix: harden restore drill scheduling and readiness
6f74300 fix: align ops preflight with container-visible paths
7f17646 fix: trust proxy network for auth rate limits
e549ceb test: add parent console audit coverage
```

Production at handoff time:

```text
PROD_MARKER=351c22f
/ready  -> {"status":"ready"}, HTTP 200
/health -> {"status":"ok", "env":"production", ...}, HTTP 200
backend healthy
db healthy
frontend healthy
redis healthy
prometheus healthy
proxy running
grafana running
```

Security hardening completed:

- `/docs` -> 404 at edge.
- `/openapi.json` -> 404 at edge.
- `/graphql` -> 404 at edge.
- `/metrics` -> 404 at edge.
- Prometheus still scrapes `backend:8000/metrics` directly inside Docker.

Last broad automated verification before this handoff:

```bash
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest tests/test_sprint69_budget_metrics.py tests/test_sprint6_cron_env.py::test_nginx_blocks_public_docs_schema_and_metrics_at_edge tests/test_health.py tests/test_ai_output_contract.py tests/test_subjects.py -q
# 72 passed

cd /root/workspace/ai-tutor/apps/frontend
npm run typecheck
# tsc --noEmit passed

BASE_URL=https://192.168.1.86 npx playwright test e2e/multi-subject-readiness.spec.ts e2e/mvp-student-flow.spec.ts --reporter=line --workers=1
# 3 passed
```

## What Is Already Done

### Design / UI

Status: complete.

Do not continue design polish unless a concrete bug appears.

Final state:

- one fixed dark Prism theme;
- no theme toggle;
- mobile Split Coach tabs `Чат / Урок / Практика`;
- desktop three-panel lesson layout;
- `/subjects`, `/subjects/[id]`, `/topics/[id]`, `/register`, `/forgot-password`, `/diagnostic`, `/link-parent`, `/parents` restyled;
- pause menu: 5 / 15 / 30 minutes;
- action buttons are dark/outlined at rest and glow on hover/focus;
- visible skip link removed;
- chat composer fixed.

Old concept screenshots are archived outside git:

```text
/root/workspace/ai-tutor/.hermes/artifacts/design-renders-2026-08-11
```

### Student MVP Flow

Status: automated green, needs human manual QA.

Automated coverage:

```text
apps/frontend/e2e/mvp-student-flow.spec.ts
```

Covers:

- login;
- `/subjects`;
- `/subjects/3`;
- first topic;
- explain;
- follow-up buttons;
- practice generation;
- wrong answer;
- corrected answer;
- chat;
- clear/reset;
- budget/429 user-facing message.

### Parent Flow / Stage 5

Status: complete for MVP, needs manual QA.

Files:

```text
apps/frontend/app/parents/page.tsx
apps/frontend/e2e/parent-console.spec.ts
docs/STAGE-5-PARENT-FLOW-AUDIT-REPORT.md
```

Known limitation:

- `parent-e2e@example.com` may have no linked child in production.
- A linked Stage 5 pair exists from prior audit, but if UI login credentials are unknown, verify via service/API or create a disposable test link only if needed and explicitly documented.

### Stage 6 Ops / Reliability

Status: complete.

Files/reports:

```text
docs/STAGE-6-RELIABILITY-OPS-MVP-REPORT.md
apps/backend/app/admin/router.py
deploy/docker-compose.yml
scripts/restore_drill.sh
deploy/monitoring/cron/ai-tutor-backup-verify.cron
```

Important facts:

- `/api/v1/admin/ops/status` is admin-only and returns DB/Redis/uploads/registry/backup/marker checks.
- backup cron/script and commit marker are visible from backend container.
- disk was cleaned to about 62% usage.
- restore drill passed on latest manual run:
  - backup `db-20260811T030001Z.sql.gz`;
  - `32` tables;
  - `14` users.

### Stage 7 Multi-Subject Expansion MVP

Status: complete for MVP-preview expansion.

Files:

```text
apps/frontend/e2e/multi-subject-readiness.spec.ts
docs/STAGE-7-MULTI-SUBJECT-EXPANSION-MVP-REPORT.md
```

Meaning:

- all seeded subjects are visible;
- only `Математика (6 класс - повторение пройденного материала)` is MVP-ready;
- non-math/unprepared subjects are preview only;
- no fake RAG readiness or misleading source claims for preview subjects.

## Access And Safe Commands

### Repo Status

```bash
cd /root/workspace/ai-tutor
git status --short --branch
git log --oneline -12
```

Expected at handoff time:

```text
## mvp-rescue
HEAD includes 351c22f
```

### Production Health

```bash
curl -sk -w '\nHTTP=%{http_code}\n' https://192.168.1.86/ready
curl -sk -w '\nHTTP=%{http_code}\n' https://192.168.1.86/health
```

### Production Compose

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
  'cd /opt/ai-tutor/deploy && docker compose ps'
```

### Admin Ops Status Without Printing JWT

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 'python3 - <<'"'"'PY'"'"'
import json, subprocess, sys
login = subprocess.run([
    "curl", "-sk", "-X", "POST", "https://localhost/api/v1/auth/login",
    "-H", "Content-Type: application/json",
    "-d", json.dumps({"email":"admin@example.com","password":"Kirill2026!"}),
], capture_output=True, text=True)
token = json.loads(login.stdout).get("access_token")
if not token:
    print("admin_login_failed", login.stdout[:250])
    sys.exit(1)
status = subprocess.run([
    "curl", "-sk", "https://localhost/api/v1/admin/ops/status",
    "-H", f"Authorization: Bearer {token}",
], capture_output=True, text=True)
body = json.loads(status.stdout)
checks = body["checks"]
print(json.dumps({
    "ok": body.get("ok"),
    "database_ok": checks["database"].get("ok"),
    "redis_ok": checks["redis"].get("ok"),
    "uploads_ok": checks["uploads"].get("ok"),
    "teacher_registry_ok": checks["teacher_registry"].get("ok"),
    "backup": checks["backup"],
    "commit_marker": checks["commit_marker"],
}, ensure_ascii=False, sort_keys=True))
PY'
```

### Security Endpoint Check

Expected all 404 at edge:

```bash
for url in \
  https://192.168.1.86/docs \
  https://192.168.1.86/openapi.json \
  https://192.168.1.86/graphql \
  https://192.168.1.86/metrics \
  https://school.431a.ru/docs \
  https://school.431a.ru/openapi.json \
  https://school.431a.ru/graphql \
  https://school.431a.ru/metrics; do
  printf '%s ' "$url"
  curl -sk -o /dev/null -w 'HTTP=%{http_code}\n' "$url"
done
```

Prometheus internal scrape should still work:

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
  'cd /opt/ai-tutor/deploy && docker compose exec -T prometheus wget -qO- http://backend:8000/metrics | head -5'
```

### Backup / Restore

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
  'tail -80 /var/log/ai-tutor-backup.log; echo --- verify ---; tail -80 /var/log/ai-tutor-backup-verify.log; echo --- restore ---; tail -80 /var/log/ai-tutor-restore-drill.log'
```

Do not print SMB credentials.

### Production DB Read-Only Examples

Use db container, not host psql:

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
  'cd /opt/ai-tutor/deploy && docker compose exec -T db psql -U tutor -d tutor -c "select id,email,display_name,role,is_active from users where role in ('"'"'parent'"'"','"'"'student'"'"') order by role,email;"'
```

## Manual QA Plan

### 1. Operator Preflight

Run and record:

- repo status clean;
- prod marker equals expected commit;
- `/ready` 200 ready;
- `/health` 200 ok;
- docker compose services healthy/running;
- admin ops status `ok=true`;
- edge docs/schema/metrics 404;
- Prometheus internal scrape works;
- latest restore drill log shows passed.

If any fail: debug root cause before patching.

### 2. Student MVP Flow — Desktop

Use `kirill@example.com` only through normal UI; do not print tokens.

Manual steps:

1. Open `https://192.168.1.86/login` or `https://school.431a.ru/login`.
2. Login as student.
3. Open `/subjects`.
4. Open `Математика (6 класс - повторение пройденного материала)`.
5. Open a P0 topic, preferably one already in the matrix: `187`, `188`, `189`, `196`, or `225`.
6. Click `Объяснить`.
7. Verify no raw artefacts:
   - no `<think>`;
   - no `&lt;think&gt;`;
   - no fenced JSON;
   - no `correct_answer`;
   - no raw `$$`, `\frac`, `\text`.
8. Verify follow-up buttons are visible where expected.
9. Click `Практика`.
10. Submit a wrong answer; verify useful “Есть ошибка” feedback.
11. Submit correct answer; verify “Верно!” feedback.
12. Send a chat message; verify assistant responds without `AI временно недоступен` or `WS закрыт` unless budget is actually exceeded.
13. Click clear/reset; verify exercise, feedback, chat, and input reset.
14. Test pause menu: 5 / 15 / 30 minutes.

Record findings in `docs/pilot-walkthrough-notes.md` if there are issues.

### 3. Student MVP Flow — Mobile Viewport

Use Playwright or browser device mode.

Check:

- tabs `Чат / Урок / Практика` are usable;
- no horizontal overflow;
- lesson/explain/practice/chat are reachable;
- no copy buttons in lesson/chat/practice areas;
- pause menu is usable;
- clear confirmation is readable.

Suggested Playwright inspection command if needed:

```bash
cd /root/workspace/ai-tutor/apps/frontend
BASE_URL=https://192.168.1.86 npx playwright test e2e/mvp-student-flow.spec.ts --project=chromium --reporter=line --workers=1
```

### 4. Parent Flow

Open:

- `/parents`
- `/parent/dashboard/{studentId}` if a linked child exists.

Check:

- parent console loads;
- recommendations are understandable;
- privacy note is visible;
- parent sees aggregate progress, not raw AI chat;
- no old white/slate UI blocks;
- no mobile/desktop overflow.

If `parent-e2e@example.com` has no linked child, do not silently create production data. Either use an existing linked Stage 5 pair from DB if credentials are known, or document that manual parent dashboard UI requires a test linked account.

### 5. Teacher/Admin Smoke

Teacher/admin smoke should be narrow.

Open:

- `/teacher/topics`
- one safe topic detail page;
- `/admin`
- `/api/v1/admin/ops/status`.

Check:

- readiness table loads;
- topic detail editor loads;
- followups/fallbacks/status forms render;
- do not save destructive changes unless using a clearly disposable test topic or immediately revert.

### 6. Multi-Subject Readiness Smoke

Open:

- `/subjects`;
- prepared math subject;
- one preview subject, e.g. Algebra.

Check:

- math repeat subject shows `MVP-ready`;
- preview subjects show `Preview`;
- preview detail page warns materials/RAG are not confirmed;
- preview subject does not imply RAG/source readiness.

Automated check:

```bash
cd /root/workspace/ai-tutor/apps/frontend
BASE_URL=https://192.168.1.86 npx playwright test e2e/multi-subject-readiness.spec.ts --reporter=line --workers=1
```

## If A Bug Is Found

Follow this loop:

1. Reproduce with a tight command or Playwright test.
2. Add/adjust regression test first and confirm RED.
3. Patch minimal code/config.
4. Run targeted tests.
5. Run relevant broader gate:
   - backend behavior -> targeted backend tests plus affected suite;
   - frontend behavior -> `npm run typecheck` and affected E2E;
   - deploy/config -> prod smoke and rollback-safe checks.
6. Commit with concise message.
7. Deploy only affected paths.
8. Verify production with real commands.
9. Update docs/matrix if readiness changes.

Do not fix unrelated design preferences or start new feature work during QA.

## Deploy Patterns

### Backend Code Change

```bash
cd /root/workspace/ai-tutor
COMMIT=$(git rev-parse --short HEAD)
tar -cf - apps/backend/app/<changed>.py apps/backend/tests/<changed_test>.py | \
  ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 'tar -xf - -C /opt/ai-tutor/'
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
  "set -e; cd /opt/ai-tutor; echo $COMMIT > .mvp-rescue-commit; cd deploy; docker compose build backend; docker compose up -d backend; docker compose ps; curl -sk -w '\nHTTP=%{http_code}\n' https://localhost/ready"
```

### Frontend Code Change

Use existing project deploy pattern; verify `npm run typecheck`, affected E2E, then rebuild/restart frontend on prod. Do not deploy visual churn without a concrete bug.

### Nginx/Deploy Config Change

```bash
cd /root/workspace/ai-tutor
COMMIT=$(git rev-parse --short HEAD)
tar -cf - deploy/nginx/nginx.conf deploy/docker-compose.yml | \
  ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 'tar -xf - -C /opt/ai-tutor/'
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
  "set -e; cd /opt/ai-tutor; echo $COMMIT > .mvp-rescue-commit; cd deploy; docker compose up -d --force-recreate proxy; docker compose exec -T proxy nginx -t; curl -sk -w '\nHTTP=%{http_code}\n' https://localhost/ready"
```

Note: during the last nginx deploy, self-signed cert files had to be regenerated on prod because the proxy mount was empty:

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
  'cd /opt/ai-tutor && bash deploy/ssl/generate-self-signed.sh 192.168.1.86'
```

## Current Known Pitfalls

- Repeated E2E login runs can hit prod login rate-limit from the same E2E origin. Inspect Redis first; only clear the local E2E-origin bucket if clearly blocked.

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
  'cd /opt/ai-tutor/deploy && docker compose exec -T redis redis-cli --scan --pattern "login_rl:*"'
```

- Browser console may show self-signed service worker certificate warning in Playwright; this is not automatically a product bug.
- `/docs`, `/openapi.json`, `/graphql`, `/metrics` are intentionally 404 at edge after `351c22f`.
- Prometheus must scrape `backend:8000/metrics` directly inside Docker, not via nginx edge.
- Old duplicate restore-drill lines remain in historical logs, but current script no longer double-writes.

## Documentation To Update During QA

Use these files, depending on finding:

```text
docs/pilot-topic-matrix.md                 # topic-specific Manual QA status
docs/pilot-walkthrough-notes.md            # create/update if multiple manual findings
docs/MVP-MANUAL-TESTING-HANDOFF-STAGES-4-7.md
docs/HANDOFF-QA-BUGFIX-NEXT-CONTEXT-2026-08-11.md
```

If a bug changes stage readiness, update the relevant report:

```text
docs/STAGE-5-PARENT-FLOW-AUDIT-REPORT.md
docs/STAGE-6-RELIABILITY-OPS-MVP-REPORT.md
docs/STAGE-7-MULTI-SUBJECT-EXPANSION-MVP-REPORT.md
```

## Definition Of Done For The Next Agent

The next agent can report “manual QA pass / bugfix complete” only after:

- exact manual or automated steps are listed;
- every failed check has a root-cause note;
- every code/config fix has a regression test or a justified smoke test;
- local targeted gates pass;
- production smoke passes if deployed;
- `git status --short --branch` is clean except intentionally ignored local artifacts;
- docs/matrix are updated if QA status changed.
