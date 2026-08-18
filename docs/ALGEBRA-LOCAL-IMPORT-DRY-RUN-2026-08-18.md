# Algebra Local Import Dry Run — 2026-08-18

## Scope

This increment converts the Algebra subset fixture path into a local-only import rehearsal.

It creates disposable material-shaped and chunk-shaped JSON records, then audits their metadata. It does **not** write database rows, create real RAG chunks, deploy code, mutate production, or promote Algebra.

Algebra remains `preview`; `promotion_allowed=false`.

## Added

### `apps/backend/scripts/algebra_local_import_dry_run.py`

Local-only import rehearsal that builds:

- `materials` — rows shaped like future `learning_materials` imports;
- `chunks` — rows shaped like future `rag_chunks` imports;
- `audit_rows` — rows directly consumable by `scripts.rag_metadata_audit`.

Default subset stays intentionally small:

- topic `34` — numeric expressions;
- topic `37` — one-variable linear equations;
- topic `41` — exponent definition/properties.

Safety flags:

```json
{
  "mode": "local_import_dry_run_only",
  "production_mutation": false,
  "db_write": false,
  "rag_write": false,
  "promotion_allowed": false,
  "readiness_decision": "keep_preview_local_dry_run_only"
}
```

### `apps/backend/tests/test_algebra_local_import_dry_run.py`

TDD coverage:

- local import dry-run builds material/chunk-shaped rows for the subset;
- generated audit rows pass the existing metadata contract;
- readiness decision remains preview / not promotable.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_local_import_dry_run.py -q
ModuleNotFoundError: No module named 'scripts.algebra_local_import_dry_run'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_local_import_dry_run.py -q
3 passed, 3 warnings
```

## Dry-Run Evidence

Command:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_local_import_dry_run \
  --out /tmp/algebra-local-import-dry-run.json
```

Output:

```text
{"ok": true, "out": "/tmp/algebra-local-import-dry-run.json", "topic_count": 3, "material_count": 3, "chunk_count": 3, "readiness_decision": "keep_preview_local_dry_run_only"}
```

Manifest summary:

```text
{'mode': 'local_import_dry_run_only', 'subject': 'algebra', 'topic_count': 3, 'db_write': False, 'rag_write': False, 'readiness_decision': 'keep_preview_local_dry_run_only'}
{'materials': 3, 'chunks': 3}
```

Metadata audit over generated `audit_rows`:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.rag_metadata_audit \
  --subject-code algebra \
  --input-json /tmp/algebra-local-import-audit-rows.json \
  --json > /tmp/algebra-local-import-audit.json

{'rows_checked': 3, 'ok_rows': 3, 'bad_rows': 0, 'problems': {}}
```

## Verification Gates

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/scripts/algebra_local_import_dry_run.py \
  apps/backend/scripts/algebra_rag_subset_fixture.py

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_local_import_dry_run.py \
  apps/backend/tests/test_algebra_rag_subset_fixture.py \
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

Production health checked at `2026-08-18 22:48 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Decision

Algebra now has a local-only import rehearsal that produces material/chunk-shaped rows and passes the RAG metadata contract for the 3-topic subset.

This is still not production RAG readiness. Next gate: add an importer adapter that can write the same rows into an isolated disposable test database/session and prove rollback/cleanup, or expand the fixture to all 19 topics while preserving `rag_ready=false` until a real import is intentionally executed.
