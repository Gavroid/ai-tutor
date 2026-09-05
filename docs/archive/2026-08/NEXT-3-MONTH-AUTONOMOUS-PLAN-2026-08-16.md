# Next 3-Month Autonomous Plan — 2026-08-16

> **For Hermes:** Execute this plan stage-by-stage without asking Igor for context. Resume from git/prod/docs evidence, not memory. Use TDD for behavior changes, run production backup/offsite before production mutation, and close every stage with docs, tests, smoke, and a commit.

## Goal

Move AI-Tutor from a Math-only MVP pilot into a stable, evidence-driven pilot platform with real manual feedback, release hygiene, verified Algebra/Geometry source readiness, stronger learning quality controls, and operational predictability.

## Architecture

The current production system stays centered on the Math pilot (`subject_id=3`) while Algebra (`subject_id=4`) and Geometry (`subject_id=5`) remain preview until verified source/RAG coverage exists. The next phase should improve release hygiene, collect manual pilot evidence, and build the source/RAG pipeline needed to promote preview subjects safely.

## Tech Stack

FastAPI backend, Next.js frontend, PostgreSQL, Redis, Prometheus, Grafana, Docker Compose, Playwright, pytest, targeted production deploys over SSH.

## Hard Rules

1. Do not expose secrets, tokens, `.env`, JWTs, private keys, or SMB credentials.
2. Do not modify Nightscout or external medical systems.
3. Before any production deploy or production data mutation, run production backup and offsite verification.
4. Preserve dark Prism/Split UI style.
5. Parent privacy boundary remains mandatory: aggregate progress only, no raw AI chat.
6. Student-facing output must never show raw JSON, `<think>`, broken markdown tables, broken math markers, or unreadable mobile formatting.
7. Algebra/Geometry must remain preview until source/RAG coverage is verified.
8. Every stage ends with tests, docs/evidence, and commit if files changed.

---

# Month 1 — Pilot Operations, Release Hygiene, And Math Quality

Month 1 keeps scope tight: use Math pilot manually, close release/process gaps, and turn feedback into measured product improvements.

## Stage 01 — Release Hygiene And Marker Recovery Plan

**Timebox:** 24–48 hours  
**Goal:** make production marker and release state trustworthy again.

### Work

- Inspect production working tree, branch, dirty files, and current deploy structure.
- Compare production deployed files to `mvp-rescue` HEAD where safely possible.
- Document why marker remains `6e698a0` and what is required to advance it safely.
- Create a marker advancement runbook that preserves targeted deploy safety.
- Do not run broad destructive sync unless prod tree is clean and backup/offsite is verified.

### Verification

- `git status`, `git log`, production marker, `/ready`, service health.
- Dry-run or read-only diff summary between local and prod.

### Deliverables

- `docs/NEXT-STAGE-01-RELEASE-HYGIENE-REPORT-YYYY-MM-DD.md`
- Optional runbook update under `deploy/release/` if code changes are needed.

### Done When

A future operator can understand exactly how to advance marker safely without guessing.

## Stage 02 — Math Manual Pilot Intake Framework

**Timebox:** 24–48 hours  
**Goal:** prepare structured intake for Igor/human manual testing.

### Work

- Review `docs/FINAL-MANUAL-TESTING-PLAN-2026-08-16.md`.
- Create a feedback intake table/template for scenario results.
- Add fields for severity, role, route, screenshot, reproduction steps, and decision.
- Add rules for what becomes blocker/high/medium/low.

### Verification

- No secrets in template.
- Routes in template still return HTTP 200.

### Deliverables

- `docs/MATH-PILOT-FEEDBACK-INTAKE-YYYY-MM-DD.md`

### Done When

Manual tester feedback can be pasted into one document and triaged without further structure work.

## Stage 03 — Math Student Session Evidence Pass 1

**Timebox:** 24–48 hours  
**Goal:** turn the existing student smoke into richer evidence.

### Work

- Run student scenario from final manual plan on production/LAN.
- Capture route timings and no-leak checks.
- Check explanation/practice output cleanliness on first 3–5 Math topics.
- Record failures in feedback intake.

### Verification

- Playwright student flow.
- API checks for no `correct_answer` leak before submit.
- `/ready HTTP=200` after run.

### Deliverables

- `docs/NEXT-STAGE-03-MATH-STUDENT-EVIDENCE-PASS-1-YYYY-MM-DD.md`

### Done When

Math student flow has current manual/automated evidence beyond simple route availability.

## Stage 04 — Math Explanation Quality Sweep

**Timebox:** 24–48 hours  
**Goal:** catch weak explanations before real pilot use.

### Work

- Select representative Math route topics: first, checkpoints, weak/complex topics, last.
- Smoke explanation generation/admin explain without burning student budget where possible.
- Flag explanations that are too short, off-topic, unreadable, or source-unsupported.
- Add regression tests or fallback rules only for concrete repeated defects.

### Verification

- Targeted backend tests for any new fallback/sanitizer behavior.
- UI smoke for corrected topics.

### Deliverables

- `docs/NEXT-STAGE-04-MATH-EXPLANATION-QUALITY-SWEEP-YYYY-MM-DD.md`

### Done When

Representative Math explanations are readable and defect patterns are documented or fixed.

## Stage 05 — Math Practice Variant Rotation Audit

**Timebox:** 24–48 hours  
**Goal:** confirm practice does not repeat stale tasks too aggressively.

### Work

- Exercise `Следующее задание` / practice regeneration across representative topics.
- Verify seed/variant changes.
- Add tests if repeated tasks occur after correct answer.
- Keep deterministic fallback bank student-ready.

### Verification

- Backend fallback seed tests.
- Playwright student flow checking changed task text/options where deterministic.

### Deliverables

- `docs/NEXT-STAGE-05-MATH-PRACTICE-ROTATION-AUDIT-YYYY-MM-DD.md`

### Done When

Students can get repeat practice without obvious same-task loops.

## Stage 06 — Parent Report Manual Evidence Pass

**Timebox:** 24–48 hours  
**Goal:** validate parent privacy and usefulness with realistic progress data.

### Work

- Use existing/seeded progress to inspect parent dashboard.
- Verify aggregate-only boundary.
- Check recommendations for no attempts, weak topics, good progress, and due review cases.
- Patch recommendation copy only if it is misleading.

### Verification

- Parent dashboard E2E.
- Backend parent tests.
- No raw AI chat in UI/API response.

### Deliverables

- `docs/NEXT-STAGE-06-PARENT-REPORT-EVIDENCE-YYYY-MM-DD.md`

### Done When

Parent report is understandable and privacy-safe for manual pilot.

## Stage 07 — Teacher Content QA Evidence Pass

**Timebox:** 24–48 hours  
**Goal:** verify teacher can use analytics/readiness/QA workflow in real order.

### Work

- Run teacher flow: analytics → readiness matrix → topic detail → material QA status.
- Confirm audit logs capture QA status transitions.
- Verify blocked/needs-review material cannot be published.
- Improve copy/empty states if teacher workflow is unclear.

### Verification

- Teacher workflow tests.
- Teacher review Playwright smoke.
- Admin audit filter for QA transition.

### Deliverables

- `docs/NEXT-STAGE-07-TEACHER-QA-EVIDENCE-YYYY-MM-DD.md`

### Done When

Teacher workflow has current evidence and no unclear critical path.

## Stage 08 — Admin Monitoring Drill

**Timebox:** 24–48 hours  
**Goal:** verify a real problem is visible without SSH.

### Work

- Review Prometheus rules and Admin Realtime after recent traffic.
- Verify DB/Redis/disk/backup metrics are present.
- Simulate only safe read-only alert queries; do not break production services.
- Document how an operator interprets 4xx vs 5xx.

### Verification

- Prometheus rules API.
- Prometheus query API for ops gauges.
- Admin Realtime snapshot.

### Deliverables

- `docs/NEXT-STAGE-08-ADMIN-MONITORING-DRILL-YYYY-MM-DD.md`

### Done When

Operator can see health/alerts without SSH and knows what to do first.

## Stage 09 — Month 1 Pilot Operations Report

**Timebox:** 24 hours  
**Goal:** decide what to fix before Algebra/Geometry source work accelerates.

### Work

- Consolidate Stage 01–08 evidence.
- List blocker/high/medium/low issues.
- Decide whether Math manual pilot is ready for a real child session.
- Update next-month priorities based on evidence.

### Verification

- References actual stage reports and latest prod health.

### Deliverables

- `docs/NEXT-MONTH-1-PILOT-OPS-REPORT-YYYY-MM-DD.md`

### Done When

There is a clear go/no-go recommendation for Math manual pilot continuation.

---

# Month 2 — Verified Sources, RAG, And Subject Expansion

Month 2 focuses on the main blocker: Algebra/Geometry cannot become pilot-ready without verified source/RAG coverage.

## Stage 10 — Source Acquisition Policy And License Gate

**Timebox:** 24–48 hours  
**Goal:** define what counts as acceptable source material.

### Work

- Document source acceptance criteria: license, provenance, topic coverage, retrievability.
- Create a checklist for importing materials.
- Re-evaluate previous candidate sources against the checklist.
- Do not import questionable materials.

### Verification

- Source checklist has explicit pass/fail criteria.
- No copyrighted/uncertain materials imported.

### Deliverables

- `docs/NEXT-STAGE-10-SOURCE-ACQUISITION-POLICY-YYYY-MM-DD.md`

### Done When

Future source imports are governed by a written gate.

## Stage 11 — Algebra Source Candidate Search Pass

**Timebox:** 24–48 hours  
**Goal:** find legally usable Algebra sources or confirm blocker remains.

### Work

- Search official/open educational repositories.
- Record candidates with URL, license/provenance, downloadability, coverage fit.
- Reject sources that require auth, have unclear rights, or mismatch grade/topic scope.

### Verification

- Every candidate has a decision and evidence.
- No material imported unless it passes Stage 10 gate.

### Deliverables

- `docs/NEXT-STAGE-11-ALGEBRA-SOURCE-CANDIDATES-YYYY-MM-DD.md`

### Done When

Algebra has either approved sources ready for import or a documented unresolved blocker.

## Stage 12 — Geometry Source Candidate Search Pass

**Timebox:** 24–48 hours  
**Goal:** find legally usable Geometry sources or confirm blocker remains.

### Work

- Repeat Stage 11 for Geometry.
- Prioritize sources with diagrams/definitions/examples aligned to route topics.
- Reject random mirrors and unclear scans.

### Verification

- Every candidate has a decision and evidence.

### Deliverables

- `docs/NEXT-STAGE-12-GEOMETRY-SOURCE-CANDIDATES-YYYY-MM-DD.md`

### Done When

Geometry source status is evidence-backed.

## Stage 13 — Algebra Source Import Dry Run

**Timebox:** 24–48 hours  
**Goal:** dry-run import only if approved Algebra sources exist.

### Work

- If no approved sources exist, write blocker report and skip import.
- If approved sources exist, import into staging/local first.
- Map pages/sections to Algebra route topics.
- Do not mark production ready until mapping is verified.

### Verification

- Local import script/test.
- Topic coverage count.
- No production mutation without backup/offsite.

### Deliverables

- `docs/NEXT-STAGE-13-ALGEBRA-SOURCE-IMPORT-DRY-RUN-YYYY-MM-DD.md`

### Done When

Algebra import path is proven locally or blocker is documented.

## Stage 14 — Geometry Source Import Dry Run

**Timebox:** 24–48 hours  
**Goal:** dry-run import only if approved Geometry sources exist.

### Work

- Same pattern as Algebra dry run.
- Pay special attention to diagrams and whether text extraction is sufficient.

### Verification

- Local import script/test.
- Topic coverage count.

### Deliverables

- `docs/NEXT-STAGE-14-GEOMETRY-SOURCE-IMPORT-DRY-RUN-YYYY-MM-DD.md`

### Done When

Geometry import path is proven locally or blocker is documented.

## Stage 15 — RAG Metadata Quality Contract

**Timebox:** 24–48 hours  
**Goal:** prevent future false readiness from wrong topic/source attachments.

### Work

- Add tests/checks for `topic_id`, `topic_name`, source title, page/section metadata.
- Add audit script to detect mismatched subject/material chunks.
- Ensure a Geometry file cannot count as Algebra source coverage.

### Verification

- Backend tests or script output with known good/bad examples.

### Deliverables

- `docs/NEXT-STAGE-15-RAG-METADATA-QUALITY-CONTRACT-YYYY-MM-DD.md`

### Done When

False source/RAG readiness is automatically detectable.

## Stage 16 — Algebra RAG Build Or Blocker Closure

**Timebox:** 24–48 hours  
**Goal:** either build Algebra RAG from approved sources or close blocker honestly.

### Work

- If approved/imported Algebra sources exist, build topic-scoped RAG chunks.
- Run metadata quality contract.
- Smoke `/subjects/4/route-plan`, teacher readiness, and source counts.
- If not, keep `rag_ready=false` and update blocker docs.

### Verification

- RAG chunk counts by topic.
- Teacher readiness API.
- Production backup before mutation if deployed.

### Deliverables

- `docs/NEXT-STAGE-16-ALGEBRA-RAG-BUILD-OR-BLOCKER-YYYY-MM-DD.md`

### Done When

Algebra RAG status is either verified or honestly blocked.

## Stage 17 — Geometry RAG Build Or Blocker Closure

**Timebox:** 24–48 hours  
**Goal:** either build Geometry RAG from approved sources or close blocker honestly.

### Work

- Same as Algebra, with diagram/source caveats.

### Verification

- RAG chunk counts by topic.
- Teacher readiness API.

### Deliverables

- `docs/NEXT-STAGE-17-GEOMETRY-RAG-BUILD-OR-BLOCKER-YYYY-MM-DD.md`

### Done When

Geometry RAG status is either verified or honestly blocked.

## Stage 18 — Multi-Subject Promotion Decision Gate

**Timebox:** 24 hours  
**Goal:** decide whether Algebra/Geometry can move beyond preview.

### Work

- Compare route/source/practice/smoke coverage for Math, Algebra, Geometry.
- Only promote a subject if all criteria pass.
- Keep preview if source/RAG is incomplete.

### Verification

- `/api/v1/subjects` readiness fields.
- Teacher readiness counts.
- Student smoke if promoted.

### Deliverables

- `docs/NEXT-STAGE-18-MULTI-SUBJECT-PROMOTION-DECISION-YYYY-MM-DD.md`

### Done When

Promotion/no-promotion decision is explicit and evidence-backed.

## Stage 19 — Month 2 Source Expansion Report

**Timebox:** 24 hours  
**Goal:** summarize source/RAG progress and remaining blockers.

### Work

- Consolidate Stages 10–18.
- Update readiness matrix.
- Define next-month operational focus.

### Verification

- References actual docs, counts, and prod health.

### Deliverables

- `docs/NEXT-MONTH-2-SOURCE-EXPANSION-REPORT-YYYY-MM-DD.md`

### Done When

Month 2 has an honest source/RAG status and decision trail.

---

# Month 3 — Scale, Quality Controls, And Pilot Handoff

Month 3 prepares the system for repeatable pilot operation, not just one-off testing.

## Stage 20 — AI Cost And Token Measurement After Live Usage

**Timebox:** 24–48 hours  
**Goal:** replace empty AI-cost baseline with real usage numbers.

### Work

- Run or wait for an AI-heavy lesson/session.
- Query `ai_requests_total` and `ai_tokens_total` after traffic.
- Estimate cost by mode where pricing is known.
- Flag expensive flows.

### Verification

- Prometheus query output.
- No secrets in logs.

### Deliverables

- `docs/NEXT-STAGE-20-AI-COST-TOKEN-MEASUREMENT-YYYY-MM-DD.md`

### Done When

AI cost baseline is based on real non-empty counters or explicitly blocked by no live usage.

## Stage 21 — Latency Budget And Cache Pass

**Timebox:** 24–48 hours  
**Goal:** keep common routes responsive under pilot load.

### Work

- Measure `/subjects`, route-plan, topic detail, analytics, parent dashboard.
- Identify slow queries or cold-cache paths.
- Add cache/versioning only where measured benefit exists.

### Verification

- Before/after timings.
- Backend tests for cache shape if changed.

### Deliverables

- `docs/NEXT-STAGE-21-LATENCY-CACHE-PASS-YYYY-MM-DD.md`

### Done When

Common pilot routes have documented latency budget and no obvious slow blockers.

## Stage 22 — Student Safety Output Contract Pass

**Timebox:** 24–48 hours  
**Goal:** harden student-facing output contracts.

### Work

- Sweep explain/practice/check outputs for raw JSON, `<think>`, broken markdown, and answer leaks.
- Add regression tests for any leak pattern.
- Keep UI readable on mobile.

### Verification

- Backend output contract tests.
- Student Playwright smoke.

### Deliverables

- `docs/NEXT-STAGE-22-STUDENT-SAFETY-OUTPUT-CONTRACT-YYYY-MM-DD.md`

### Done When

Known student-output leak/format classes are tested or documented.

## Stage 23 — Parent Privacy Regression Pass

**Timebox:** 24–48 hours  
**Goal:** prevent privacy regressions as analytics expand.

### Work

- Test parent cannot access raw chat, unrelated child, teacher/admin data.
- Verify dashboard remains aggregate-only.
- Add tests for any new parent endpoints.

### Verification

- Parent backend tests.
- Parent dashboard E2E.

### Deliverables

- `docs/NEXT-STAGE-23-PARENT-PRIVACY-REGRESSION-YYYY-MM-DD.md`

### Done When

Parent privacy boundary remains explicit and tested.

## Stage 24 — Teacher/Admin RBAC Regression Pass

**Timebox:** 24–48 hours  
**Goal:** keep role boundaries safe.

### Work

- Verify student/parent cannot access teacher/admin endpoints.
- Verify teachers cannot edit others’ unpublished materials.
- Verify admin audit/ops endpoints require admin.

### Verification

- Backend RBAC tests.
- Targeted browser/API smoke.

### Deliverables

- `docs/NEXT-STAGE-24-TEACHER-ADMIN-RBAC-REGRESSION-YYYY-MM-DD.md`

### Done When

Teacher/admin role boundaries are current and tested.

## Stage 25 — Backup Restore Drill And Release Runbook

**Timebox:** 24–48 hours  
**Goal:** prove recovery and release operations are repeatable.

### Work

- Run safe restore drill according to existing backup scripts/runbook.
- Verify offsite manifest visibility.
- Update release/rollback runbooks where stale.
- Do not touch production data destructively.

### Verification

- Restore drill output.
- Backup/offsite manifest hash verification.

### Deliverables

- `docs/NEXT-STAGE-25-BACKUP-RESTORE-RELEASE-RUNBOOK-YYYY-MM-DD.md`

### Done When

Recovery path is current and documented.

## Stage 26 — Full Pilot Rehearsal V2

**Timebox:** 24–48 hours  
**Goal:** rerun cross-role pilot after all next-phase changes.

### Work

- Student: diagnostic/topic/wrong/right answer.
- Parent: dashboard/privacy.
- Teacher: analytics/readiness/QA status.
- Admin: audit/realtime/monitoring.
- Verify exports/report links if present.

### Verification

- Cross-role Playwright suite.
- `/ready HTTP=200` after run.
- No 5xx after run.

### Deliverables

- `docs/NEXT-STAGE-26-FULL-PILOT-REHEARSAL-V2-YYYY-MM-DD.md`

### Done When

System is ready for next manual pilot wave.

## Stage 27 — Next 3-Month Execution Report

**Timebox:** 24 hours  
**Goal:** summarize this new plan’s execution results.

### Work

- Summarize what changed, what deployed, what tests passed.
- Include subject readiness matrix.
- Include known risks and human review items.

### Verification

- References actual docs/commits/prod marker.
- Prod health included.

### Deliverables

- `docs/NEXT-THREE-MONTH-EXECUTION-REPORT-YYYY-MM-DD.md`

### Done When

Igor can read one file and understand the next 3-month phase outcome.

## Stage 28 — Next Final Manual Pilot Plan

**Timebox:** 24 hours  
**Goal:** produce updated manual testing instructions after this next plan.

### Work

- Update manual routes, scenarios, expected results, blockers, screenshot checklist, and feedback template.
- Include subject readiness and promotion decisions.
- Avoid secrets.

### Verification

- Referenced routes exist.
- No secrets in plan.
- Prod marker/health recorded.

### Deliverables

- `docs/NEXT-FINAL-MANUAL-PILOT-PLAN-YYYY-MM-DD.md`

### Done When

A new session can stop execution and hand Igor a current manual pilot plan.

---

# Definition Of Done For This New 3-Month Plan

The new plan is complete only when:

- Production is healthy: `/ready HTTP=200`.
- Current production marker is recorded.
- Math pilot feedback is collected and triaged.
- Release marker hygiene has a runbook or is fixed.
- Algebra/Geometry source/RAG status is evidence-backed.
- Parent, teacher, admin, and student boundaries are retested.
- Monitoring/backup/recovery status is documented.
- Security/privacy review is refreshed.
- Final execution report exists.
- Final manual pilot plan exists.
- No secrets are written to docs.
