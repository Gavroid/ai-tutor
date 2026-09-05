# AI-Tutor Next Session Handoff — 2026-08-17

## Purpose

Файл для быстрой передачи новой сессии чата. Используй его, чтобы продолжить AI-Tutor MVP без повторного сбора контекста.

## Current Workspace

```text
Workspace: /root/workspace/ai-tutor
Branch: mvp-rescue
Latest completed commit: b4512f8 docs: close next stage 06 parent evidence
Next stage to execute: Stage 07 — Teacher Content QA Evidence Pass
Main plan: docs/NEXT-3-MONTH-AUTONOMOUS-PLAN-2026-08-16.md
```

## Production State At Handoff

```text
Checked at: 2026-08-17 15:08 MSK
Production URL: https://school.431a.ru
LAN URL: https://192.168.1.86
Production marker: 6e698a0
/ready: HTTP 200
/health: HTTP 200
Services: backend/frontend/db/redis/prometheus healthy; grafana/proxy running
```

Production is still in **targeted deploy mode**. Do not run broad destructive release deploy or marker advancement until release hygiene is solved.

## Access Notes

SSH access to production is available from this environment with the existing configured key path:

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes -o ConnectTimeout=8 root@192.168.1.86 '<command>'
```

Do not print private key contents, tokens, passwords, `.env`, JWTs, Bearer values, or SMB credentials.

Health check command:

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes -o ConnectTimeout=8 root@192.168.1.86 '
  printf "marker="; cat /opt/ai-tutor/.mvp-rescue-commit
  curl -sk -w "\nREADY_HTTP=%{http_code}\n" https://localhost/ready
  curl -sk -w "\nHEALTH_HTTP=%{http_code}\n" https://localhost/health
  cd /opt/ai-tutor/deploy && docker compose ps --format "table {{.Name}}\t{{.State}}\t{{.Status}}"
'
```

Backup/offsite gate before any production deploy or production data mutation:

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes -o ConnectTimeout=8 root@192.168.1.86 '
  cd /opt/ai-tutor/deploy/backup
  ./backup.sh
  ./ai-tutor-backup-offsite.sh
'
```

Proceed only if offsite verification reports `OFFSITE OK`.

## Hard Rules

1. Do not ask Igor for context or decisions; inspect repo/docs/git/prod yourself.
2. Do not expose secrets, tokens, `.env`, private keys, JWTs, Bearer values, passwords, or SMB credentials.
3. Do not modify Nightscout or external medical systems.
4. Before any production deploy or production data mutation, run production backup + offsite verification.
5. Preserve dark Prism/Split UI style.
6. Parent privacy boundary is mandatory: aggregate progress only, no raw AI chat exposure.
7. Student-facing AI output must never show raw JSON, `<think>`, broken markdown tables, broken math markers, hidden answers, or unreadable mobile formatting.
8. Algebra/Geometry remain `preview` until verified source/RAG coverage exists.
9. Every stage ends with tests, docs/evidence, and commit if files changed.
10. Production tree is dirty/on `master`; avoid broad destructive deploy and marker advancement. Use targeted safe deploys only if required.

## Current Subject Readiness

```text
Math subject_id=3: mvp_ready; route 42/42; sources/RAG 42/42; practice 42/42
Algebra subject_id=4: preview; route 19/19; sources/RAG 0/19; practice 19/19
Geometry subject_id=5: preview; route 13/13; sources/RAG 0/13; practice 13/13
```

## Completed Next-Plan Stages

Main plan: `docs/NEXT-3-MONTH-AUTONOMOUS-PLAN-2026-08-16.md`.

Completed:

1. **Stage 01 — Release Hygiene And Marker Recovery Plan**  
   Report: `docs/NEXT-STAGE-01-RELEASE-HYGIENE-REPORT-2026-08-16.md`  
   Runbook: `docs/NEXT-RELEASE-MARKER-ADVANCEMENT-RUNBOOK-2026-08-16.md`  
   Commit: `70e5567`

2. **Stage 02 — Math Manual Pilot Intake Framework**  
   Template: `docs/MATH-PILOT-FEEDBACK-INTAKE-2026-08-16.md`  
   Commit: `417190b`

3. **Stage 03 — Math Student Session Evidence Pass 1**  
   Report: `docs/NEXT-STAGE-03-MATH-STUDENT-EVIDENCE-PASS-1-2026-08-16.md`  
   Commit: `b7991a5`

4. **Stage 04 — Math Explanation Quality Sweep**  
   Report: `docs/NEXT-STAGE-04-MATH-EXPLANATION-QUALITY-SWEEP-2026-08-16.md`  
   Commit: `af5fc71`

5. **Stage 05 — Math Practice Variant Rotation Audit**  
   Report: `docs/NEXT-STAGE-05-MATH-PRACTICE-ROTATION-AUDIT-2026-08-16.md`  
   Commit: `172588f`  
   Important: production registry for topics `187/190/203` was fixed after backup/offsite `manifest-20260816T135558Z.md5`; repeat generation now gives 3/3 unique questions for sampled topics.

6. **Stage 06 — Parent Report Manual Evidence Pass**  
   Report: `docs/NEXT-STAGE-06-PARENT-REPORT-EVIDENCE-2026-08-16.md`  
   Commit: `b4512f8`  
   Backend parent tests: `18 passed`; parent dashboard E2E: `1 passed`. Production had no active parent-child link, so no synthetic production data was created.

## Next Stage To Start

### Stage 07 — Teacher Content QA Evidence Pass

Plan requirements:

- Run teacher flow: analytics → readiness matrix → topic detail → material QA status.
- Confirm audit logs capture QA status transitions.
- Verify blocked/needs-review material cannot be published.
- Improve copy/empty states if teacher workflow is unclear.

Verification:

- Teacher workflow tests.
- Teacher review Playwright smoke.
- Admin audit filter for QA transition.

Deliverable:

- `docs/NEXT-STAGE-07-TEACHER-QA-EVIDENCE-YYYY-MM-DD.md`

## Likely Files For Stage 07

Backend:

- `apps/backend/app/teacher/router.py`
- `apps/backend/app/teacher/service.py`
- `apps/backend/app/teacher/schemas.py`
- `apps/backend/app/teacher/content_registry.py`
- `apps/backend/tests/test_teacher.py`
- `apps/backend/app/admin/router.py`
- `apps/backend/app/admin/service.py`

Frontend:

- `apps/frontend/app/teacher/page.tsx`
- `apps/frontend/app/teacher/topics/page.tsx`
- `apps/frontend/app/teacher/topics/[id]/page.tsx`
- `apps/frontend/app/teacher/materials/[id]/page.tsx`
- `apps/frontend/e2e/teacher-review-v2.spec.ts`
- `apps/frontend/lib/api.ts`
- `apps/frontend/types/index.ts`

## Known Production Hygiene Issue

Production git tree is dirty and on `master`, while local work is on `mvp-rescue`. Because of this:

- do not run broad `rsync --delete`;
- do not advance `.mvp-rescue-commit` unless release marker workflow is truly restored;
- use targeted sync/build only when production mutation is required;
- document marker unchanged in every production stage report unless marker workflow was actually run.

## Current Local Working Tree Note

Known untracked artifacts remain outside staged plan work and should not be deleted unless explicitly requested:

```text
docs/AI-Tutor-Stakeholder-Presentation-2026-08-14.pptx
docs/AI-Tutor-Stakeholder-Presentation-PANDOC-2026-08-14.pptx
docs/AI-Tutor-Stakeholder-Presentation-SAFE-2026-08-14.pptx
tmp/
```

## Useful Verification Commands

Backend teacher gate:

```bash
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest tests/test_teacher.py tests/test_health.py -q
```

Frontend teacher smoke:

```bash
cd /root/workspace/ai-tutor/apps/frontend
BASE_URL=https://192.168.1.86 npx playwright test e2e/teacher-review-v2.spec.ts --project=chromium
```

Cross-role smoke if a stage affects shared flows:

```bash
cd /root/workspace/ai-tutor/apps/frontend
BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts --project=chromium
```

## Copy-Paste Prompt For New Chat Session

```text
[Workspace::v1: /root/workspace]
Continue AI-Tutor MVP development autonomously.

Workspace: /root/workspace/ai-tutor
Branch: mvp-rescue
Main plan: /root/workspace/ai-tutor/docs/NEXT-3-MONTH-AUTONOMOUS-PLAN-2026-08-16.md
Handoff: /root/workspace/ai-tutor/docs/HANDOFF-NEXT-SESSION-2026-08-17.md

Current progress:
- Completed next-plan Stages 01–06.
- Latest completed commit: b4512f8 docs: close next stage 06 parent evidence.
- Next stage: Stage 07 — Teacher Content QA Evidence Pass.
- Production URL: https://school.431a.ru
- LAN URL: https://192.168.1.86
- Production marker: 6e698a0
- Production health at handoff: /ready=200, /health=200; backend/frontend/db/redis/prometheus healthy; grafana/proxy running.

Hard rules:
1. Do not ask me for context or decisions; inspect repo/docs/git/prod yourself.
2. Do not expose secrets, tokens, .env, private keys, JWTs, Bearer values, passwords, or SMB credentials.
3. Do not modify Nightscout or external medical systems.
4. Before any production deploy or production data mutation, run production backup + offsite verification.
5. Preserve dark Prism/Split UI style.
6. Parent privacy boundary is mandatory: aggregate progress only, no raw AI chat exposure.
7. Student-facing AI output must never show raw JSON, <think>, broken markdown tables, broken math markers, hidden answers, or unreadable mobile formatting.
8. Algebra/Geometry remain preview until verified source/RAG coverage exists.
9. Every stage ends with tests, docs/evidence, and commit if files changed.
10. Production tree is dirty/on master; avoid broad destructive deploy and marker advancement. Use targeted safe deploys only if required.

Start by reading the handoff file and Stage 07 in the main plan, then execute Stage 07 fully: teacher analytics → readiness matrix → topic detail → material QA status; audit log for QA transitions; blocked/needs-review cannot publish; tests; browser smoke; report; commit. Continue through later stages in order without involving me.
```
