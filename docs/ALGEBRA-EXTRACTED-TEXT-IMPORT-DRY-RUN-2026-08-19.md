# Algebra Extracted Text Import Dry Run — 2026-08-19

## Scope

This increment converts verified exact-asset extraction output into material/chunk-shaped local import rows.

It uses `text_excerpt` from passed `algebra_exact_asset_fetch_probe` rows, not generic rehearsal text and not curated snippet text.

It does **not** write DB rows, create real RAG chunks, deploy code, mutate production, or promote Algebra.

Algebra remains `preview`.

## Added

### `apps/backend/scripts/algebra_extracted_text_import_dry_run.py`

Local dry-run builder that consumes a probe JSON object from `algebra_exact_asset_fetch_probe` and converts passed rows into:

- material-shaped rows;
- chunk-shaped rows;
- `rag_metadata_audit`-compatible audit rows.

Failed probe rows are ignored fail-closed.

### `apps/backend/scripts/algebra_exact_asset_fetch_probe.py`

Updated passed rows to include `text_excerpt` and support `--source-text-json` / `source_text_by_url` overrides for flaky HTML pages.

This keeps IM Unit pages usable when direct Python/curl fetch stalls but `web_extract` succeeds.

### `apps/backend/tests/test_algebra_extracted_text_import_dry_run.py`

TDD coverage:

- passed probe rows produce extracted-text material/chunk rows;
- failed probe rows are ignored;
- generated audit rows pass RAG metadata audit.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_extracted_text_import_dry_run.py -q
ModuleNotFoundError: No module named 'scripts.algebra_extracted_text_import_dry_run'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_exact_asset_fetch_probe.py \
  apps/backend/tests/test_algebra_extracted_text_import_dry_run.py -q
9 passed, 3 warnings
```

## End-To-End Local Evidence

Full exact asset probe with Wallace direct PDF extraction and IM `web_extract` text override:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_exact_asset_fetch_probe \
  --source-text-json /tmp/algebra-im-source-overrides.json \
  --out /tmp/algebra-exact-asset-probe-full.json

{"ok": true, "out": "/tmp/algebra-exact-asset-probe-full.json", "asset_count": 19, "pass_count": 19, "fail_count": 0, "source_counts": {"im_first_edition": 7, "wallace_algebra": 12}}
```

Extracted-text import dry run:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_extracted_text_import_dry_run \
  --probe-json /tmp/algebra-exact-asset-probe-full.json \
  --out /tmp/algebra-extracted-text-import.json

{"ok": true, "out": "/tmp/algebra-extracted-text-import.json", "topic_count": 19, "material_count": 19, "chunk_count": 19, "readiness_decision": "keep_preview_extracted_text_dry_run_only"}
```

Metadata audit:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.rag_metadata_audit \
  --subject-code algebra \
  --input-json /tmp/algebra-extracted-text-audit-rows.json \
  --json > /tmp/algebra-extracted-text-audit.json

{'rows_checked': 19, 'ok_rows': 19, 'bad_rows': 0, 'problems': {}}
```

## Verification Gates

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/scripts/algebra_exact_asset_fetch_probe.py \
  apps/backend/scripts/algebra_extracted_text_import_dry_run.py

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_exact_asset_fetch_probe.py \
  apps/backend/tests/test_algebra_extracted_text_import_dry_run.py \
  apps/backend/tests/test_rag_metadata_audit.py -q
15 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health checked at `2026-08-19 08:40 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Decision

The Algebra pipeline now has a full local path from exact approved assets → extracted text excerpts → material/chunk-shaped rows → metadata audit `19/19` clean.

This remains local-only and does not promote Algebra. Next gate: feed extracted-text rows into durable local SQLite import/readiness snapshot, then keep preview unless a real staging/production import with smoke is executed.
