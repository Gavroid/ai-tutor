# Algebra Promotion Gate — 2026-08-19

## Scope

This increment adds an explicit fail-closed Algebra promotion gate.

The gate prevents local rehearsal evidence from accidentally being treated as production/staging readiness. It does not change runtime subject readiness, deploy code, mutate production, or promote Algebra.

Algebra remains `preview`; local durable import evidence is not enough for `rag_ready=true`.

## Added

### `apps/backend/scripts/algebra_promotion_gate.py`

A conservative evaluator for Algebra readiness promotion.

Inputs:

- route topic count;
- source topic count;
- practice topic count;
- metadata audit bad row count;
- import mode;
- production mutation flag;
- smoke result flag.

Fail-closed blockers:

- route coverage incomplete;
- source coverage incomplete;
- practice coverage incomplete;
- metadata audit failed;
- import is local-only / not staging or production;
- production import not actually executed;
- smoke not passed.

Local rehearsal modes such as `durable_local_sqlite_import_target`, `disposable_sqlite_import_rehearsal`, and `local_import_dry_run_only` cannot promote Algebra even when they have `19/19` local coverage and metadata audit `0` bad rows.

### `apps/backend/tests/test_algebra_promotion_gate.py`

TDD coverage:

- full local durable rehearsal remains blocked and keeps Algebra preview;
- staging/prod-like import can become `mvp_ready_candidate` only when all gates pass;
- partial coverage and metadata failures block promotion.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_promotion_gate.py -q
ModuleNotFoundError: No module named 'scripts.algebra_promotion_gate'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_promotion_gate.py -q
3 passed, 3 warnings
```

## CLI Evidence

Local durable rehearsal stays blocked:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_promotion_gate \
  --route-topic-count 19 \
  --source-topic-count 19 \
  --practice-topic-count 19 \
  --metadata-bad-rows 0 \
  --import-mode durable_local_sqlite_import_target

LOCAL_RC=2
{'mvp_status': 'preview', 'rag_ready': False, 'promotion_allowed': False, 'blockers': ['import_not_production_or_staging', 'smoke_not_passed']}
```

Staging-like import with smoke passed becomes only a candidate:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_promotion_gate \
  --route-topic-count 19 \
  --source-topic-count 19 \
  --practice-topic-count 19 \
  --metadata-bad-rows 0 \
  --import-mode staging_import \
  --smoke-passed

STAGING_RC=0
{'mvp_status': 'mvp_ready_candidate', 'rag_ready': True, 'promotion_allowed': True, 'blockers': []}
```

## Verification Gates

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/scripts/algebra_promotion_gate.py \
  apps/backend/scripts/algebra_durable_local_import_target.py

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_promotion_gate.py \
  apps/backend/tests/test_algebra_durable_local_import_target.py \
  apps/backend/tests/test_algebra_disposable_import_session.py \
  apps/backend/tests/test_algebra_local_import_dry_run.py \
  apps/backend/tests/test_rag_metadata_audit.py \
  apps/backend/tests/test_subjects.py::test_list_subjects_returns_seed -q
19 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health checked at `2026-08-19 07:20 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Decision

The Algebra pipeline now has an explicit promotion guardrail: local dry-runs, durable local SQLite imports, and disposable rehearsals cannot accidentally mark Algebra as ready.

Next gate remains staging or production-safe targeted import only after backup/offsite verification and smoke coverage. Until then Algebra stays `preview`.
