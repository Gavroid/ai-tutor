# Algebra Asset Snippet Durable Import — 2026-08-19

## Scope

This increment runs the exact-asset snippet import dry-run through a durable local SQLite target.

It writes all 19 asset-snippet material/chunk rows into a caller-owned local SQLite file, reads them back for metadata audit/readiness snapshot, and supports cleanup.

It does **not** use the configured application database, deploy code, mutate production, create production RAG chunks, or promote Algebra.

Algebra remains `preview`.

## Added

### `apps/backend/scripts/algebra_asset_snippet_durable_import.py`

Durable local adapter for asset-snippet rows.

It provides:

- `run_asset_snippet_import_target(db_path=...)` — commits exact asset-snippet material/chunk rows to a local SQLite file;
- `read_asset_snippet_audit_rows(db_path=...)` — reads committed rows back in `rag_metadata_audit` shape;
- `cleanup_asset_snippet_import_target(db_path=...)` — removes local rehearsal rows while preserving the DB file;
- CLI flags `--db-path` and `--cleanup`.

Safety properties:

```json
{
  "mode": "asset_snippet_durable_local_import_target",
  "production_mutation": false,
  "promotion_allowed": false,
  "readiness_decision": "keep_preview_asset_snippet_durable_local_only"
}
```

### `apps/backend/tests/test_algebra_asset_snippet_durable_import.py`

TDD coverage:

- asset-snippet durable import writes 19 rows and audits cleanly;
- read-back rows feed the local readiness snapshot and still block promotion;
- cleanup removes all rows.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_asset_snippet_durable_import.py -q
ModuleNotFoundError: No module named 'scripts.algebra_asset_snippet_durable_import'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_asset_snippet_durable_import.py -q
3 passed, 3 warnings
```

## Durable Local Run Evidence

Command:

```text
rm -f /tmp/ai-tutor-algebra-asset-snippet.sqlite3
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_asset_snippet_durable_import \
  --db-path /tmp/ai-tutor-algebra-asset-snippet.sqlite3 \
  > /tmp/algebra-asset-snippet-durable.json
```

Result:

```text
{
  'mode': 'asset_snippet_durable_local_import_target',
  'topic_count': 19,
  'material_count': 19,
  'chunk_count': 19,
  'production_mutation': False,
  'promotion_allowed': False,
  'readiness_decision': 'keep_preview_asset_snippet_durable_local_only'
}
```

Metadata audit:

```text
{'rows_checked': 19, 'ok_rows': 19, 'bad_rows': 0, 'problems': {}}
```

Cleanup evidence:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_asset_snippet_durable_import \
  --db-path /tmp/ai-tutor-algebra-asset-snippet.sqlite3 \
  --cleanup

{'materials_deleted': 19, 'chunks_deleted': 19, 'material_count_after': 0, 'chunk_count_after': 0}
```

## Verification Gates

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_asset_snippet_durable_import.py -q
3 passed, 3 warnings
```

## Decision

The Algebra pipeline now has a durable local target using exact asset snippets rather than generic rehearsal text.

This is still not production/staging source readiness because snippets are curated local metadata, not extracted full source text. Next gate: fetch/extract exact assets to temporary local text and validate extraction quality before any durable real import is considered.
