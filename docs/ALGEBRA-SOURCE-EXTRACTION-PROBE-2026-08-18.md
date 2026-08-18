# Algebra Source Extraction Probe — 2026-08-18

## Scope

This increment advances the Algebra Source/RAG pipeline from a source mapping manifest toward extraction validation.

It remains a **local probe only**:

- no source files downloaded into the repo;
- no database import;
- no RAG chunk creation;
- no production deploy;
- no production data mutation;
- Algebra remains `preview` and `rag_ready=false`.

## Added

### `apps/backend/scripts/algebra_source_extraction_probe.py`

Local validator for approved Algebra source text.

It takes a JSON object mapping `source_key` to extracted text, then checks Stage 13 topic mappings against required section/topic terms.

Outputs:

- per-topic probe rows;
- pass/fail status;
- matched/missing terms;
- source counts;
- explicit safety flags: `production_mutation=false`, `db_import=false`, `rag_chunk_creation=false`.

The probe is fail-closed: missing source text or missing required terms produces failed rows rather than inferred coverage.

### `apps/backend/tests/test_algebra_source_extraction_probe.py`

TDD coverage:

- accepted source text must match required section/topic keywords;
- missing terms fail closed;
- probe rows inherit Stage 13 mapping and no-mutation flags;
- summary counts pass/fail and source coverage.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_source_extraction_probe.py -q
ModuleNotFoundError: No module named 'scripts.algebra_source_extraction_probe'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_source_extraction_probe.py -q
4 passed, 3 warnings
```

Combined Algebra source tests:

```text
apps/backend/.venv/bin/python -m py_compile apps/backend/scripts/algebra_source_extraction_probe.py
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_source_extraction_probe.py \
  apps/backend/tests/test_algebra_source_import_dry_run.py -q
8 passed, 3 warnings
```

## Source Evidence

`web_extract` confirmed the approved source index pages remain reachable enough for local evidence collection:

- Illustrative Mathematics Algebra 1 index exposes Unit 2 `Linear Equations, Inequalities, and Systems` and Unit 4 `Functions`.
- Tyler Wallace `Beginning and Intermediate Algebra` page exposes CC BY 3.0 licensing plus section links including `0.3 Order of Operations`, `0.4 Properties of Algebra`, `1.3 General Linear Equations`, `5.1 Exponent Properties`, and polynomial sections.

A direct Python fetch of IM later timed out, so the probe used the already extracted IM text from `web_extract`; Wallace used the full cached extract at `/root/.hermes/profiles/chatgpt/cache/web/www.wallace.ccfaculty.org-648068e679.md`.

## Probe Evidence

Command:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_source_extraction_probe \
  --source-text-json /tmp/algebra-source-text.json \
  --out /tmp/algebra-extraction-probe.json
```

Output:

```text
PROBE_RC=0
{'topic_count': 19, 'pass_count': 19, 'fail_count': 0, 'source_counts': {'im_first_edition': 7, 'wallace_algebra': 12}}
```

## Verification Gates

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_source_extraction_probe.py \
  apps/backend/tests/test_algebra_source_import_dry_run.py \
  apps/backend/tests/test_algebra_fallback_seed.py \
  apps/backend/tests/test_math_route_plan.py::test_algebra_route_plan_endpoint_returns_preview_route \
  apps/backend/tests/test_subjects.py::test_list_subjects_returns_seed -q
13 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health checked at `2026-08-18 22:41 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Decision

Algebra source extraction is now validated at index/section evidence level for the Stage 13 approved mapping: `19/19` probe rows pass.

This is **not** Algebra RAG readiness. The next gate is a true local subset import fixture: create local learning-material/chunk fixtures for 2–3 Algebra topics, run metadata audit, and keep production untouched unless backup/offsite + targeted import is explicitly executed later.
