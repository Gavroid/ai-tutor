# Algebra Restored-Backup Staging Rehearsal — 2026-08-19

## Scope

This increment runs the Algebra extracted-text import path against a temporary PostgreSQL staging database restored from a fresh production backup.

It does **not** mutate the production database, deploy code, advance markers, or promote Algebra. The temporary staging DB was created in a separate Docker container and removed after the rehearsal.

Algebra remains `preview` in production.

## Fresh Backup / Offsite / Restore Evidence

Production backup run:

```text
RUN_BACKUP_START=2026-08-19T11:58:23+00:00
Backup DB: db-20260819T115823Z.sql.gz
Backup uploads: uploads-20260819T115823Z.tar.gz
Manifest: manifest-20260819T115823Z.md5
```

Offsite verification:

```text
OFFSITE: uploaded 120 files (all size-verified)
OFFSITE OK: hash verified manifest-20260819T115823Z.md5 (a977e812ef76bb84679d94112401b3f3)
OFFSITE OK: 120 uploaded, 0 deleted, 205 total on SMB
```

Restore drill:

```text
RESTORE DRILL PASSED
Backup: db-20260819T115823Z.sql.gz
Size: 12815945 bytes
Tables: 32
Users: 14
```

Production read-only health remained OK:

```text
READY_HTTP=200
HEALTH_HTTP=200
```

## Temporary Staging DB

A temporary PostgreSQL container was created on the production host, bound to localhost only:

```text
container=ai-tutor-algebra-staging-db
port=127.0.0.1:55432
database=tutor
source_backup=db-20260819T115823Z.sql.gz
```

Pre-import counts in restored staging DB:

```text
tables=32
users=14
algebra_materials_before=0
algebra_chunks_before=0
```

## Import Rehearsal

The local committed runner was executed from the dev workspace through an SSH tunnel to the temporary staging DB:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_production_import \
  --manifest-json /tmp/algebra-extracted-text-import.json \
  --target-env staging \
  --db-url postgresql+psycopg2://tutor:tutor@127.0.0.1:55432/tutor \
  --execute
```

Result:

```json
{
  "subject": "algebra",
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

Read-back counts from temporary staging DB:

```text
algebra_materials_after=19
algebra_chunks_after=19
algebra_source_topic_count_after=19
```

RAG metadata audit against the temporary staging DB:

```json
{
  "summary": {
    "rows_checked": 19,
    "ok_rows": 19,
    "bad_rows": 0,
    "problems": {}
  },
  "bad_rows": []
}
```

Endpoint-like local readiness calculation against the temporary staging DB showed source/RAG coverage but did not promote production:

```text
code=algebra
mvp_status=preview
route_ready=True
rag_ready=True
source_topic_count=19
practice_ready=False
practice_topic_count=0
```

Note: `practice_ready=False` here is an artifact of running app readiness code from the local workspace against the restored DB without the production runtime content registry context. The read-only production API still reports Algebra practice coverage `19/19`; production source/RAG remains `0/19` because production DB was not mutated.

## Production Import Gate

Production preflight remains blocked:

```text
marker=6e698a0
branch=master
head=cb99f2b
dirty_count=155
```

The import execution gate result on current production facts:

```json
{
  "decision": "block_import",
  "import_allowed": false,
  "blockers": [
    "target_tree_dirty",
    "target_branch_mismatch",
    "target_head_mismatch"
  ],
  "backup_verified": true,
  "offsite_verified": true,
  "target_tree_clean": false,
  "branch_aligned": false,
  "head_aligned": false,
  "smoke_plan_defined": true,
  "production_mutation": false
}
```

## Cleanup

Temporary artifacts on the production host were removed:

```text
/tmp/algebra_production_import.py
/tmp/algebra-extracted-text-import.json
/tmp/algebra-postgres-staging-import.json
/opt/ai-tutor/apps/backend/scripts/algebra_production_import.py
container ai-tutor-algebra-staging-db
```

Post-clean production dirty count stayed unchanged at `155`, confirming the rehearsal did not introduce a new persistent production tree delta.

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
  apps/backend/tests/test_algebra_exact_asset_fetch_probe.py \
  apps/backend/tests/test_rag_metadata_audit.py -q
28 passed, 3 warnings
```

## Decision

The Algebra source/RAG import path is now verified against a restored production backup in a temporary PostgreSQL staging container. Production import remains intentionally blocked until production tree, branch, head, and marker hygiene are resolved or an explicit targeted production-import procedure is approved with a precise rollback plan.
