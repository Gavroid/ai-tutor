# Algebra Disposable Import Rehearsal — 2026-08-18

## Scope

This increment adds an isolated disposable import rehearsal for the Algebra source/RAG pipeline.

It inserts the local 19-topic dry-run material/chunk rows into an in-memory SQLite database, runs metadata audit, then rolls the transaction back and verifies cleanup.

It does **not** touch the configured application database, write production rows, create production RAG chunks, deploy code, mutate production, or promote Algebra.

## Added

### `apps/backend/scripts/algebra_disposable_import_session.py`

A disposable SQLite rehearsal adapter that:

1. builds the full Algebra local import dry-run manifest;
2. creates isolated in-memory rehearsal tables;
3. inserts material-shaped rows;
4. inserts chunk-shaped rows;
5. runs `rag_metadata_audit` over the generated audit rows;
6. rolls back the transaction;
7. verifies material/chunk counts return to zero.

Safety flags stay explicit:

```json
{
  "mode": "disposable_sqlite_import_rehearsal",
  "production_mutation": false,
  "promotion_allowed": false,
  "readiness_decision": "keep_preview_disposable_rehearsal_only"
}
```

### `apps/backend/tests/test_algebra_disposable_import_session.py`

TDD coverage:

- 3-topic rehearsal writes rows, audits metadata, and rolls back to zero rows;
- default rehearsal covers all 19 Algebra topics, audits metadata, and rolls back to zero rows.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_disposable_import_session.py -q
ModuleNotFoundError: No module named 'scripts.algebra_disposable_import_session'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_disposable_import_session.py -q
2 passed, 3 warnings
```

## Rehearsal Evidence

Command:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_disposable_import_session \
  > /tmp/algebra-disposable-import.json
```

Result:

```text
{
  'mode': 'disposable_sqlite_import_rehearsal',
  'topic_count': 19,
  'material_count_before_rollback': 19,
  'chunk_count_before_rollback': 19,
  'material_count_after_rollback': 0,
  'chunk_count_after_rollback': 0,
  'production_mutation': False,
  'promotion_allowed': False,
  'readiness_decision': 'keep_preview_disposable_rehearsal_only'
}
```

Metadata audit result:

```text
{'rows_checked': 19, 'ok_rows': 19, 'bad_rows': 0, 'problems': {}}
```

## Verification Gates

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/scripts/algebra_disposable_import_session.py \
  apps/backend/scripts/algebra_local_import_dry_run.py

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_disposable_import_session.py \
  apps/backend/tests/test_algebra_local_import_dry_run.py \
  apps/backend/tests/test_rag_metadata_audit.py \
  apps/backend/tests/test_algebra_source_extraction_probe.py \
  apps/backend/tests/test_algebra_source_import_dry_run.py \
  apps/backend/tests/test_algebra_fallback_seed.py \
  apps/backend/tests/test_math_route_plan.py::test_algebra_route_plan_endpoint_returns_preview_route \
  apps/backend/tests/test_subjects.py::test_list_subjects_returns_seed -q
25 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health checked at `2026-08-18 23:02 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Decision

The Algebra pipeline now proves the 19-topic material/chunk rows can be inserted into an isolated SQL session, pass metadata audit, and roll back cleanly.

Algebra remains `preview`; `rag_ready=false` until a deliberate local/staging real import writes durable rows and passes `rag_metadata_audit` against the actual generated chunks. Production import would require backup/offsite verification first.
