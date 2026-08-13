# AI-Tutor Further Development Plan

_Last updated: 2026-08-13 19:25 MSK_

This plan starts from the current pilot-ready MVP state after manual QA closure, mobile fixes, admin/teacher/parent UI cleanup, Realtime monitoring stabilization, and disk cleanup. It intentionally excludes Telegram/email distribution work.

## Current Baseline

- Production app: `https://school.431a.ru`
- Current branch: `mvp-rescue`
- Manual QA checklist: closed in `docs/pilot-walkthrough-notes.md`
- Design source of truth: `docs/PRISM-DESIGN-PATTERNS.md`
- Historical QA handoff archived: `docs/HANDOFF-QA-BUGFIX-NEXT-CONTEXT-2026-08-11.md`
- Backend currently runs `uvicorn --workers 1` so in-process Prometheus metrics stay consistent until multiprocess metrics are implemented.

## Principles

1. Preserve the accepted Prism/Split visual style.
2. Do not change production behavior without a backup and verification.
3. Prefer small, testable refactors over broad rewrites.
4. Keep parent privacy boundary: aggregate progress only, no raw AI chat exposure.
5. Avoid adding Telegram/email distribution features in this phase.
6. For student-facing AI output, never allow raw JSON, raw markdown tables, `<think>`, broken math markers, or unreadable mobile formatting.

---

## Phase 1 — Release Freeze and Documentation Hygiene

**Goal:** make the current pilot-ready state auditable and easy to restore.

### Work

- Create a pilot release tag after final confirmation.
- Update `README.md` to match reality:
  - current domain;
  - actual admin/teacher/parent/student flows;
  - current monitoring behavior;
  - backend workers = 1, with reason;
  - backup/offsite status.
- Update `docs/architecture.md`:
  - `/admin` is one route with internal tabs;
  - `/admin/invites` and `/admin/realtime` are redirects/compatibility routes;
  - Realtime is fixed snapshot + manual refresh, not WebSocket streaming;
  - `proxy.ts` handles canonical host redirect.
- Update `docs/DEPLOY-GUIDE.md`:
  - current deploy commands;
  - backup before deploy;
  - disk cleanup commands and safe order;
  - restore-friendly backup paths.
- Update `docs/PRISM-DESIGN-PATTERNS.md` with the final mobile chat/readability and admin/teacher cleanup rules.

### Done When

- Docs match the production architecture.
- A new agent can deploy, restore, and validate without needing chat history.
- No stale references to `/admin?tab=...` as desired UI, WS Realtime as primary UI transport, or backend `workers=4` as current state.

### Estimate

6–8 hours.

---

## Phase 2 — Frontend Refactor Without Visual Changes

**Goal:** make future UI changes safer by removing giant files and scattered override layers.

### Work

#### 2.1 Split `globals.css`

Current `apps/frontend/app/globals.css` is large and contains many historical override layers. Split into:

```text
apps/frontend/app/styles/
  prism-base.css
  prism-layout.css
  prism-buttons.css
  prism-console.css
  split-lesson.css
  mobile.css
  legacy-overrides.css
```

`globals.css` should import these files in a clear order.

#### 2.2 Extract Admin Components

Split `apps/frontend/app/admin/page.tsx` into:

```text
AdminTabs
AuditTab
UsersTab
StatsTab
ToolsTab
InvitesTab
RealtimeTab
RealtimeKpi
```

Keep visible behavior unchanged.

#### 2.3 Extract Lesson Components

Split `apps/frontend/app/topics/[id]/page.tsx` into:

```text
LessonRail
TutorChat
ChatMessage
ChatComposer
PracticePanel
MobileLessonTabs
```

Keep accepted mobile/desktop behavior unchanged.

### Done When

- `npm run typecheck` passes.
- `npm run build` passes.
- Playwright smoke passes on:
  - `/subjects`
  - `/subjects/[id]`
  - `/topics/[id]`
  - `/admin`
  - `/teacher`
  - `/parents`
- No user-visible style regression.

### Estimate

18–28 hours.

---

## Phase 3 — Observability and Monitoring Upgrade

**Goal:** make monitoring useful, stable, and not misleading.

### Work

- Keep backend at `workers=1` until Prometheus multiprocess mode is properly implemented.
- Add explicit Realtime timestamp in UI:
  - `Снимок: HH:MM:SS MSK`
- Separate expected 4xx from real problems:
  - expected/soft: missing draft `404`, unauthenticated checks before login;
  - actionable: unexpected `403`, `429` spikes, new unknown `404`, any `5xx`.
- Improve Prometheus/Grafana panels:
  - HTTP by route/status;
  - AI tokens by role;
  - AI requests by mode/status;
  - backend RAM MiB;
  - backup age and offsite status;
  - `/ready` status and latency;
  - Redis and DB health.
- Later subphase: implement Prometheus multiprocess mode before returning `workers=4`.

### Done When

- Admin Realtime labels match the real source of each number.
- Expected 4xx do not look like product errors.
- There is a clear path to return multi-worker safely.

### Estimate

10–16 hours for MVP monitoring cleanup.

Prometheus multiprocess: additional 10–18 hours.

---

## Phase 4 — Backend Reliability and Security Debt

**Goal:** reduce production risk while keeping the pilot simple.

### Work

- Add rate limit to `/auth/register` by IP/email.
- Add audit-log retention policy:
  - configurable retention period;
  - cron/script or backend maintenance command;
  - tests for old records.
- Harden trusted proxy / `X-Forwarded-For` handling:
  - only trust configured proxy CIDRs;
  - ignore spoofed XFF from untrusted sources.
- Clarify and test admin budget controls.
- Add targeted tests for canonical host redirect and expected 4xx classification.

### Done When

- Brute-force/self-register risk is lower.
- Audit table growth is controlled.
- IP-based logic is not spoofable through fake headers.

### Estimate

14–22 hours.

---

## Phase 5 — RAG and Content Quality

**Goal:** improve answer quality and reduce hallucinations/weak explanations.

### Work

- Create persistent RAG storage plan:
  - phase A: persisted chunks + BM25/hybrid search;
  - phase B: pgvector or external embedding API.
- Add quality gates for AI output:
  - no raw JSON;
  - no `<think>` blocks;
  - no broken markdown/math;
  - markdown tables render as tables;
  - sources stay short and readable.
- Build a topic quality matrix for priority P0/P1/P2 topics.
- Add browser smoke for representative P0 topics:
  - explain;
  - practice;
  - wrong answer;
  - correct answer;
  - parent summary update.

### Done When

- Priority topics produce readable, source-grounded, student-friendly answers.
- The system has measurable checks for broken AI output.
- RAG state survives restarts or has a clear rebuild path.

### Estimate

24–40 hours for phase A.

pgvector/external embeddings: additional 24–40 hours.

---

## Phase 6 — Student Learning Loop

**Goal:** make the product feel like a tutor, not only a chat page.

### Work

- Add lesson progress indicator by topic.
- Add “next best step” after explanation/practice.
- Add better practice loop:
  - multiple tasks in sequence;
  - adaptive difficulty;
  - short error explanation;
  - no answer leakage too early.
- Add end-of-lesson summary:
  - what was learned;
  - what needs repetition;
  - recommended next topic/practice.
- Improve spaced repetition UI for due topics.

### Done When

- A student can complete a small learning loop without manual guidance.
- The system recommends what to do next.
- Parent/teacher views can summarize learning progress from structured events.

### Estimate

28–48 hours.

---

## Phase 7 — Parent Product Layer

**Goal:** make parent dashboard useful for decisions, not just visible.

### Work

- Improve dashboard storytelling:
  - recent progress;
  - weak topics;
  - activity trend;
  - suggested support actions.
- Add privacy-safe weekly summary page inside the app.
- Add export/download option, if needed, without Telegram/email distribution.
- Add parent settings for what to display.

### Done When

- Parent can understand what happened this week in under one minute.
- No raw chat is exposed.
- The dashboard recommends concrete next actions.

### Estimate

16–28 hours.

---

## Phase 8 — Teacher Product Layer

**Goal:** make teacher tools practical for maintaining content quality.

### Work

- Improve material workflow queue:
  - generated;
  - needs review;
  - approved;
  - published.
- Replace JSON textareas in topic editor with structured forms where practical.
- Add content completeness checks:
  - concept explanation;
  - examples;
  - practice tasks;
  - mini-test;
  - flashcards/followups.
- Add batch review for P0 topics first.

### Done When

- Teacher/admin can see which topics are ready and why.
- Editing content does not require raw JSON knowledge.
- Published content has minimum completeness checks.

### Estimate

24–40 hours.

---

## Phase 9 — Operations and Disk Hygiene

**Goal:** keep production recoverable and clean.

### Work

- Formalize disk cleanup runbook:
  - Docker build cache cleanup;
  - dangling volume inspection;
  - journald vacuum;
  - image prune rules;
  - what never to delete.
- Add post-backup cleanup checklist.
- Add periodic disk report script, read-only by default.
- Decide retention policy for local backups after confirming offsite status.

### Done When

- Disk usage does not creep unnoticed.
- Cleanup can be repeated safely after full backup.
- Restore-critical data is never removed by cleanup.

### Estimate

6–10 hours.

---

## Recommended Sequence

1. Phase 1 — Freeze/docs hygiene.
2. Phase 2 — Frontend refactor without UI changes.
3. Phase 3 — Monitoring cleanup.
4. Phase 4 — Reliability/security debt.
5. Phase 5 — RAG/content quality.
6. Phase 6 — Student learning loop.
7. Phase 7 — Parent product layer.
8. Phase 8 — Teacher product layer.
9. Phase 9 — Ops/disk hygiene.

## Near-Term 2-Week Slice

If only 2 weeks are available, do:

1. Phase 1 docs freeze.
2. Phase 2 CSS split + admin/topic component extraction.
3. Phase 3 monitoring cleanup, without full multiprocess.
4. Phase 4 register rate-limit + audit retention.
5. One small Phase 5 topic-quality slice for P0 topics.
