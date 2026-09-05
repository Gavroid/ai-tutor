# Algebra Asset Extraction Snippets — 2026-08-19

## Scope

This increment adds local snippet metadata tied to the exact Algebra source asset manifest.

It is still metadata-only:

- no source files downloaded into the repo;
- no database writes;
- no RAG chunk creation;
- no production deploy;
- no production data mutation;
- no readiness promotion.

Algebra remains `preview`.

## Added

### `apps/backend/scripts/algebra_asset_extraction_snippets.py`

Local snippet manifest builder for exact Algebra assets.

It creates one snippet row per Algebra route topic and ties each row to:

- exact asset URL from `algebra_source_asset_manifest`;
- source key/title/section;
- license and attribution;
- curated local snippet text;
- extraction mode `local_curated_snippet_from_exact_asset`;
- no-mutation flags.

Validation checks:

- unique topic ids;
- manifest topic count matches snippet count;
- snippets are non-empty;
- asset URL and source section are present;
- production mutation flag remains false.

### `apps/backend/tests/test_algebra_asset_extraction_snippets.py`

TDD coverage:

- snippet manifest covers all 19 exact assets;
- current manifest validates cleanly;
- validator rejects empty snippets.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_asset_extraction_snippets.py -q
ModuleNotFoundError: No module named 'scripts.algebra_asset_extraction_snippets'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_asset_extraction_snippets.py -q
3 passed, 3 warnings
```

## Manifest Evidence

Command:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_asset_extraction_snippets \
  --out /tmp/algebra-asset-snippets.json
```

Output:

```text
{"ok": true, "out": "/tmp/algebra-asset-snippets.json", "topic_count": 19, "snippet_count": 19, "problems": []}
```

Summary:

```text
{'mode': 'local_asset_snippet_manifest_only', 'subject': 'algebra', 'topic_count': 19, 'production_mutation': False, 'db_import': False, 'rag_chunk_creation': False}
{'snippets': 19, 'source_keys': ['im_first_edition', 'wallace_algebra']}
```

First snippet example:

```text
topic_id=34
asset_url=http://www.wallace.ccfaculty.org/book/0.3%20Order%20of%20Operations.pdf
snippet=Order of operations: evaluate grouped arithmetic expressions using operation priority.
```

Last snippet example:

```text
topic_id=52
asset_url=https://im.kendallhunt.com/HS/students/1/2/index.html
snippet=Systems of equations: elimination combines equations to remove one variable.
```

## Verification Gates

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/scripts/algebra_asset_extraction_snippets.py \
  apps/backend/scripts/algebra_source_asset_manifest.py

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_asset_extraction_snippets.py \
  apps/backend/tests/test_algebra_source_asset_manifest.py \
  apps/backend/tests/test_algebra_local_readiness_snapshot.py \
  apps/backend/tests/test_algebra_promotion_gate.py \
  apps/backend/tests/test_subjects.py::test_list_subjects_returns_seed -q
12 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health checked at `2026-08-19 07:35 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Decision

The Algebra pipeline now has exact assets plus local snippet metadata for all 19 topics. This is enough for the next local-only gate: build material/chunk-shaped rows from exact asset snippets instead of generic rehearsal text, then run durable local import and promotion gate again.

Production import remains blocked until backup/offsite verification and targeted import planning are performed.
