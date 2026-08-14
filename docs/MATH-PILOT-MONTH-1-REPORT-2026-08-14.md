# Math Pilot Month 1 Report — 2026-08-14

## Executive Decision

Recommendation: continue math pilot polish and start Month 2 Algebra/Geometry audits in preview mode.

Rationale:

- Math MVP is technically ready: route, diagnostic, sources, followups, fallback practice, student loop, parent report, teacher review, and adaptive recommendation are all in place.
- Production is healthy after the latest targeted deploys.
- Remaining math gaps are editorial/manual QA, not blocking technical gaps.
- Algebra/Geometry should not be marked ready yet; Month 2 should start with scope audits and preview route planning.

## Production State

Latest verified production state during Stage 10:

```text
production marker: 6e698a0
/ready HTTP=200
/health HTTP=200
backend/db/frontend/prometheus/redis running healthy; grafana/proxy running
```

Important note: production marker was not advanced during Stages 03–09 because work used controlled targeted seed/rebuild deploys instead of the full release marker workflow. The deployed runtime includes the targeted changes documented in Stage reports.

## Completed Month 1 Scope

| Stage | Status | Evidence |
|---|---:|---|
| Stage 01 — Pilot baseline/repo hygiene | Complete | `docs/CURRENT-PILOT-STATUS-2026-08-14.md` |
| Stage 02 — Editorial review framework | Complete | `docs/MATH-EDITORIAL-REVIEW-MATRIX-2026-08-14.md` |
| Stage 03 — Fallback quality pass 1 | Complete | `docs/MATH-FALLBACK-STAGE-03-SMOKE-REPORT-2026-08-14.md` |
| Stage 04 — Fallback quality completion | Complete | `docs/MATH-FALLBACK-QUALITY-REPORT-2026-08-14.md` |
| Stage 05 — Live pilot script | Complete | `docs/MATH-LIVE-PILOT-SCRIPT-2026-08-14.md` |
| Stage 06 — Student lesson loop polish | Complete | `docs/STAGE-06-STUDENT-LESSON-LOOP-POLISH-REPORT-2026-08-14.md` |
| Stage 07 — Parent report V2 | Complete | `docs/STAGE-07-PARENT-REPORT-V2-2026-08-14.md` |
| Stage 08 — Teacher review mode V2 | Complete | `docs/STAGE-08-TEACHER-REVIEW-MODE-V2-2026-08-14.md` |
| Stage 09 — Adaptive progression pass 1 | Complete | `docs/STAGE-09-ADAPTIVE-PROGRESSION-PASS-1-2026-08-14.md` |

## What Works

- Math route plan exists and covers 42 topics: `/api/v1/subjects/3/route-plan`.
- Diagnostic uses balanced checkpoint topics and exposes `correct_answer` for controlled diagnostic flow.
- Math source/followup baseline is `42/42`.
- Editorial matrix covers all 42 route topics.
- First deterministic fallback variant is now hand-authored for `42/42` topics.
- Student topic page now guides the loop with clear next-step CTAs:
  - explanation → practice;
  - wrong answer → retry;
  - correct answer → next task or next route topic.
- Parent dashboard now gives non-technical cards:
  - what improved;
  - where help is needed;
  - what to do tomorrow;
  - route progress.
- Teacher readiness view now includes route metadata, checkpoint filter, route tier filter, and manual status filter.
- Adaptive progression is math-route-aware for `subject_id=3`.

## What Failed / Was Fixed

- Stage 03/04 fallback seed originally covered only a subset of topics. Fixed to `42/42` first fallback variants.
- Stage 05 E2E expected obsolete follow-up labels. Fixed to current backend-managed labels: `Ещё пример`, `Проверь меня`, `Дай задачу`.
- Stage 06/07/08 Playwright selectors hit hidden duplicate responsive DOM on Prism/Split pages. Fixed by scoping selectors to visible table/card surfaces.
- Parent/teacher real-login E2E hit auth rate-limit `429` after repeated test runs. Product login UI now displays the backend 429 detail, and V2 UI checks use mocked auth where auth is not the test target.
- Production host has no `npm` in PATH. Frontend deploys now use Docker Compose build/restart only.

## Quality Gaps

- Editorial status is a framework, not completed human review. Matrix has initial statuses: `approved=16`, `needs_example=23`, `needs_easy_task=3`.
- Second and third fallback variants are still generic safe/checkable helper tasks; first variant is the polished one.
- Full release marker workflow needs a dedicated production tree hygiene stage before broad `rsync --delete` release deploys.
- Algebra/Geometry are still outside ready scope and must remain preview until audited.

## Student Evidence

Latest Stage 10 gate:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/mvp-student-flow.spec.ts --grep "student can open topic" --project=chromium
1 passed (13.4s)
```

This verifies:

- student login;
- subject/topic navigation;
- explanation response;
- no raw JSON / `correct_answer` leak in generated exercise response;
- wrong-answer feedback;
- correct-answer feedback;
- clean chat output;
- current follow-up labels;
- no copy button in lesson/chat/practice flow.

## Parent / Teacher Observations

Parent:

- Parent report V2 has actionable cards and explicit privacy note.
- Raw AI chat is not surfaced to parent UI.
- Parent dashboard V2 smoke passed with mocked dashboard payload to avoid login rate-limit noise.

Teacher:

- Teacher review V2 smoke passed after selector tightening.
- Readiness endpoint now returns route order/tier/focus/checkpoint metadata.
- Filters exist for priority, route tier, checkpoint-only, and manual QA status.

## Test Evidence

Stage 10 verification commands:

```text
cd apps/backend
.venv/bin/pytest tests/test_sprint8_recommend_next.py tests/test_math_route_plan.py tests/test_math_fallback_seed.py tests/test_health.py -q
26 passed, 15 warnings in 8.69s

cd apps/frontend
npm run typecheck
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/mvp-student-flow.spec.ts --grep "student can open topic" --project=chromium
1 passed (13.4s)
```

Representative production API smoke from Stage 09:

```text
/api/v1/progress/recommend-next?subject_id=3 HTTP=200
response subset: {'topic_id': 203, 'subject_id': 3, 'reason': 'weak_topic', 'mastery_score': 0.16666666666666666}
```

## Backups Used During Month 1 Execution

Production backup/offsite verification was run before each production mutation. Recent relevant manifests:

```text
manifest-20260814T152458Z.md5
manifest-20260814T153114Z.md5
manifest-20260814T154640Z.md5
manifest-20260814T160137Z.md5
manifest-20260814T161507Z.md5
manifest-20260814T164757Z.md5
manifest-20260814T165300Z.md5
```

All listed stage reports document offsite hash verification where production mutation occurred.

## Decision Gate

Decision: proceed to Month 2, but keep Algebra/Geometry in honest preview until each subject has route + sources + fallback practice + smoke evidence.

Recommended next stage: Stage 11 — Algebra/Geometry Scope Audit.

Do not start by adding content blindly. First produce DB/API-derived audit of subject IDs, topic counts, source materials, RAG chunks, fallback tasks, followups, and readiness state.

## Remaining Non-Blockers

- Clean or commit untracked stakeholder presentation intermediate artifacts only in a dedicated repo hygiene stage.
- Resolve production working tree hygiene before a full release marker deploy.
- Human/manual editorial review is still required for `needs_example` and `needs_easy_task` math topics.
- Align printed/exported parent report HTML with Parent Report V2 cards later.
