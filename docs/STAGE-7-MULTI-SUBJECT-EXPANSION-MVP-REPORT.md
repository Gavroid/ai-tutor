# Stage 7 Multi-Subject Expansion MVP Report

Date: 2026-07-31
Branch: `mvp-rescue`

## Result

Stage 7 — **Multi-Subject Expansion MVP** is complete.

The app can expose all seeded subjects while clearly marking which subject is actually MVP-ready for pilot testing and which subjects are preview-only.

## Completed Scope

### Backend

Extended `SubjectOut` with support/readiness fields:

- `mvp_status`
- `support_note`
- `rag_ready`
- `practice_ready`

Current MVP-ready rule:

- `Математика (6 класс - повторение пройденного материала)` → `mvp_ready`
- all other seeded subjects → `preview`

This keeps expansion honest: users can navigate all subjects, but pilot testing remains scoped to prepared math content.

### Frontend

Updated subjects UI:

- `/subjects` now shows `MVP-ready` or `Preview` badge per subject.
- `/subjects/[id]` now shows a clear support notice:
  - green MVP-ready notice for prepared math;
  - amber preview notice for non-ready subjects.

### RAG safety

Existing RAG guard remains active:

- RAG context and sources are enabled only for the prepared math repeat subject.
- Other subjects do not receive misleading math sources.

## Verification

Local gates:

- Backend targeted: `109 passed`
- Frontend typecheck: passed
- Frontend build: passed
- MVP E2E: `2 passed`

## MVP Status

Stage 7 is complete for MVP purposes.

Known limitation: non-math subjects are exposed as preview navigation only. They are not yet content-ready pilot subjects.
