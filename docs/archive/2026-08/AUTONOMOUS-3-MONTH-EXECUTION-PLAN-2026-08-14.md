# AI-Tutor Autonomous 3-Month Execution Plan

_Last updated: 2026-08-14 17:52 MSK_

## Purpose

This document is a self-contained execution plan for a fresh AI-Tutor development session with full repo and production access. It breaks the next 3 months into autonomous 24–48 hour stages and includes a ready-to-copy prompt for a new chat session.

The new session must not ask Igor for context unless a command is blocked by the runtime or a required credential/access is unavailable. It should make decisions independently, continue after temporary failures, and produce a manual testing plan when the 3-month plan is completed.

---

## Current Baseline

| Item | Current State |
|---|---|
| Workspace | `/root/workspace/ai-tutor` |
| Branch | `mvp-rescue` |
| Production URL | `https://school.431a.ru` |
| LAN URL | `https://192.168.1.86` |
| Current prod marker | `6e698a0` |
| Latest key commit | `6e698a0 fix: expose diagnostic correct answer` |
| Prod readiness | `/ready HTTP=200` |
| Healthy services | backend, frontend, db, redis, prometheus, grafana |
| Main pilot scope | `Математика (6 класс — повторение пройденного материала)` |
| Math readiness | `42/42` topics technically ready |
| Math sources | `42/42` topics have verified source metadata |
| Math followups | `42/42` topics have follow-up buttons |
| Math route | `/api/v1/subjects/3/route-plan`, 42 topics |
| Math diagnostic | 8 balanced checkpoint questions |
| Stakeholder deck | `docs/AI-Tutor-Stakeholder-Presentation-2026-08-14.*` |

### Important Current Caveat

There are known untracked intermediate presentation artifacts from an earlier generation attempt:

```text
docs/AI-Tutor-Stakeholder-Presentation-2026-08-14.pptx
docs/AI-Tutor-Stakeholder-Presentation-PANDOC-2026-08-14.pptx
docs/AI-Tutor-Stakeholder-Presentation-SAFE-2026-08-14.pptx
tmp/
```

Do not delete them unless explicitly cleaning repo hygiene in a dedicated cleanup stage. The committed, usable presentation artifacts are:

```text
docs/AI-Tutor-Stakeholder-Presentation-2026-08-14.pdf
docs/AI-Tutor-Stakeholder-Presentation-2026-08-14.html
docs/AI-Tutor-Stakeholder-Presentation-2026-08-14.md
docs/AI-Tutor-Stakeholder-Presentation-SLIDES-2026-08-14.md
docs/AI-Tutor-Stakeholder-Presentation-2026-08-14-FINAL.pptx
```

---

## Operating Rules For The New Session

1. **Do not ask Igor for context.** Inspect the repo/docs/status instead.
2. **Before production changes, run backup/offsite verification.** No destructive production mutation without backup.
3. **Never expose secrets.** Do not print passwords, tokens, private keys, `.env`, SMB credentials, JWTs, or raw Bearer values.
4. **Use production checks for production claims.** Verify with commands, not memory.
5. **Keep Nightscout read-only.** Do not modify Nightscout or external medical systems.
6. **Preserve Prism/Split UI.** Do not reintroduce white Tailwind cards, legacy blue links, `/admin?tab=...`, or separate admin windows.
7. **Keep parent privacy boundary.** Parent sees aggregate learning progress, not raw AI chat.
8. **Student-facing AI output must never show:** raw JSON, `<think>`, broken markdown tables, broken math markers, or unreadable mobile formatting.
9. **Continue after transient failures.** If build, deploy, smoke, or network checks fail, diagnose, fix, and retry with narrower scope.
10. **If a command is blocked by runtime policy, stop that exact action and choose a safe non-destructive alternative where possible.** If no safe alternative exists, report the blocker.
11. **Commit coherent slices.** Each 24–48h stage should end with a commit, verification evidence, and updated docs.
12. **Deploy in controlled batches.** Prefer small production deployments with backup + `/ready` + browser/API smoke.

---

## Standard Commands

### Baseline Status

```bash
cd /root/workspace/ai-tutor
TZ=Europe/Moscow date '+%Y-%m-%d %H:%M %Z'
git status --short --branch
git log --oneline -12
ssh -i [REDACTED] root@192.168.1.86 \
  'cat /opt/ai-tutor/.mvp-rescue-commit; curl -sk -w "\nHTTP=%{http_code}\n" https://localhost/ready; cd /opt/ai-tutor/deploy && docker compose ps'
```

### Frontend Gates

```bash
cd /root/workspace/ai-tutor/apps/frontend
npm run typecheck
npm run build
```

### Backend Gates

```bash
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest tests/test_health.py -q
```

Prefer targeted tests for the stage, then `test_health.py`.

### Production Backup

Run on production host before production deploy/data mutation:

```bash
ssh -i [REDACTED] root@192.168.1.86 \
  'set -e; cd /opt/ai-tutor/deploy/backup; ./backup.sh; ./ai-tutor-backup-offsite.sh'
```

### Production Health

```bash
curl -sk -w '\nHTTP=%{http_code}\n' https://192.168.1.86/ready
curl -sk -w '\nHTTP=%{http_code}\n' https://192.168.1.86/health
```

---

# 3-Month Plan By 24–48 Hour Stages

## Month 1 — Prove The Math Pilot

Goal: turn the technically-ready math MVP into a trustworthy learning pilot for one real student and family.

---

## Stage 01 — Pilot Baseline And Repo Hygiene

**Timebox:** 24 hours  
**Goal:** start from a clean, auditable state.

### Work

- Run baseline status commands.
- Confirm prod marker, `/ready`, service health.
- Inspect untracked files and decide whether to keep, commit, or document them.
- Ensure stakeholder presentation artifacts are discoverable.
- Update a short `docs/CURRENT-PILOT-STATUS-YYYY-MM-DD.md`.

### Verification

- `git status --short --branch` understood and documented.
- `/ready HTTP=200`.
- Docker services healthy/running.

### Deliverables

- Current pilot status doc.
- Optional repo hygiene commit.

### Done When

A new agent can tell exactly what is deployed and what files are intentional.

---

## Stage 02 — Math Editorial Review Framework

**Timebox:** 24–48 hours  
**Goal:** create a structured review system for all 42 math topics.

### Work

- Create `docs/MATH-EDITORIAL-REVIEW-MATRIX-YYYY-MM-DD.md`.
- For each topic, track:
  - explanation clarity;
  - fallback task clarity;
  - difficulty fit;
  - source usefulness;
  - common mistake quality;
  - parent-readable summary.
- Add teacher-facing statuses if missing:
  - `editorial_status` or equivalent registry note;
  - `needs_rewrite`, `approved`, `needs_example`, `needs_easy_task`.
- Do not rewrite all content blindly; flag first, then improve targeted issues.

### Verification

- Matrix covers 42/42 topics.
- Teacher readiness page still loads.
- Backend/Frontend gates pass if code changed.

### Deliverables

- Editorial review matrix.
- Optional status fields/UI if needed.

### Done When

Every math topic has a human-review slot and clear quality status.

---

## Stage 03 — Math Fallback Task Quality Pass 1

**Timebox:** 24–48 hours  
**Goal:** improve weak deterministic fallback tasks.

### Work

- Review existing fallback variants from `math_practice_variants_seed.py` and `math_fallback_seed.py`.
- Replace generic fallback tasks with real school-style tasks for at least 15 high-impact topics.
- Ensure every changed fallback is:
  - checkable;
  - single/numeric where practical;
  - has clear explanation;
  - has typical mistakes.
- Add tests that validate rows are checkable and correct answers appear in options.

### Verification

- Targeted backend tests pass.
- Production smoke on edited topics: explain → generate → wrong answer → correct answer.

### Deliverables

- Updated fallback seed(s).
- Updated editorial matrix.
- Smoke evidence doc.

### Done When

At least 15 topics have upgraded, non-generic fallback tasks.

---

## Stage 04 — Math Fallback Task Quality Pass 2

**Timebox:** 24–48 hours  
**Goal:** complete fallback quality across all 42 topics.

### Work

- Upgrade remaining topics not covered in Stage 03.
- Ensure each topic has 3 meaningful variants:
  - easy/base;
  - medium/practice;
  - review/checkpoint.
- Ensure no topic depends only on generic “what is this topic?” fallback.

### Verification

- Backend fallback tests pass.
- All-math targeted practice smoke passes or records failures with fixes.

### Deliverables

- `docs/MATH-FALLBACK-QUALITY-REPORT-YYYY-MM-DD.md`.
- Commit with seed and tests.

### Done When

42/42 math topics have meaningful practice variants.

---

## Stage 05 — Live Student Pilot Script

**Timebox:** 24 hours  
**Goal:** define exact manual pilot scenario before real testing.

### Work

Create `docs/MATH-LIVE-PILOT-SCRIPT-YYYY-MM-DD.md` covering:

1. Login as student.
2. Start math diagnostic.
3. Answer at least 3 questions.
4. Open route map.
5. Complete one easy topic.
6. Intentionally answer one task wrong.
7. Read feedback.
8. Complete one correct task.
9. Check parent dashboard.
10. Check teacher readiness.

### Verification

- Dry-run script with QA/test accounts where safe.
- No secret values written.

### Deliverables

- Manual pilot script.
- Browser smoke evidence for the non-destructive parts.

### Done When

A human can run the pilot without asking the agent what to click.

---

## Stage 06 — Student Lesson Loop Polish

**Timebox:** 24–48 hours  
**Goal:** make the lesson feel guided, not like a generic chat.

### Work

- Improve `/topics/[id]` next-step panel:
  - after explanation: suggest practice;
  - after wrong answer: suggest retry/explanation;
  - after correct answer: suggest next task or next topic.
- Use route-plan `next_topic_id` where useful.
- Avoid layout regressions on mobile.

### Verification

- Frontend typecheck/build.
- Mobile viewport smoke: `/topics/187`, `/topics/200`, `/topics/228`.
- Overflow = 0, no white panels.

### Deliverables

- UI changes.
- Smoke report.

### Done When

The student can understand the next action at every step.

---

## Stage 07 — Parent Report V2 For Math Pilot

**Timebox:** 24–48 hours  
**Goal:** make parent output actionable and non-technical.

### Work

- Improve parent dashboard math section:
  - “what improved”;
  - “where help is needed”;
  - “what to do tomorrow”;
  - route/checkpoint progress.
- Preserve privacy boundary: no raw chat.
- Add export/print-friendly wording if practical.

### Verification

- Parent dashboard smoke under parent QA account.
- No raw chat displayed.
- Mobile/desktop layout no overflow.

### Deliverables

- Parent dashboard update.
- Parent summary examples in docs.

### Done When

A parent can understand progress in under 1 minute.

---

## Stage 08 — Teacher Review Mode V2

**Timebox:** 24–48 hours  
**Goal:** make quality review faster for teacher/admin.

### Work

- Improve teacher topics/readiness view:
  - filter by editorial status;
  - show source/fallback/followup coverage;
  - show route tier and checkpoint flag;
  - quick “needs rewrite / approved” action if safe.
- Keep UI Prism style.

### Verification

- Teacher page smoke.
- Backend tests for any new status logic.
- No destructive editing of other users’ materials.

### Deliverables

- Teacher review improvements.
- Updated review matrix.

### Done When

Teacher can review math topics without reading raw JSON or logs.

---

## Stage 09 — Adaptive Progression Pass 1

**Timebox:** 24–48 hours  
**Goal:** use student data to guide next topic selection.

### Work

- Review current `/api/v1/progress/recommend-next`.
- Restrict math pilot recommendations to math route when current subject is math.
- Prefer weak topics before new topics.
- Use route order and mastery thresholds.
- Keep T1D recovery behavior intact.

### Verification

- Unit tests for:
  - no attempts → first route topic;
  - weak topic → review weak topic;
  - mastered current → next route topic;
  - all mastered → completion message.
- Browser smoke on student page.

### Deliverables

- Improved progression logic.
- Tests.

### Done When

Next-topic recommendation is explainable and stable.

---

## Stage 10 — Month 1 Pilot Report And Decision Gate

**Timebox:** 24 hours  
**Goal:** close the first month plan with evidence and decide expansion readiness.

### Work

- Compile docs from Stages 01–09.
- Produce `docs/MATH-PILOT-MONTH-1-REPORT-YYYY-MM-DD.md`.
- Include:
  - what works;
  - what failed;
  - quality gaps;
  - data from attempts;
  - parent/teacher observations;
  - recommendation: continue math polish vs start algebra/geometry.

### Verification

- Production `/ready=200`.
- Key smoke tests pass.
- Report references actual command outputs.

### Deliverables

- Month 1 report.
- Updated stakeholder summary if useful.

### Done When

There is a clear decision whether to expand beyond math.

---

## Month 2 — Expand The Proven Template

Goal: apply the same readiness pattern to Algebra and Geometry without lowering quality standards.

---

## Stage 11 — Algebra/Geometry Scope Audit

**Timebox:** 24–48 hours  
**Goal:** understand what exists before adding content.

### Work

- Identify subject IDs and current topic counts for Algebra and Geometry.
- For each subject, audit:
  - topics;
  - source materials;
  - RAG chunks;
  - fallback tasks;
  - followups;
  - current preview/readiness state.
- Produce `docs/ALGEBRA-GEOMETRY-SCOPE-AUDIT-YYYY-MM-DD.md`.

### Verification

- Audit produced from DB/API, not guessed.
- No production mutation.

### Deliverables

- Scope audit.
- Estimated work per subject.

### Done When

The agent knows exactly what is missing for Algebra/Geometry readiness.

---

## Stage 12 — Algebra Route Plan

**Timebox:** 24–48 hours  
**Goal:** create route-plan equivalent for Algebra.

### Work

- Add algebra route map module or extend existing route abstraction.
- Define topic order, tier, focus, checkpoints.
- Add route-plan endpoint for Algebra only when the subject has enough coverage or mark as preview route.
- Add tests.

### Verification

- Backend tests pass.
- API returns route count matching DB topics.
- Non-ready subjects are not falsely marked ready.

### Deliverables

- Algebra route plan.
- Tests.

### Done When

Algebra has a structured learning path, even if not yet content-ready.

---

## Stage 13 — Geometry Route Plan

**Timebox:** 24–48 hours  
**Goal:** create route-plan equivalent for Geometry.

### Work

- Same pattern as Algebra:
  - topic order;
  - tier;
  - focus;
  - checkpoint topics.
- Add tests and preview UI indicators.

### Verification

- Backend tests pass.
- UI clearly says preview if content is not ready.

### Deliverables

- Geometry route plan.
- Tests.

### Done When

Geometry has a structured route without overstating readiness.

---

## Stage 14 — Algebra Source And RAG Readiness Pass

**Timebox:** 24–48 hours  
**Goal:** prepare algebra sources like math sources.

### Work

- Import or identify source materials.
- Chunk and backfill metadata.
- Ensure citations have:
  - subject_id;
  - topic_id;
  - topic_name;
  - page_number or stable section reference;
  - material_title.
- Add audit doc.

### Verification

- Source smoke on representative topics.
- No misleading math sources used for Algebra.

### Deliverables

- Algebra RAG source audit.
- Backfill script if needed.

### Done When

Algebra can show verified sources for its pilot topics.

---

## Stage 15 — Geometry Source And RAG Readiness Pass

**Timebox:** 24–48 hours  
**Goal:** prepare geometry sources like math sources.

### Work

- Same as Algebra source pass.
- Special attention to diagrams/visual geometry: if source extraction is weak, document limitations.

### Verification

- Source smoke on representative topics.
- No weak/vague citations shown as verified.

### Deliverables

- Geometry RAG source audit.

### Done When

Geometry can show verified sources for its pilot topics or has documented blockers.

---

## Stage 16 — Algebra Practice Bank Pass 1

**Timebox:** 24–48 hours  
**Goal:** create deterministic checkable Algebra fallback tasks.

### Work

- Build fallback seed similar to math fallback/variants.
- Start with P0/pilot topics only.
- Add tests that all answers are checkable.

### Verification

- Generate → wrong check → correct check smoke.

### Deliverables

- Algebra fallback seed.
- Test coverage.

### Done When

Algebra pilot topics do not depend on unstable free-text practice.

---

## Stage 17 — Geometry Practice Bank Pass 1

**Timebox:** 24–48 hours  
**Goal:** create deterministic checkable Geometry fallback tasks.

### Work

- Build geometry fallback seed.
- Prefer single-choice/numeric tasks.
- Avoid visual-only tasks until diagram support is reliable.

### Verification

- Generate/check smoke.
- Tests for fallback rows.

### Deliverables

- Geometry fallback seed.

### Done When

Geometry pilot topics have stable practice tasks.

---

## Stage 18 — Multi-Subject Readiness UI

**Timebox:** 24–48 hours  
**Goal:** make subject readiness honest and understandable.

### Work

- Update subjects page/readiness panels:
  - math = ready;
  - algebra/geometry = preview, partial-ready, or ready based on actual coverage;
  - show sources/practice/route status.
- Add teacher/admin views for subject readiness.

### Verification

- Multi-subject Playwright smoke.
- No subject is marked ready without source + practice + smoke coverage.

### Deliverables

- UI changes.
- Readiness report.

### Done When

Stakeholders can see exactly which subjects are ready and why.

---

## Stage 19 — Month 2 Expansion Report

**Timebox:** 24 hours  
**Goal:** close Month 2 and decide Month 3 priorities.

### Work

- Produce `docs/MONTH-2-SUBJECT-EXPANSION-REPORT-YYYY-MM-DD.md`.
- Include readiness per subject:
  - route;
  - sources;
  - fallback practice;
  - smoke;
  - manual review status.

### Verification

- Report backed by command/API evidence.
- Prod healthy.

### Deliverables

- Month 2 report.

### Done When

It is clear whether Algebra/Geometry can enter pilot scope.

---

## Month 3 — Platform Layer And Manual Testing Readiness

Goal: make the product manageable, measurable, and ready for manual testing by a human.

---

## Stage 20 — Learning Analytics V1

**Timebox:** 24–48 hours  
**Goal:** show useful learning data without overwhelming users.

### Work

- Aggregate by subject/topic:
  - attempts;
  - accuracy;
  - mastery;
  - weak topics;
  - recent activity.
- Add admin/teacher dashboard panels if missing.
- Keep parent view simple.

### Verification

- Backend tests for aggregations.
- Dashboard smoke.

### Deliverables

- Analytics V1.
- Docs.

### Done When

Teacher/admin can identify where learning or content is weak.

---

## Stage 21 — Content Quality Workflow V1

**Timebox:** 24–48 hours  
**Goal:** make content QA repeatable.

### Work

- Define statuses:
  - draft;
  - AI generated;
  - needs review;
  - approved;
  - published;
  - blocked.
- Ensure teacher UI supports status changes safely.
- Add audit logging for sensitive changes.

### Verification

- Teacher tests.
- Audit tests.

### Deliverables

- Content QA workflow.

### Done When

Content readiness is a workflow, not a spreadsheet in someone’s head.

---

## Stage 22 — Manual Testing Harness

**Timebox:** 24–48 hours  
**Goal:** make human testing easy and reproducible.

### Work

- Build `/docs/MANUAL-TESTING-PLAN-YYYY-MM-DD.md` draft.
- Create test scenarios for:
  - student;
  - parent;
  - teacher;
  - admin;
  - recovery after errors;
  - mobile.
- Include expected results and what counts as blocker.

### Verification

- Dry-run selected scenarios with browser automation.
- No secrets in doc.

### Deliverables

- Manual testing plan draft.

### Done When

A human tester can execute scenarios without chat history.

---

## Stage 23 — Reliability And Alerts Hardening

**Timebox:** 24–48 hours  
**Goal:** ensure pilot failures are visible.

### Work

- Validate Prometheus rules:
  - backend down;
  - 5xx;
  - unexpected 4xx;
  - disk;
  - backup age;
  - Redis/DB health.
- Fix stale/incorrect dashboard panels.
- Document alert interpretation.

### Verification

- Prometheus rules API.
- Grafana provisioning logs.
- Admin Realtime smoke.

### Deliverables

- Monitoring validation report.

### Done When

A real production problem is visible without SSH.

---

## Stage 24 — Performance And Cost Review

**Timebox:** 24–48 hours  
**Goal:** know if the pilot is affordable and responsive.

### Work

- Measure:
  - AI call latency;
  - token use;
  - route latency;
  - frontend load;
  - backend memory.
- Identify expensive or slow flows.
- Add simple caching/retry limits where appropriate.

### Verification

- Metrics captured from production.
- No secrets exposed.

### Deliverables

- Performance/cost report.

### Done When

The project has a cost/performance baseline for pilot scaling.

---

## Stage 25 — Security And Privacy Review

**Timebox:** 24–48 hours  
**Goal:** reduce pilot risk.

### Work

- Review auth, parent-child links, teacher/admin RBAC, invite flows.
- Confirm parent cannot access raw chat.
- Confirm preview subjects do not expose misleading ready state.
- Run relevant security tests.

### Verification

- Auth/RBAC tests.
- Browser/API checks.

### Deliverables

- Security/privacy report.

### Done When

Pilot privacy boundaries are explicitly verified.

---

## Stage 26 — Cross-Role Pilot Dress Rehearsal

**Timebox:** 24–48 hours  
**Goal:** run the whole system before handing to Igor.

### Work

Run a full end-to-end rehearsal:

1. Student logs in.
2. Student starts diagnostic.
3. Student completes one topic.
4. Student answers one wrong and one correct task.
5. Parent checks summary.
6. Teacher checks readiness/content status.
7. Admin checks monitoring/realtime.
8. Export/report links work.

### Verification

- Browser smoke evidence.
- `/ready HTTP=200` after test.
- No unexpected 5xx.

### Deliverables

- Dress rehearsal report.

### Done When

The system is ready for Igor’s manual testing.

---

## Stage 27 — Final 3-Month Completion Report

**Timebox:** 24 hours  
**Goal:** summarize the whole 3-month execution.

### Work

Create `docs/THREE-MONTH-EXECUTION-REPORT-YYYY-MM-DD.md`:

- what was done;
- what was deployed;
- what tests passed;
- what still needs human review;
- subject readiness matrix;
- product maturity by phase;
- known risks.

### Verification

- Report references actual docs/commits/markers.
- Prod health included.

### Deliverables

- Final 3-month report.

### Done When

Igor can read one file and understand the project state.

---

## Stage 28 — Final Manual Testing Plan For Igor

**Timebox:** 24 hours  
**Goal:** provide manual testing instructions after the 3-month plan is complete.

### Work

Produce `docs/FINAL-MANUAL-TESTING-PLAN-YYYY-MM-DD.md` with:

- test accounts by role, without passwords;
- exact route list;
- step-by-step student scenario;
- parent scenario;
- teacher scenario;
- admin scenario;
- mobile scenario;
- expected results;
- blocker severity definitions;
- screenshot checklist;
- feedback template.

### Verification

- Plan references deployed marker.
- No secrets in plan.
- All referenced routes exist.

### Deliverables

- Final manual testing plan.

### Done When

The new session can stop execution and hand Igor a complete manual testing plan.

---

# Definition Of Done For The Full 3-Month Plan

The 3-month plan is complete only when all of the following are true:

- Production is healthy: `/ready HTTP=200`.
- Current production marker is recorded.
- Math pilot has live-use evidence or a completed dress rehearsal.
- Math has editorial status for all 42 topics.
- Algebra/Geometry readiness is honestly reported; ready only if source + route + fallback + smoke criteria are met.
- Parent, teacher, admin, and student flows are tested.
- Monitoring/backup status is documented.
- Security/privacy review is documented.
- Final execution report exists.
- Final manual testing plan exists.
- No secrets are written to docs.

---

# Ready-To-Copy Prompt For A New Autonomous Session

Copy the full prompt below into a new Hermes chat session.

```text
[Workspace::v1: /root/workspace]

Open and follow `/root/workspace/ai-tutor/docs/AUTONOMOUS-3-MONTH-EXECUTION-PLAN-2026-08-14.md` from top to bottom.

You are continuing the AI-Tutor MVP project on branch `mvp-rescue`.

Goal: execute the full 3-month plan autonomously in 24–48 hour stages. Do not ask me for context. Inspect the repo, docs, git history, production marker, services, and existing reports yourself. Make decisions independently. If commands fail, debug and retry with a narrower safe path. If a long command hangs, wait, check progress, and continue from the last completed stage. If the session disconnects or context is compressed, resume from the latest committed stage/report and production marker.

Current known baseline at plan creation:
- Workspace: `/root/workspace/ai-tutor`
- Production URL: `https://school.431a.ru`
- LAN URL: `https://192.168.1.86`
- Branch: `mvp-rescue`
- Production marker: `6e698a0`
- `/ready HTTP=200`
- Services healthy/running: backend, frontend, db, redis, prometheus, grafana
- Math subject is the pilot scope: `Математика (6 класс — повторение пройденного материала)`
- Math technical readiness: `42/42`
- Math verified source coverage: `42/42`
- Math followup coverage: `42/42`
- Math route plan exists: `/api/v1/subjects/3/route-plan`
- Math diagnostic uses 8 checkpoint topics and returns `correct_answer`

Hard rules:
1. Do not expose secrets. Never print passwords, tokens, `.env`, private key contents, JWTs, Bearer values, or SMB credentials.
2. Do not modify Nightscout or external medical systems.
3. Before any production deploy or production data mutation, run production backup and offsite verification.
4. Preserve dark Prism/Split UI style. Do not reintroduce white cards or legacy admin routes.
5. Parent privacy boundary is mandatory: aggregate progress only, no raw AI chat exposure.
6. Student-facing AI output must never show raw JSON, `<think>`, broken markdown tables, broken math markers, or unreadable mobile formatting.
7. Use commands to verify every claim. Do not rely on memory.
8. Commit coherent slices. Each stage should end with tests, docs/evidence, and commit where files changed.
9. Deploy in small controlled batches with `/ready`, service health, and browser/API smoke.
10. Do not ask Igor what to do next unless a command is hard-blocked by runtime policy or required access is missing.

Execution:
- Start with Stage 01 in the plan document.
- Continue through all stages in order unless a later prerequisite must be fixed first.
- If a stage reveals a real blocker, fix it at root cause, update tests/docs, and continue.
- If a stage is already complete, verify it and mark/report it as complete rather than redoing destructive work.
- Maintain or create stage reports under `docs/`.
- After the full 3-month plan is complete, provide `docs/FINAL-MANUAL-TESTING-PLAN-YYYY-MM-DD.md` for Igor with step-by-step manual testing scenarios.

At the end, report:
- final production marker;
- production health;
- completed stages;
- tests passed;
- backups used;
- remaining non-blockers;
- path to final manual testing plan.

Begin now. Do not ask clarifying questions.
```

---

# Session Recovery Rules

If the new session loses context, it must recover by running:

```bash
cd /root/workspace/ai-tutor
TZ=Europe/Moscow date '+%Y-%m-%d %H:%M %Z'
git status --short --branch
git log --oneline -20
find docs -maxdepth 1 -type f | grep -E 'REPORT|PLAN|MATRIX|PILOT|READINESS' | sort | tail -50
ssh -i [REDACTED] root@192.168.1.86 \
  'cat /opt/ai-tutor/.mvp-rescue-commit; curl -sk -w "\nHTTP=%{http_code}\n" https://localhost/ready; cd /opt/ai-tutor/deploy && docker compose ps'
```

Then continue from the latest stage report that exists in `docs/` and the latest commit marker.

---

# Manual Testing Plan Requirements After Completion

The final manual testing plan must include at minimum:

## Student

- Login.
- Open subjects.
- Open math route.
- Start diagnostic.
- Answer at least 3 diagnostic questions.
- Open a recommended topic.
- Read explanation.
- Generate practice.
- Answer wrong.
- Read feedback.
- Answer correct.
- Move to next topic.

## Parent

- Login.
- Open children list.
- Open child dashboard.
- Confirm weekly summary.
- Confirm weak topics.
- Confirm “what to do tomorrow”.
- Confirm raw chat is not visible.

## Teacher

- Login.
- Open topic readiness.
- Filter by subject/status.
- Review route tier/checkpoint/source/fallback/followup indicators.
- Edit a safe draft/status if included in current release.

## Admin

- Login.
- Open `/admin`.
- Check users/invites/audit/realtime.
- Confirm no separate `/admin?tab` or legacy visible admin window.
- Confirm monitoring values look stable.

## Mobile

- iPhone-size viewport.
- `/subjects`, `/subjects/3`, `/topics/187`, `/diagnostic`.
- Confirm no horizontal overflow, no white legacy panels, readable chat/practice.

## Blocker Definitions

- P0 blocker: login impossible, `/ready` fails, student cannot complete lesson, parent sees private chat, production data corruption, 5xx on core route.
- P1 blocker: broken route UI, diagnostic inaccurate, teacher cannot review readiness, mobile core layout unusable.
- P2 issue: copy typo, minor spacing, cosmetic low-risk bug.
