# Algebra Exact Source Asset Manifest — 2026-08-19

## Scope

This increment narrows Algebra source/RAG planning from broad source mappings to exact source assets for all 19 Algebra route topics.

It is metadata-only:

- no source files downloaded into the repo;
- no database writes;
- no RAG chunk creation;
- no production deploy;
- no production data mutation;
- no readiness promotion.

Algebra remains `preview`.

## Added

### `apps/backend/scripts/algebra_source_asset_manifest.py`

Exact source asset manifest builder.

It maps all `19` Algebra route topics to concrete approved assets:

- Wallace section PDFs for numeric expressions, properties, equations, variation, exponents, and polynomial sections;
- IM Algebra 1 Unit 2 / Unit 4 pages for linear equations, systems, and functions.

Each asset records:

- topic id/order/focus;
- source key/title/section;
- exact asset URL;
- asset label;
- license;
- attribution;
- source decision;
- no-mutation flags.

Validation checks:

- unique topic ids;
- manifest topic count matches asset count;
- every asset URL uses an approved source prefix;
- license is present and not `ND`;
- production mutation flag remains false.

### `apps/backend/tests/test_algebra_source_asset_manifest.py`

TDD coverage:

- asset manifest covers all 19 Algebra topics with exact assets;
- validator rejects unsafe/unapproved asset URLs;
- current manifest validates cleanly.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_source_asset_manifest.py -q
ModuleNotFoundError: No module named 'scripts.algebra_source_asset_manifest'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_source_asset_manifest.py -q
3 passed, 3 warnings
```

## Manifest Evidence

Command:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_source_asset_manifest \
  --out /tmp/algebra-source-assets.json
```

Output:

```text
{"ok": true, "out": "/tmp/algebra-source-assets.json", "topic_count": 19, "asset_count": 19, "problems": []}
```

Summary:

```text
{'mode': 'exact_source_asset_manifest_only', 'subject': 'algebra', 'topic_count': 19, 'production_mutation': False, 'db_import': False, 'rag_chunk_creation': False}
{'assets': 19, 'source_keys': ['im_first_edition', 'wallace_algebra']}
```

First asset example:

```text
topic_id=34
asset_url=http://www.wallace.ccfaculty.org/book/0.3%20Order%20of%20Operations.pdf
license=CC BY 3.0
```

Last asset example:

```text
topic_id=52
asset_url=https://im.kendallhunt.com/HS/students/1/2/index.html
license=CC BY 4.0
```

## Verification Gates

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/scripts/algebra_source_asset_manifest.py \
  apps/backend/scripts/algebra_local_readiness_snapshot.py

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_source_asset_manifest.py \
  apps/backend/tests/test_algebra_local_readiness_snapshot.py \
  apps/backend/tests/test_algebra_promotion_gate.py \
  apps/backend/tests/test_algebra_durable_local_import_target.py \
  apps/backend/tests/test_rag_metadata_audit.py \
  apps/backend/tests/test_subjects.py::test_list_subjects_returns_seed -q
18 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health checked at `2026-08-19 07:30 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Decision

The Algebra source/RAG pipeline now has an exact asset manifest for all 19 topics. The next gate is content extraction from these exact assets into local text snippets, followed by metadata audit and the existing promotion gate.

Production import remains blocked until backup/offsite verification and targeted import/deploy planning are performed.
