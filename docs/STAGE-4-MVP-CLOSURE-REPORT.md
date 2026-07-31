# Stage 4 MVP Closure Report — Teacher Content Workflow

Date: 2026-07-31
Branch: `mvp-rescue`

## Result

Stage 4 — **Teacher Content Workflow MVP** is complete.

This is not a full CMS yet. It is the minimum usable teacher/admin workflow that removes the biggest remaining operational bottleneck: editing pilot content knobs only through code/SSH.

## Completed Scope

### Stage 4.1 — Read-only readiness dashboard

Completed earlier and retained:

- `GET /api/v1/teacher/topics/readiness`
- `/teacher/topics` page
- P0/P1/P2 filters
- summary metrics
- per-topic readiness table

### Stage 4.2 — Backend-managed follow-up buttons

Completed:

- Public endpoint:
  - `GET /api/v1/topics/{topic_id}/followups`
- Teacher endpoints:
  - `GET /api/v1/teacher/topics/{topic_id}/followups`
  - `PUT /api/v1/teacher/topics/{topic_id}/followups`
- Student topic UI now loads follow-up buttons from backend API instead of frontend hardcode.
- Teacher edits are stored in `teacher_content_registry.json` under `UPLOAD_DIR`.
- Updates write audit events.

### Stage 4.3 — Backend-managed practice fallback bank

Completed:

- Teacher endpoints:
  - `GET /api/v1/teacher/topics/{topic_id}/fallbacks`
  - `PUT /api/v1/teacher/topics/{topic_id}/fallbacks`
- `AIService.generate_exercise(...)` can use registry fallback rows when AI output is invalid/off-topic.
- `/api/v2/exercises/generate` passes `topic_id` into `AIService` so registry fallbacks can apply.
- Legacy code fallback remains as emergency fallback if registry has no active rows.

### Stage 4.4 — Teacher edit/review API + audit

Completed:

- Teacher endpoint:
  - `PATCH /api/v1/teacher/topics/{topic_id}/status`
- Status fields supported:
  - `explain_status`
  - `practice_status`
  - `source_status`
  - `manual_qa_status`
  - `notes`
- Mutations write audit events through existing audit log chain.

### Stage 4.5 — Safe RAG rebuild job MVP

Completed as safe MVP operation:

- Teacher endpoints:
  - `POST /api/v1/teacher/rag/rebuild-topic/{topic_id}`
  - `GET /api/v1/teacher/rag/jobs/{job_id}`
- Current behavior is a safe dry-run verification:
  - counts current topic-scoped chunks;
  - records job status;
  - writes audit event;
  - does not delete or rewrite chunks.

This is intentionally non-destructive for MVP. A real background destructive rebuild worker can be added later.

## Frontend

Added:

- `/teacher/topics/[id]`

The teacher topic detail page supports:

- editing follow-up buttons as JSON;
- editing fallback tasks as JSON;
- updating manual QA status/notes;
- launching safe RAG rebuild job;
- viewing RAG job JSON result.

Updated:

- `/teacher/topics` rows now link to `/teacher/topics/{topic_id}`.
- `/topics/{id}` student page now loads followups from backend API.

## Persistence

Stage 4 MVP uses a lightweight JSON registry:

```text
UPLOAD_DIR/teacher_content_registry.json
```

Stored sections:

- `followups`
- `fallbacks`
- `topic_status`
- `rag_jobs`

Reason: fast MVP delivery without a DB migration-heavy CMS rewrite. Future Stage 4.x can move this registry into relational tables while keeping API contracts stable.

## Verification

Local gates:

- Backend targeted: `97 passed`
- Frontend typecheck: passed
- Frontend build: passed
- MVP E2E: `2 passed`

## Known Limitations

- Editing UI uses JSON textareas, not polished form controls.
- Registry is file-backed, not table-backed.
- RAG rebuild is safe dry-run, not destructive reindex worker.
- Fallback/followup defaults still exist in code as emergency fallback.
- Audit is mutation-level, not field-level diff UI.

## MVP Status

Stage 4 is complete for MVP purposes.

Next recommended stage: manual teacher/admin smoke and then Stage 5 — parent/progress product or Stage 4.x table-backed content registry.
