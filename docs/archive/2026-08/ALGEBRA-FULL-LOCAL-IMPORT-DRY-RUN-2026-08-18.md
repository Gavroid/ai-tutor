# Algebra Full Local Import Dry Run — 2026-08-18

## Scope

This increment expands the Algebra local import dry-run from the initial 3-topic subset to all 19 Algebra route topics.

It still performs no real import:

- no source files downloaded into the repo;
- no database writes;
- no real RAG chunk creation;
- no production deploy;
- no production data mutation;
- no readiness promotion.

Algebra remains `preview`; `rag_ready=false` until a real local/staging import and metadata audit are intentionally executed.

## Changed

### `apps/backend/scripts/algebra_local_import_dry_run.py`

Default behavior now covers every Algebra route topic from `ALGEBRA_TOPIC_PLAN`.

- explicit `--topic` arguments still allow a small subset run;
- default run builds 19 material-shaped rows;
- default run builds 19 chunk-shaped rows;
- generated `audit_rows` remain compatible with `scripts.rag_metadata_audit`;
- `db_write=false`, `rag_write=false`, `production_mutation=false` remain unchanged.

### `apps/backend/tests/test_algebra_local_import_dry_run.py`

Added TDD coverage that default import dry-run covers all 19 Algebra topics and passes metadata audit.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_local_import_dry_run.py -q
FAILED test_local_import_dry_run_default_covers_all_algebra_topics
assert 3 == 19
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_local_import_dry_run.py -q
4 passed, 3 warnings
```

## Dry-Run Evidence

Command:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_local_import_dry_run \
  --out /tmp/algebra-local-import-19.json
```

Output:

```text
{"ok": true, "out": "/tmp/algebra-local-import-19.json", "topic_count": 19, "material_count": 19, "chunk_count": 19, "readiness_decision": "keep_preview_local_dry_run_only"}
```

Manifest summary:

```text
{'mode': 'local_import_dry_run_only', 'subject': 'algebra', 'topic_count': 19, 'db_write': False, 'rag_write': False, 'readiness_decision': 'keep_preview_local_dry_run_only'}
{'materials': 19, 'chunks': 19}
```

Metadata audit over generated rows:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.rag_metadata_audit \
  --subject-code algebra \
  --input-json /tmp/algebra-local-import-19-audit-rows.json \
  --json > /tmp/algebra-local-import-19-audit.json

{'rows_checked': 19, 'ok_rows': 19, 'bad_rows': 0, 'problems': {}}
```

## Verification Gates

```text
apps/backend/.venv/bin/python -m py_compile apps/backend/scripts/algebra_local_import_dry_run.py

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_local_import_dry_run.py \
  apps/backend/tests/test_algebra_rag_subset_fixture.py \
  apps/backend/tests/test_rag_metadata_audit.py \
  apps/backend/tests/test_algebra_source_extraction_probe.py \
  apps/backend/tests/test_algebra_source_import_dry_run.py \
  apps/backend/tests/test_algebra_fallback_seed.py \
  apps/backend/tests/test_math_route_plan.py::test_algebra_route_plan_endpoint_returns_preview_route \
  apps/backend/tests/test_subjects.py::test_list_subjects_returns_seed -q
26 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health checked at `2026-08-18 22:59 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Decision

The Algebra pipeline can now generate a full 19-topic local import rehearsal and validate its metadata contract with `bad_rows=0`.

This is still not production source/RAG readiness. The next gate should be an isolated disposable test database/session adapter or a staging-only importer that writes and rolls back the same material/chunk rows, then runs `rag_metadata_audit` against the generated rows before any production import is considered.
