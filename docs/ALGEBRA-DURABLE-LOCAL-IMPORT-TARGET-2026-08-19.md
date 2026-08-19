# Algebra Durable Local Import Target — 2026-08-19

## Scope

This increment adds a durable local SQLite import target for the Algebra Source/RAG pipeline.

Unlike the previous disposable in-memory rehearsal, this writes rows into a caller-owned local SQLite file, reads them back, audits metadata, and supports explicit cleanup. It still does **not** use the configured application database, deploy code, mutate production, create production RAG chunks, or promote Algebra readiness.

Algebra remains `preview`; `promotion_allowed=false`.

## Added

### `apps/backend/scripts/algebra_durable_local_import_target.py`

Durable local adapter for Algebra import rehearsal.

It provides:

- `run_durable_import_target(db_path=...)` — commits material/chunk-shaped rows to a local SQLite file;
- `read_durable_audit_rows(db_path=...)` — reads committed rows back in `rag_metadata_audit` input shape;
- `cleanup_durable_import_target(db_path=...)` — deletes local rehearsal rows while keeping the DB file for inspection;
- CLI flags `--db-path`, `--topic`, and `--cleanup`.

Default run covers all `19` Algebra route topics.

Safety properties:

```json
{
  "mode": "durable_local_sqlite_import_target",
  "production_mutation": false,
  "promotion_allowed": false,
  "readiness_decision": "keep_preview_durable_local_only"
}
```

### `apps/backend/tests/test_algebra_durable_local_import_target.py`

TDD coverage:

- durable local import commits 3-topic subset rows to a file-backed SQLite DB;
- rows read back from the DB pass RAG metadata audit for all 19 topics;
- cleanup removes rows and keeps the file for inspection.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_durable_local_import_target.py -q
ModuleNotFoundError: No module named 'scripts.algebra_durable_local_import_target'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_durable_local_import_target.py -q
3 passed, 3 warnings
```

## Durable Local Run Evidence

Command:

```text
rm -f /tmp/ai-tutor-algebra-durable-local.sqlite3
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_durable_local_import_target \
  --db-path /tmp/ai-tutor-algebra-durable-local.sqlite3 \
  > /tmp/algebra-durable-local-result.json
```

Result:

```text
{
  'mode': 'durable_local_sqlite_import_target',
  'topic_count': 19,
  'material_count': 19,
  'chunk_count': 19,
  'production_mutation': False,
  'promotion_allowed': False,
  'readiness_decision': 'keep_preview_durable_local_only'
}
```

Metadata audit:

```text
{'rows_checked': 19, 'ok_rows': 19, 'bad_rows': 0, 'problems': {}}
```

Cleanup evidence:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_durable_local_import_target \
  --db-path /tmp/ai-tutor-algebra-durable-local.sqlite3 \
  --cleanup

{'materials_deleted': 19, 'chunks_deleted': 19, 'material_count_after': 0, 'chunk_count_after': 0}
```

## Verification Gates

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/scripts/algebra_durable_local_import_target.py \
  apps/backend/scripts/algebra_disposable_import_session.py \
  apps/backend/scripts/algebra_local_import_dry_run.py

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_durable_local_import_target.py \
  apps/backend/tests/test_algebra_disposable_import_session.py \
  apps/backend/tests/test_algebra_local_import_dry_run.py \
  apps/backend/tests/test_algebra_rag_subset_fixture.py \
  apps/backend/tests/test_rag_metadata_audit.py \
  apps/backend/tests/test_algebra_source_extraction_probe.py \
  apps/backend/tests/test_algebra_source_import_dry_run.py \
  apps/backend/tests/test_algebra_fallback_seed.py \
  apps/backend/tests/test_math_route_plan.py::test_algebra_route_plan_endpoint_returns_preview_route \
  apps/backend/tests/test_subjects.py::test_list_subjects_returns_seed -q
31 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health checked at `2026-08-19 07:15 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Decision

The Algebra pipeline now has a durable local file-backed import target that can write all 19 topic rows, read them back, pass metadata audit, and clean up.

This still does **not** make Algebra production-ready. Next gate: run the same import target in a real staging environment or a production-safe targeted import path only after backup/offsite verification, then verify teacher readiness and subject readiness endpoints against the generated durable rows.
