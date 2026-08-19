# Algebra Production-Shaped Import Runner — 2026-08-19

## Scope

This increment adds a guarded production-shaped import runner for Algebra extracted-text source/RAG rows.

It can build an import plan, dry-run a target, execute against a caller-provided staging-like DB URL, and explicitly block production writes unless `--allow-production` is set. It does **not** deploy code, mutate production, advance markers, or promote Algebra.

Algebra remains `preview`.

## Added

### `apps/backend/scripts/algebra_production_import.py`

Guarded import runner for the already-audited extracted-text manifest.

Capabilities:

- reads `materials`, `chunks`, and `audit_rows` from an extracted-text manifest;
- audits metadata before any write;
- defaults to dry-run;
- writes `learning_materials` + `rag_chunks` only when `--execute` is provided;
- blocks production writes unless `--allow-production` is explicitly provided;
- never sets `promotion_allowed=true`.

### `apps/backend/tests/test_algebra_production_import.py`

TDD coverage:

- import plan uses extracted-text rows and audits metadata;
- dry-run writes no rows;
- production execution blocks without explicit flag;
- staging SQLite execution writes material/chunk rows.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_production_import.py -q
ModuleNotFoundError: No module named 'scripts.algebra_production_import'
```

### GREEN

Initial GREEN required fixing the test fixture metadata to satisfy the existing `rag_metadata_audit` contract rather than weakening the audit.

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_production_import.py -q
4 passed, 3 warnings
```

## Staging-Shaped Rehearsal Evidence

Dry-run with the real extracted-text manifest:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_production_import \
  --manifest-json /tmp/algebra-extracted-text-import.json \
  --target-env staging \
  --db-url sqlite+pysqlite:////tmp/ai-tutor-algebra-staging-import.sqlite3
```

Result:

```json
{
  "target_env": "staging",
  "dry_run": true,
  "material_count": 19,
  "chunk_count": 19,
  "metadata_audit": {
    "rows_checked": 19,
    "ok_rows": 19,
    "bad_rows": 0,
    "problems": {}
  },
  "production_mutation": false,
  "promotion_allowed": false,
  "decision": "dry_run_only",
  "rows_written": 0,
  "blockers": []
}
```

Staging-like SQLite execution:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_production_import \
  --manifest-json /tmp/algebra-extracted-text-import.json \
  --target-env staging \
  --db-url sqlite+pysqlite:////tmp/ai-tutor-algebra-staging-import.sqlite3 \
  --execute
```

Result:

```json
{
  "target_env": "staging",
  "dry_run": false,
  "material_count": 19,
  "chunk_count": 19,
  "metadata_audit": {
    "rows_checked": 19,
    "ok_rows": 19,
    "bad_rows": 0,
    "problems": {}
  },
  "production_mutation": false,
  "promotion_allowed": false,
  "decision": "staging_import_executed",
  "rows_written": 38,
  "blockers": []
}
```

SQLite read-back:

```text
db_counts 19 19
topic_count 19
```

Production guard evidence:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_production_import \
  --manifest-json /tmp/algebra-extracted-text-import.json \
  --target-env production \
  --db-url sqlite+pysqlite:////tmp/ai-tutor-prod-block-test.sqlite3 \
  --execute

RC=2
blockers=["allow_production_not_set"]
rows_written=0
production_mutation=false
```

## Production Preflight Blocker

Read-only production preflight at `2026-08-19 14:56 MSK`:

```text
marker=6e698a0
branch=master
head=cb99f2b
dirty_count=155
containers: backend/frontend/db/redis/prometheus healthy, grafana/proxy running
latest local backup: db-20260819T030001Z.sql.gz (~13M)
latest uploads backup: uploads-20260819T030001Z.tar.gz (~19M)
offsite script has zero-size, suspicious-size, and size-mismatch guards
```

Decision: production import remains blocked because the target tree is dirty and branch/head/marker are not aligned with local `mvp-rescue` HEAD.

## Verification Gates

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/scripts/algebra_production_import.py \
  apps/backend/tests/test_algebra_production_import.py
exit 0

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_production_import.py \
  apps/backend/tests/test_algebra_import_execution_plan.py \
  apps/backend/tests/test_algebra_extracted_text_durable_import.py \
  apps/backend/tests/test_algebra_extracted_text_import_dry_run.py \
  apps/backend/tests/test_rag_metadata_audit.py -q
21 passed, 3 warnings
```

## Decision

The import path is now production-shaped and staging-rehearsed against a local SQLite target with 19 material rows and 19 RAG chunk rows. Production execution remains blocked until production tree/branch/head/marker hygiene is resolved and backup/offsite + smoke are explicitly verified immediately before import.
