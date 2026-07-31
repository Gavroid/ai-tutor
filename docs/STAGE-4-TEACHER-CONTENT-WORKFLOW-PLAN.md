# Stage 4 Plan — Teacher Content Workflow MVP

Date: 2026-07-31 15:49 MSK
Branch: `mvp-rescue`
Previous stage: Stage 3B UX Polish — closed

## Goal

Build the first usable **Teacher Content Workflow MVP** so future content changes do not require manual code edits, SQL, SSH, or ad-hoc RAG rebuild scripts.

The product must move from “developer-managed content” to “teacher/admin-managed content with safe publication gates”.

## Why This Is Next

The student MVP is now usable enough for controlled pilot:

- 42 real math topics exist.
- P0/P1 smoke gates are green.
- Verified page-level sources are visible.
- Practice has deterministic fallbacks for pilot-critical topics.
- Lesson UX has follow-up buttons and next-practice flow.

The main remaining bottleneck is operational/content workflow:

- topic/fallback/follow-up logic is still partly hardcoded;
- RAG rebuild requires backend scripts and SSH;
- teachers cannot review or publish generated content in a controlled flow;
- adding another subject would repeat manual rescue work.

## Stage 4 MVP Scope

### In scope

1. Teacher/admin content dashboard for math topics.
2. Per-topic readiness status.
3. Draft → review → publish workflow.
4. Structured follow-up/subtopic metadata.
5. Practice fallback bank editable outside code, at least for pilot topics.
6. RAG material/index status visible in UI.
7. Safe “rebuild topic RAG” operation for one topic or one subject.
8. Audit log for content changes.

### Out of scope

- Full multi-subject expansion.
- Quote-level semantic citations.
- Full WYSIWYG lesson authoring.
- Parent/progress product expansion.
- Replacing all existing hardcoded fallbacks in one pass.

## Proposed Data Model

### `topic_content_status`

Tracks readiness per topic.

Fields:

- `topic_id`
- `explain_status`: `todo | smoke_ok | manual_ok | blocked`
- `practice_status`: `todo | smoke_ok | manual_ok | blocked`
- `source_status`: `hidden | verified | blocked`
- `manual_qa_status`: `todo | ok | issue`
- `last_reviewed_by`
- `last_reviewed_at`
- `notes`

### `topic_followups`

Structured buttons after explanations.

Fields:

- `id`
- `topic_id`
- `label`
- `prompt`
- `kind`: `choice | next`
- `order_index`
- `is_active`

Examples:

- `Среднее чисел`
- `Средняя скорость`
- `Средний вес`
- `Далее`
- `Второй способ`

### `topic_practice_fallbacks`

Editable deterministic practice tasks.

Fields:

- `id`
- `topic_id`
- `question_text`
- `type`
- `options_json`
- `correct_answer`
- `explanation`
- `typical_mistakes_json`
- `difficulty`
- `order_index`
- `is_active`

### `content_audit_events`

Content-specific audit log.

Fields:

- `id`
- `actor_user_id`
- `topic_id`
- `action`
- `before_json`
- `after_json`
- `created_at`

## Stage 4 Implementation Plan

### Phase 4.1 — Read-only teacher readiness dashboard

Goal: show current state without mutating content.

Tasks:

1. Backend endpoint: `GET /api/v1/teacher/topics/readiness?subject_id=3`.
2. Return topic list with:
   - topic id/name/section;
   - chunk count;
   - fallback count;
   - follow-up count;
   - explain/practice/source/manual QA status.
3. Frontend page: `/teacher/topics`.
4. Add filters: `P0/P1/P2`, `needs review`, `manual issue`.
5. Tests:
   - endpoint auth;
   - response includes chunk/fallback/follow-up counts;
   - frontend smoke renders topic rows.

Exit: teacher can see readiness state for all 42 math topics.

### Phase 4.2 — Move follow-up buttons out of hardcoded frontend

Goal: replace `followUpActionsForTopic(...)` hardcoding with backend data.

Tasks:

1. Add `topic_followups` table/migration.
2. Seed current MVP follow-ups:
   - topic 187: average numbers/speed/weight.
   - topic 193: try yourself / second method.
   - topic 225: next.
3. Backend endpoint includes follow-ups in `GET /api/v1/subjects/topics/{id}` or separate `/topic-followups`.
4. Frontend uses returned follow-ups.
5. Keep frontend hardcoded fallback only as emergency fallback for rollout.
6. Tests:
   - follow-up rows are returned by topic;
   - inactive rows hidden;
   - E2E still sees buttons.

Exit: follow-up buttons can be managed by content, not code.

### Phase 4.3 — Move deterministic practice fallbacks out of code

Goal: practice bank is data-driven for P0/P1 topics.

Tasks:

1. Add `topic_practice_fallbacks` table/migration.
2. Seed current P0/P1 deterministic fallback tasks.
3. Update `AIService.generate_exercise(...)`:
   - try AI structured output;
   - validate topic match;
   - if invalid, fetch fallback from DB by topic/difficulty/rotation;
   - fallback to legacy code only if DB empty.
4. Backend admin/teacher CRUD minimal endpoints.
5. Tests:
   - DB fallback used when AI invalid;
   - rotation returns different active rows;
   - inactive fallback hidden;
   - legacy fallback remains safe if DB empty.

Exit: practice edits no longer require code deploy for pilot topics.

### Phase 4.4 — Teacher edit/review/publish workflow

Goal: teacher can review and publish content states.

Tasks:

1. Add edit UI for followups and fallback tasks.
2. Add status update UI for manual QA fields.
3. Add audit events for every mutation.
4. Add role guards:
   - teacher/admin can edit;
   - student/parent cannot.
5. Tests:
   - auth/role enforcement;
   - audit row created;
   - UI can edit and save one follow-up.

Exit: teacher can safely manage pilot content without SSH/code changes.

### Phase 4.5 — Safe RAG rebuild operation

Goal: rebuild topic/subject RAG safely from UI/API.

Tasks:

1. Backend job endpoint:
   - `POST /api/v1/teacher/rag/rebuild-topic/{topic_id}`
   - `POST /api/v1/teacher/rag/rebuild-subject/{subject_id}`
2. Job must be async/background and idempotent.
3. Show job status:
   - queued/running/succeeded/failed;
   - chunks before/after;
   - errors.
4. Guardrails:
   - teacher/admin only;
   - backup/snapshot before destructive rebuild;
   - never delete non-target subject data.
5. Tests:
   - rebuild is scoped to topic/subject;
   - failure leaves old data intact;
   - status endpoint reports result.

Exit: future RAG updates do not require SSH script runs.

## Definition of Done

Stage 4 is complete when:

- teacher/admin can view all topic readiness statuses;
- follow-up buttons for current MVP topics are data-driven;
- deterministic practice fallback bank for P0/P1 is data-driven;
- content edits produce audit events;
- at least one topic can be edited and verified end-to-end without code changes;
- `/ready` remains green;
- backend targeted tests pass;
- frontend typecheck passes;
- MVP E2E passes.

## First Work Item

Start with **Phase 4.1 — Read-only teacher readiness dashboard**.

Reason: it is low-risk, improves visibility immediately, and gives us the UI/API surface needed before editing content.
