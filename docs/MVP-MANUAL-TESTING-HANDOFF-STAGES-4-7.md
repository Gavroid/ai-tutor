# MVP Manual Testing Handoff — Stages 4–7

Date: 2026-08-12
Branch: `mvp-rescue`

## Scope Ready For Manual Testing

The following MVP stages are closed and ready for manual QA:

- Stage 4 — Teacher Content Workflow MVP
- Stage 5 — Parent / Progress Product MVP
- Stage 6 — Reliability / Ops Hardening MVP
- Stage 7 — Multi-Subject Expansion MVP

## Recommended Manual Test Order

### 1. Operator preflight

Login as admin and verify:

- `/api/v1/admin/ops/status` returns HTTP 200.
- `checks.database.ok = true`.
- `checks.redis.ok = true`.
- `checks.uploads.ok = true`.
- `checks.teacher_registry.ok = true`.

Expected ops/status checks:

- `checks.database.ok = true`;
- `checks.redis.ok = true`;
- `checks.uploads.ok = true`;
- `checks.teacher_registry.ok = true`;
- `checks.backup.cron_exists = true`;
- `checks.backup.script_exists = true`;
- `checks.commit_marker.ok = true`.

Current production marker at handoff time: `8674981`; backend runtime includes parent-link and pending-invite fixes through `8674981`.

### 2. Student MVP flow

Use the prepared math subject only:

- `Математика (6 класс - повторение пройденного материала)`

Check:

- explain works;
- verified source appears for prepared topics;
- practice works;
- wrong answer then correction works;
- after correct answer, `Следующее задание` works;
- clear resets chat/practice/feedback.

### 3. Teacher content workflow

Open:

- `/teacher/topics`
- `/teacher/topics/{topic_id}`

Check:

- readiness table loads;
- topic row links to detail editor;
- followups JSON can be edited and saved;
- fallback JSON can be edited and saved;
- manual QA status can be saved;
- safe RAG rebuild job returns status.

Use a test topic or revert changes after smoke.

### 4. Parent / progress dashboard

Open:

- `/parents`
- `/parent/dashboard/{studentId}`

Check:

- summary card appears under header;
- recommendations appear;
- weak topic recommendation links to topic if present;
- privacy note remains visible;
- no AI chat content is exposed to parent.



Current parent test account for manual QA:

- `parent-e2e@example.com` has linked child `Student E2E`;
- `/parent/dashboard/20` is expected to load;
- parent dashboard API returned HTTP 200 and included `privacy_note`;
- pre-mutation DB backup: `/opt/ai-tutor/deploy/backup/_manual/qa-parent-link-pre-20260811.sql`.

### 5. Multi-subject scope

Open:

- `/subjects`
- one prepared math subject;
- one non-math subject.

Check:

- math repeat subject shows `MVP-ready`;
- non-ready subjects show `Preview`;
- preview subject page warns that materials/RAG are not confirmed.

## If Something Fails

Send:

- screenshot;
- URL;
- role/account used;
- action clicked;
- expected vs actual.

Prioritize bugs in this order:

1. student hot path;
2. wrong/misleading sources;
3. practice answer correctness;
4. teacher save/revert workflow;
5. parent privacy leak;
6. preview subjects mislabelled as ready.
