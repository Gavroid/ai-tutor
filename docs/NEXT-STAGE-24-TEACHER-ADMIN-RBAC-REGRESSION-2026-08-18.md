# Next Stage 24 — Teacher/Admin RBAC Regression Pass — 2026-08-18

## Decision

Stage 24 is complete. Teacher/admin role boundaries are current and covered by backend regression tests plus browser/API smoke.

Runtime code did not need changes. Existing `require_teacher_or_admin`, `require_admin`, and `generated_by` owner checks already enforce the boundary; Stage 24 added explicit regression coverage so future teacher/admin UI or API expansion does not weaken it silently.

## Files Added

- `apps/backend/tests/test_teacher_admin_rbac_stage24.py`
- `apps/frontend/e2e/teacher-admin-rbac-stage24.spec.ts`

## Backend RBAC Coverage

The Stage 24 backend fixture creates:

- student;
- parent;
- teacher 1;
- teacher 2;
- admin;
- teacher-owned unpublished draft;
- other-teacher unpublished draft;
- other-teacher published library item.

Assertions prove:

- student and parent cannot access teacher endpoints;
- student, parent, and teacher cannot access admin endpoints;
- teacher cannot view/edit/approve/publish/unpublish/delete another teacher’s unpublished draft;
- teacher bulk approve returns `forbidden` for another teacher’s material;
- teacher can view shared published library material but cannot mutate it;
- admin can access audit/users/stats/realtime endpoints;
- admin can edit any teacher material.

## Browser/API Smoke Coverage

The new Playwright spec logs in real roles and checks:

- student and parent receive `403` on teacher/admin API surfaces;
- teacher receives `200` on teacher readiness/materials;
- teacher receives `403` on admin audit/users/stats/realtime;
- admin receives `200` on audit/users/stats/realtime.

## Verification

Backend regression pass:

```text
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest \
  tests/test_teacher_admin_rbac_stage24.py \
  tests/test_teacher.py::test_get_material_blocks_other_teacher \
  tests/test_teacher.py::test_delete_other_teachers_material_blocked \
  tests/test_admin.py::test_audit_log_requires_admin \
  tests/test_sprint35_teacher_flow.py::test_bulk_approve_non_teacher_403 -q
10 passed, 68 warnings
```

Frontend local browser pass:

```text
cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
npx playwright test e2e/teacher-admin-rbac-stage24.spec.ts --project=chromium
3 passed
```

LAN production browser pass:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/teacher-admin-rbac-stage24.spec.ts --project=chromium
3 passed
```

Production health:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
backend healthy
frontend healthy
db healthy
redis healthy
prometheus healthy
grafana/proxy running
```

## Production Impact

None.

- No runtime code changes.
- No deploy.
- No DB migration.
- No production data mutation.
- No backup/offsite required for Stage 24 because production was not mutated.
- No Nightscout or external medical system touched.

## Done Criteria

- Student/parent cannot access teacher/admin endpoints: complete.
- Teacher cannot edit or publish others’ unpublished materials: complete.
- Admin audit/ops endpoints require admin: complete.
- Backend RBAC tests: complete.
- Targeted browser/API smoke: complete.
- Commit: pending at report creation.
