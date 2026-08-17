# Next Stage 07 — Teacher Content QA Evidence Pass — 2026-08-17

## Scope

Stage 07 verified the teacher workflow in the required order:

1. Teacher analytics summary.
2. Readiness matrix.
3. Topic detail / readiness controls.
4. Material QA status workflow.
5. Admin audit filtering for QA transitions.

No production deploy or production data mutation was required. Production remained in targeted deploy mode and marker was not advanced.

## Local Changes

### Backend Evidence

Updated `apps/backend/tests/test_teacher.py` to make the existing content QA workflow test stricter:

- `needs_review` material cannot publish directly.
- `blocked` material cannot publish directly.
- Both blocked publish attempts return `409` with the `teacher_approved` prerequisite visible.
- Admin audit filter `action=material.quality_status.update&entity=learning_material` returns the QA transition trail.
- Audit details prove transitions:
  - `ai_generated -> needs_review`
  - `needs_review -> blocked`
  - `blocked -> approved`
- Audit details retain teacher note evidence for the blocked transition.

### Frontend Evidence

Expanded `apps/frontend/e2e/teacher-review-v2.spec.ts`:

- Keeps the existing readiness matrix smoke for route metadata and filters.
- Adds a full teacher review smoke:
  - `/teacher` analytics panel loads aggregate-only learning analytics.
  - `/teacher/topics` readiness matrix links to topic detail.
  - `/teacher/topics/187` topic detail shows publication readiness and manual QA controls.
  - `/teacher/materials/501` material QA workflow supports `needs_review` and `blocked` states.
  - Publish button is hidden for `needs_review` and `blocked` states.
  - Teacher UI does not expose raw AI chat, raw JSON, or `correct_answer` in the checked flow.

## Verification

### Backend

```text
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest tests/test_teacher.py::test_quality_workflow_status_transition_and_audit -q
1 passed, 10 warnings

.venv/bin/pytest tests/test_teacher.py tests/test_health.py -q
46 passed, 73 warnings
```

### Frontend

```text
cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

npx playwright test e2e/teacher-review-v2.spec.ts --project=chromium
2 passed

BASE_URL=https://192.168.1.86 npx playwright test e2e/teacher-review-v2.spec.ts --project=chromium
2 passed
```

The LAN Playwright run uses mocked teacher/auth/API responses for workflow UI coverage; it does not mutate production data.

### Production Read-Only Health

Checked at `2026-08-17 15:14 MSK`.

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
backend/frontend/db/redis/prometheus healthy
grafana/proxy running
```

## Findings

- Backend already enforced the material status state machine correctly; the gap was evidence granularity.
- Admin audit filtering already worked; tests now prove QA transition details and notes, not just event existence.
- Teacher UI critical path is test-covered from analytics to readiness, topic detail, and material QA.
- Parent privacy boundary was not touched; teacher analytics smoke asserts aggregate-only copy and no raw AI chat exposure.
- No changes were made to Nightscout or external medical systems.

## Production Decision

No targeted deploy was performed:

- Stage 07 changes are test/evidence only.
- Production health is already green.
- Production tree remains dirty/on `master` per handoff, so broad deploy and marker advancement remain out of scope.

## Done Criteria

- Teacher workflow tests: complete.
- Teacher review Playwright smoke: complete.
- Admin audit filter for QA transition: complete.
- Blocked / needs-review cannot publish: complete.
- Report: complete.
- Commit: pending at report creation.
