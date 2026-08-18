# Algebra Local RAG Subset Fixture — 2026-08-18

## Scope

This increment creates a local fixture path for the next Algebra RAG gate.

It does **not** import source files, write `learning_materials`, create real `rag_chunks`, deploy code, mutate production, or change Algebra readiness. Algebra remains `preview` until a real import and metadata audit pass exists.

## Added

### `apps/backend/scripts/algebra_rag_subset_fixture.py`

Local fixture builder for a small Algebra subset.

Default subset:

- topic `34` — numeric expressions / Wallace support;
- topic `37` — one-variable linear equations / IM support;
- topic `41` — exponent definition/properties / Wallace support.

The script emits JSON rows compatible with `scripts.rag_metadata_audit` and includes full metadata fields:

- `subject_code=algebra`;
- `topic_id` / `topic_name`;
- `source_title` / `source_url` / `source_section`;
- `license`;
- `attribution`;
- source key and import decision.

Safety flags are explicit on every fixture row and manifest:

```json
{
  "production_mutation": false,
  "db_import": false,
  "rag_chunk_creation": false,
  "readiness_decision": "keep_preview_until_real_import_and_audit"
}
```

### `apps/backend/tests/test_algebra_rag_subset_fixture.py`

TDD coverage:

- subset fixture builds topic-scoped Algebra rows without mutation flags;
- generated rows pass existing RAG metadata audit;
- manifest keeps Algebra preview / not ready.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_rag_subset_fixture.py -q
ModuleNotFoundError: No module named 'scripts.algebra_rag_subset_fixture'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_rag_subset_fixture.py -q
3 passed, 3 warnings
```

## Fixture + Metadata Audit Evidence

Fixture command:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_rag_subset_fixture \
  --out /tmp/algebra-rag-subset-fixture.json
```

Output:

```text
{"ok": true, "out": "/tmp/algebra-rag-subset-fixture.json", "topic_count": 3, "source_counts": {"wallace_algebra": 2, "im_first_edition": 1}, "readiness_decision": "keep_preview_until_real_import_and_audit"}
```

Metadata audit over fixture rows:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.rag_metadata_audit \
  --subject-code algebra \
  --input-json /tmp/algebra-rag-subset-audit-rows.json \
  --json > /tmp/algebra-rag-subset-audit.json

{'rows_checked': 3, 'ok_rows': 3, 'bad_rows': 0, 'problems': {}}
```

## Verification Gates

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/scripts/algebra_rag_subset_fixture.py \
  apps/backend/scripts/algebra_source_extraction_probe.py

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_rag_subset_fixture.py \
  apps/backend/tests/test_algebra_source_extraction_probe.py \
  apps/backend/tests/test_algebra_source_import_dry_run.py \
  apps/backend/tests/test_rag_metadata_audit.py \
  apps/backend/tests/test_algebra_fallback_seed.py \
  apps/backend/tests/test_math_route_plan.py::test_algebra_route_plan_endpoint_returns_preview_route \
  apps/backend/tests/test_subjects.py::test_list_subjects_returns_seed -q
22 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health checked at `2026-08-18 22:45 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Decision

Algebra now has a local subset fixture path that proves the RAG metadata contract can pass for 3 representative topics.

This still does **not** make Algebra source/RAG ready. Next gate: convert this fixture path into a real local-only import dry run that creates temporary/local material + chunk rows or a disposable DB fixture, then run `rag_metadata_audit` against those generated rows before any production import is considered.
