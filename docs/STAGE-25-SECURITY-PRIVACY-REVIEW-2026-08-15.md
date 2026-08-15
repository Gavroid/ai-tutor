# Stage 25 — Security And Privacy Review — 2026-08-15

## Scope

Stage 25 goal: reduce pilot privacy/security risk and explicitly verify the boundaries that matter before manual testing.

## Reviewed Areas

- Auth and RBAC paths.
- Parent-child privacy boundary.
- Teacher/admin material workflow RBAC.
- Secure exercise anti-leak contract.
- Subject readiness honesty for preview subjects.
- Production browser/API smoke.

## Backend Security Tests

Executed security/privacy regression subset:

```text
cd apps/backend
.venv/bin/pytest   tests/test_pilot_secure_exercises.py   tests/test_parents_materials.py   tests/test_teacher.py::test_generate_blocks_student   tests/test_teacher.py::test_generate_blocks_parent   tests/test_teacher.py::test_list_materials_blocks_student   tests/test_teacher.py::test_get_material_blocks_other_teacher   tests/test_subjects.py::test_list_subjects_returns_seed   tests/test_health.py -q
27 passed, 29 warnings
```

What this verifies:

- Generated exercise safe projection does not expose `correct_answer` or `explanation` before submit.
- Parent invite requires parent role.
- Parent dashboard flow uses aggregate progress.
- Teacher generation blocks student/parent.
- Teacher material list blocks student.
- Teacher cannot open another teacher’s unpublished material.
- Subject readiness remains honest:
  - Math ready;
  - Algebra/Geometry preview with `rag_ready=false`.

## Browser / UI Privacy Smoke

Production LAN smoke:

```text
Student MVP flow: 1 passed
Parent dashboard V2 privacy/actionability: 1 passed
Teacher review mode V2 no raw JSON: 1 passed
```

What this verifies:

- Student practice flow remains clean and does not expose raw JSON in the UI.
- Parent dashboard shows actionable aggregate report cards and no raw AI chat.
- Teacher readiness matrix shows route metadata and filters without raw JSON or `correct_answer` leakage.

## Production API Checks

Production `/api/v1/subjects` readiness smoke:

```text
SUBJECTS_HTTP=200
algebra: preview, route_ready=true, rag_ready=false, practice_ready=true, source_topic_count=0/19
geom: preview, route_ready=true, rag_ready=false, practice_ready=true, source_topic_count=0/13
math: mvp_ready, route_ready=true, rag_ready=true, practice_ready=true, source_topic_count=42/42
```

Production health:

```text
/ready HTTP=200
/health HTTP=200
```

## Privacy Boundaries

| Boundary | Status | Evidence |
|---|---|---|
| Parent cannot see raw AI chat | Verified | Parent dashboard V2 E2E checks no raw chat/user/assistant text |
| Student cannot see server answer before submit | Verified by regression | Secure exercise safe projection excludes `correct_answer`; student flow E2E checks clean feedback |
| Preview subjects are not overstated | Verified | Algebra/Geometry are `preview`, `rag_ready=false`, `source_topic_count=0` |
| Teacher/admin RBAC | Verified | Student/parent blocked from teacher generation; student blocked from material list; teacher blocked from another teacher's unpublished material |
| Admin/ops health | Verified | `/ready=200`, `/health=200`, Stage 23 Prometheus ops metrics in place |

## Remaining Risks

- Production marker remains `6e698a0` because this plan uses targeted deploys while production release tree is not fully aligned. This is tracked as release-hygiene debt, not a runtime privacy blocker.
- Baseline pilot accounts exist; manual testers must use operator-provided credentials and avoid writing passwords/tokens into screenshots or reports.
- Algebra/Geometry source/RAG readiness remains blocked by lack of verified sources, so they must stay preview.

## Decision

No security/privacy blocker found for manual Math pilot. Algebra and Geometry remain preview until verified source/RAG coverage exists.

## Next Stage

Proceed to Stage 26 — Cross-Role Pilot Dress Rehearsal.
