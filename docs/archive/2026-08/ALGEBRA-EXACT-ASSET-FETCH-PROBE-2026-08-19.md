# Algebra Exact Asset Fetch Probe — 2026-08-19

## Scope

This increment adds a temporary fetch/extract probe for exact Algebra source assets.

It verifies that the exact asset URLs selected for the Algebra pipeline can produce extractable text with the expected topic/section terms.

It does **not** write source files into the repo, import database rows, create RAG chunks, deploy code, mutate production, or promote Algebra.

Algebra remains `preview`.

## Added

### `apps/backend/scripts/algebra_exact_asset_fetch_probe.py`

Temporary exact-asset fetch/extract probe.

Capabilities:

- selects exact assets from `algebra_source_asset_manifest`;
- fetches Wallace PDFs into temporary storage and extracts text with `pypdf`;
- extracts HTML text from temporary files;
- supports `--source-text-json` overrides for flaky HTML assets already fetched by a reliable extraction tool;
- validates required topic/section terms;
- records no-mutation flags.

The probe is fail-closed: fetch errors, short extracted text, or missing required terms produce failed rows.

### `apps/backend/tests/test_algebra_exact_asset_fetch_probe.py`

TDD coverage:

- exact topic selection uses the expected asset URLs;
- extracted text evaluator passes/fails on required terms and text length;
- HTML extraction keeps unit terms;
- `source_text_by_url` override supports flaky HTML assets;
- summary counts pass/fail and source coverage.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_exact_asset_fetch_probe.py -q
ModuleNotFoundError: No module named 'scripts.algebra_exact_asset_fetch_probe'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_exact_asset_fetch_probe.py -q
6 passed, 3 warnings
```

## Fetch/Extract Evidence

Representative first run without overrides:

```text
SAMPLE_RC=2
{'asset_count': 2, 'pass_count': 1, 'fail_count': 1, 'source_counts': {'im_first_edition': 1, 'wallace_algebra': 1}}
34 pass 7394 [] []
37 fail 0 ['fetch_or_extract_error:TimeoutError'] ['Unit 2', 'Linear Equations']
```

Finding: Wallace PDFs can be fetched/extracted directly; IM Unit pages return `HTTP=200` but direct Python/curl reads stall after partial HTML. Fresh `web_extract` of IM Unit 2 and Unit 4 succeeds and provides the required unit/lesson anchors.

Final full probe used:

- direct temp fetch/extraction for Wallace PDFs;
- explicit `--source-text-json` override from fresh `web_extract` for IM Unit 2 / Unit 4 pages;
- accepted aliases `Alg1.2` ↔ `Unit 2`, `Alg1.4` ↔ `Unit 4`.

Command:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_exact_asset_fetch_probe \
  --source-text-json /tmp/algebra-im-source-overrides.json \
  --out /tmp/algebra-exact-asset-probe-full.json
```

Result:

```text
FULL_RC=0
{'asset_count': 19, 'pass_count': 19, 'fail_count': 0, 'source_counts': {'im_first_edition': 7, 'wallace_algebra': 12}}
```

## Verification Gates

```text
apps/backend/.venv/bin/python -m py_compile apps/backend/scripts/algebra_exact_asset_fetch_probe.py

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_exact_asset_fetch_probe.py \
  apps/backend/tests/test_algebra_source_asset_manifest.py \
  apps/backend/tests/test_algebra_asset_snippet_import_dry_run.py \
  apps/backend/tests/test_rag_metadata_audit.py \
  apps/backend/tests/test_subjects.py::test_list_subjects_returns_seed -q
19 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health checked at `2026-08-19 08:19 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Decision

Exact Algebra assets now have a verified local fetch/extract probe with `19/19` pass using direct PDF extraction plus explicit IM text overrides from reliable web extraction.

This still is not production RAG readiness. Next gate: replace curated snippets with extracted text slices from the probe output and feed those slices into the durable local import/readiness snapshot path.
