# Algebra Asset Snippet Import Dry Run — 2026-08-19

## Scope

This increment builds material/chunk-shaped dry-run rows from exact Algebra asset snippets.

It moves the Algebra pipeline one step beyond generic rehearsal text: rows now derive from exact asset snippet metadata while remaining local-only.

No production deploy, production data mutation, database write, real RAG chunk creation, or readiness promotion was performed.

Algebra remains `preview`.

## Added

### `apps/backend/scripts/algebra_asset_snippet_import_dry_run.py`

Local dry-run builder that converts `algebra_asset_extraction_snippets` rows into:

- material-shaped rows;
- chunk-shaped rows;
- `rag_metadata_audit`-compatible audit rows.

Each generated row retains:

- topic id/focus;
- exact asset URL;
- source section;
- license;
- attribution;
- extraction mode;
- no-mutation flags.

Safety flags:

```json
{
  "mode": "asset_snippet_import_dry_run_only",
  "production_mutation": false,
  "db_write": false,
  "rag_write": false,
  "promotion_allowed": false,
  "readiness_decision": "keep_preview_asset_snippet_dry_run_only"
}
```

### `apps/backend/tests/test_algebra_asset_snippet_import_dry_run.py`

TDD coverage:

- manifest builds 19 material/chunk rows from exact snippets;
- generated audit rows pass RAG metadata audit;
- readiness decision remains preview / not promotable.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_asset_snippet_import_dry_run.py -q
ModuleNotFoundError: No module named 'scripts.algebra_asset_snippet_import_dry_run'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_asset_snippet_import_dry_run.py -q
3 passed, 3 warnings
```

## Dry-Run Evidence

Command:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_asset_snippet_import_dry_run \
  --out /tmp/algebra-asset-snippet-import.json
```

Output:

```text
{"ok": true, "out": "/tmp/algebra-asset-snippet-import.json", "topic_count": 19, "material_count": 19, "chunk_count": 19, "readiness_decision": "keep_preview_asset_snippet_dry_run_only"}
```

Manifest summary:

```text
{'mode': 'asset_snippet_import_dry_run_only', 'subject': 'algebra', 'topic_count': 19, 'db_write': False, 'rag_write': False, 'readiness_decision': 'keep_preview_asset_snippet_dry_run_only'}
{'materials': 19, 'chunks': 19}
```

Metadata audit:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.rag_metadata_audit \
  --subject-code algebra \
  --input-json /tmp/algebra-asset-snippet-audit-rows.json \
  --json > /tmp/algebra-asset-snippet-audit.json

{'rows_checked': 19, 'ok_rows': 19, 'bad_rows': 0, 'problems': {}}
```

## Verification Gates

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/scripts/algebra_asset_snippet_import_dry_run.py \
  apps/backend/scripts/algebra_asset_extraction_snippets.py

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_asset_snippet_import_dry_run.py \
  apps/backend/tests/test_algebra_asset_extraction_snippets.py \
  apps/backend/tests/test_algebra_source_asset_manifest.py \
  apps/backend/tests/test_algebra_local_readiness_snapshot.py \
  apps/backend/tests/test_rag_metadata_audit.py \
  apps/backend/tests/test_subjects.py::test_list_subjects_returns_seed -q
18 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health checked at `2026-08-19 07:42 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Decision

The Algebra pipeline can now generate source-asset-specific material/chunk-shaped rows and pass metadata audit for all 19 topics.

Next gate: feed these asset-snippet rows into the durable local SQLite target / local readiness snapshot path, then keep Algebra preview unless a real staging or production-safe import with smoke is executed.
