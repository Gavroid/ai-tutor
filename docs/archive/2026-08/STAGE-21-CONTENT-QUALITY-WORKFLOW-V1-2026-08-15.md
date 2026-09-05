# Stage 21 — Content Quality Workflow V1 — 2026-08-15

## Scope

Stage 21 goal: make content QA repeatable instead of relying on implicit spreadsheet-like status tracking.

## Completed

- Extended material status model with explicit QA states:
  - `draft`;
  - `ai_generated`;
  - `needs_review`;
  - `approved` public transition, stored as legacy-compatible `teacher_approved`;
  - `published`;
  - `blocked`.
- Added backend endpoint:
  - `POST /api/v1/teacher/materials/{material_id}/quality-status`.
- Added audit logging for sensitive quality status changes:
  - action: `material.quality_status.update`;
  - entity: `learning_material`;
  - details include old status, requested status, stored status, and note.
- Updated teacher material detail UI with a `Content QA Workflow` panel:
  - note field;
  - `Needs review`;
  - `Blocked`;
  - `Approved`.
- Updated teacher material list status labels/colors for `needs_review` and `blocked`.

## Compatibility

Existing workflow endpoints remain compatible:

- `POST /teacher/materials/{id}/approve` still returns/stores `teacher_approved`.
- `POST /teacher/materials/{id}/publish` still requires `teacher_approved`.
- `approved` in the new QA endpoint maps to `teacher_approved` to avoid breaking existing student/library publish flow.
- `needs_review` and `blocked` prevent publishing until explicitly moved back to approved.

## TDD Evidence

RED before implementation:

```text
POST /api/v1/teacher/materials/{id}/quality-status
expected 200, got 404
```

GREEN after implementation:

```text
cd apps/backend
.venv/bin/pytest tests/test_teacher.py::test_quality_workflow_status_transition_and_audit -q
1 passed
```

Targeted regression gates:

```text
cd apps/backend
.venv/bin/pytest   tests/test_teacher.py::test_quality_workflow_status_transition_and_audit   tests/test_teacher.py::test_workflow_generate_approve_publish   tests/test_teacher.py::test_workflow_cannot_publish_without_approve   tests/test_health.py -q
11 passed
```

Frontend gates:

```text
cd apps/frontend
npm run typecheck
npm run build
Compiled successfully
```

## Production Backup / Offsite

Required backup was run before production deploy:

```text
backup manifest: /opt/ai-tutor/deploy/backup/_out/manifest-20260815T065715Z.md5
OFFSITE OK: hash verified manifest-20260815T065715Z.md5
SMB total after upload: 223 files
```

## Production Deploy

Targeted backend/frontend deploy:

```text
docker compose build backend frontend
docker compose up -d --no-deps backend frontend
backend_health=healthy
frontend_health=healthy
/ready HTTP=200
```

## Production Smoke

Because production had no teacher-generated editable material available, a temporary smoke material was created after backup, then removed after verification.

```text
SMOKE_MATERIAL=51
QUALITY_HTTP=200
{'status': 'needs_review', 'id': 51}
DELETE_HTTP=200
{'quality_audit_count': 1}
READY_HTTP=200
```

## Privacy / Safety

- The workflow only changes material QA status and audit metadata.
- No raw student AI chats or parent-private data are exposed.
- The temporary production smoke material was deleted after audit verification.

## Known Limitations

- The underlying DB column is still a string, so new statuses require no migration; a future hardening pass can add DB-level enum/check constraints.
- UI exposes the primary Stage 21 transitions. Full status history is currently visible via admin audit log, not a dedicated material timeline panel.

## Next Stage

Proceed to Stage 22 — Manual Testing Harness.
