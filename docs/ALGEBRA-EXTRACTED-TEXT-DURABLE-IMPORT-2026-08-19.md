# Algebra Extracted Text Durable Import — 2026-08-19

## Scope

This increment runs verified exact-asset extracted text rows through a durable local SQLite target.

It writes all 19 extracted-text material/chunk rows into a caller-owned local SQLite file, reads them back for metadata audit/readiness snapshot, and supports cleanup.

It does **not** use the configured application database, deploy code, mutate production, create production RAG chunks, or promote Algebra.

Algebra remains `preview`.

## Added

### `apps/backend/scripts/algebra_extracted_text_durable_import.py`

Durable local adapter for extracted-text rows produced by `algebra_extracted_text_import_dry_run`.

It provides:

- `run_extracted_text_import_target(db_path=..., probe_manifest=...)` — commits extracted-text material/chunk rows to a local SQLite file;
- `read_extracted_text_audit_rows(db_path=...)` — reads committed rows back in `rag_metadata_audit` shape;
- `cleanup_extracted_text_import_target(db_path=...)` — removes local rehearsal rows while preserving the DB file;
- CLI flags `--probe-json`, `--db-path`, and `--cleanup`.

Safety properties:

```json
{
  "mode": "extracted_text_durable_local_import_target",
  "production_mutation": false,
  "promotion_allowed": false,
  "readiness_decision": "keep_preview_extracted_text_durable_local_only"
}
```

### `apps/backend/tests/test_algebra_extracted_text_durable_import.py`

TDD coverage:

- extracted-text durable import writes probe rows and audits cleanly;
- read-back rows feed the local readiness snapshot and still block promotion;
- cleanup removes all rows.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_extracted_text_durable_import.py -q
ModuleNotFoundError: No module named 'scripts.algebra_extracted_text_durable_import'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_extracted_text_durable_import.py -q
3 passed, 3 warnings
```

## Durable Local Run Evidence

Command:

```text
rm -f /tmp/ai-tutor-algebra-extracted-text-import.sqlite3 \
  /tmp/algebra-extracted-text-durable-result.json \
  /tmp/algebra-extracted-text-readiness.json

PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_extracted_text_durable_import \
  --probe-json /tmp/algebra-exact-asset-probe-full.json \
  --db-path /tmp/ai-tutor-algebra-extracted-text-import.sqlite3 \
  > /tmp/algebra-extracted-text-durable-result.json
```

Result:

```json
{
  "mode": "extracted_text_durable_local_import_target",
  "db_path": "/tmp/ai-tutor-algebra-extracted-text-import.sqlite3",
  "topic_count": 19,
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
  "readiness_decision": "keep_preview_extracted_text_durable_local_only"
}
```

Local readiness snapshot:

```json
{
  "subject": "algebra",
  "source": "durable_local_sqlite_import_target",
  "route_topic_count": 19,
  "source_topic_count": 19,
  "practice_topic_count": 19,
  "metadata_bad_rows": 0,
  "metadata_ok_rows": 19,
  "metadata_rows_checked": 19,
  "mvp_status": "preview",
  "route_ready": true,
  "rag_ready": false,
  "practice_ready": true,
  "promotion_allowed": false,
  "blockers": [
    "import_not_production_or_staging",
    "smoke_not_passed"
  ],
  "import_mode": "durable_local_sqlite_import_target",
  "production_mutation": false,
  "smoke_passed": false
}
```

## Verification Gates

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/scripts/algebra_extracted_text_durable_import.py \
  apps/backend/scripts/algebra_extracted_text_import_dry_run.py \
  apps/backend/scripts/algebra_local_readiness_snapshot.py \
  apps/backend/tests/test_algebra_extracted_text_durable_import.py
exit 0

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_exact_asset_fetch_probe.py \
  apps/backend/tests/test_algebra_extracted_text_import_dry_run.py \
  apps/backend/tests/test_algebra_extracted_text_durable_import.py \
  apps/backend/tests/test_algebra_local_readiness_snapshot.py \
  apps/backend/tests/test_algebra_promotion_gate.py \
  apps/backend/tests/test_rag_metadata_audit.py -q
23 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health checked read-only at `2026-08-19 14:37 MSK`:

```text
READY_HTTP=200
HEALTH_HTTP=200
```

## Decision

The Algebra pipeline now has a durable local target using verified extracted exact-asset text rather than generic rehearsal text or curated snippet rows.

This remains local-only and does not promote Algebra. Next gate: run the extracted-text durable rows through a staging/prod-safe import plan only after backup/offsite verification and explicit smoke coverage. Until then, Algebra remains `preview`.
