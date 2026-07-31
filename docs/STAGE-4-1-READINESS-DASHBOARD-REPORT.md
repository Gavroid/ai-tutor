# Stage 4.1 Readiness Dashboard Report

Date: 2026-07-31
Branch: `mvp-rescue`

## Result

Stage 4.1 — **Read-only Teacher Topic Readiness Dashboard** is complete.

Teacher/admin users can now view a read-only readiness table for the math topic set. The dashboard does not mutate content. It gives visibility into topic readiness before Stage 4.2/4.3 move follow-ups and fallback practice tasks out of code and into data.

## Backend

Added endpoint:

```http
GET /api/v1/teacher/topics/readiness?subject_id=3&priority=P0|P1|P2
```

Authorization:

- `teacher` allowed
- `admin` allowed
- `student` / `parent` blocked by existing `require_teacher_or_admin()` dependency

Response rows include:

- `topic_id`
- `topic_name`
- `section_id`
- `section_name`
- `subject_id`
- `subject_name`
- `priority`
- `material_count`
- `chunk_count`
- `fallback_count`
- `followup_count`
- `explain_status`
- `practice_status`
- `source_status`
- `manual_qa_status`

## Frontend

Added page:

```text
/teacher/topics
```

Features:

- summary cards:
  - topics
  - materials
  - RAG chunks
  - fallback count
  - follow-up count
- filter chips:
  - all
  - P0
  - P1
  - P2
- readiness table with per-topic statuses
- link from `/teacher` to `/teacher/topics`

## Tests

Added backend tests:

- `test_teacher_topics_readiness_blocks_student`
- `test_teacher_topics_readiness_returns_topic_rows`

Verification:

- Backend targeted: `64 passed`
- Frontend typecheck: passed
- Frontend build: passed
- MVP E2E: `2 passed`

## Current Limitations

- Readiness statuses are derived from known MVP topic ids and current code-backed coverage.
- No database table for readiness state yet.
- No teacher editing yet.
- Follow-up/fallback counts are derived from current hardcoded MVP coverage.

These are intentional for Stage 4.1. Stage 4.2 and Stage 4.3 will make follow-ups and fallback practice tasks data-driven.

## Next Stage

Stage 4.2 — move topic follow-up buttons out of frontend hardcoding and into backend-managed data.
