# Stage 7 Multi-Subject Expansion MVP Report

Date: 2026-08-11
Branch: `mvp-rescue`
Current production marker: `8a14fac`

## Result

Stage 7 — **Multi-Subject Expansion MVP** remains complete and now has fresh production verification plus dedicated browser regression coverage.

The app exposes all seeded subjects while clearly marking which subject is actually MVP-ready for pilot testing and which subjects are preview-only.

## Completed Scope

### Backend

`SubjectOut` exposes support/readiness fields:

- `mvp_status`
- `support_note`
- `rag_ready`
- `practice_ready`

Current MVP-ready rule:

- `Математика (6 класс - повторение пройденного материала)` → `mvp_ready`, `rag_ready=true`, `practice_ready=true`
- all other seeded subjects → `preview`, `rag_ready=false`, `practice_ready=false`

Production API verification on 2026-08-11 returned 12 subjects with exactly this split: one MVP-ready math repeat subject and 11 preview subjects.

### Frontend

Subjects UI is verified to show:

- `/subjects` gallery with `MVP-ready` / `Preview` badges;
- math repeat card with ready support note;
- preview subject card with “materials/RAG not confirmed” warning;
- `/subjects/[id]` readiness panel showing Ready/RAG/Practice state for math;
- `/subjects/[id]` readiness panel showing Preview/RAG OFF/Practice Preview state for non-ready subjects.

### RAG Safety

Existing RAG guard remains active:

- RAG context and sources are enabled only for the prepared math repeat subject.
- Other subjects do not receive misleading math sources.
- Preview subjects are navigation-visible but not content-ready pilot subjects.

## New Regression Coverage

Added:

```text
apps/frontend/e2e/multi-subject-readiness.spec.ts
```

Covered behavior:

- student login;
- `/subjects` loads subject gallery;
- math repeat subject shows `MVP-ready` and ready support note;
- Algebra preview subject shows `Preview` and unconfirmed materials/RAG warning;
- math subject detail page shows readiness panel and active RAG/practice state;
- preview subject detail page shows preview warning and RAG OFF state.

## Verification Commands And Outcomes

Backend contract:

```bash
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest tests/test_subjects.py -q
# 9 passed
```

Frontend regression:

```bash
cd /root/workspace/ai-tutor/apps/frontend
BASE_URL=https://192.168.1.86 npx playwright test e2e/multi-subject-readiness.spec.ts --reporter=line
# 1 passed

npm run typecheck
# tsc --noEmit passed
```

Production API smoke:

```text
GET https://localhost/api/v1/subjects as kirill@example.com
subject_count 12
math repeat subject: mvp_status=mvp_ready, rag_ready=true, practice_ready=true
all 11 other seeded subjects: mvp_status=preview, rag_ready=false, practice_ready=false
```

MVP student flow stayed green on production:

```bash
cd /root/workspace/ai-tutor/apps/frontend
BASE_URL=https://192.168.1.86 npx playwright test e2e/mvp-student-flow.spec.ts --reporter=line
# 2 passed
```

## MVP Status

Stage 7 is complete for MVP purposes.

Known limitation: non-math subjects are exposed as preview navigation only. They are not yet content-ready pilot subjects; adding them to pilot scope still requires real curriculum import, source material upload, topic-scoped RAG, fallback bank coverage, smoke, and manual walkthrough.
