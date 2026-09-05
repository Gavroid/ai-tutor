# Algebra Import Execution Plan Gate — 2026-08-19

## Scope

This increment adds a fail-closed safety checker for deciding whether an Algebra source/RAG import may even be planned for staging or production.

It does **not** import rows, write DB records, create RAG chunks, deploy code, mutate production, advance markers, or promote Algebra.

Algebra remains `preview`.

## Added

### `apps/backend/scripts/algebra_import_execution_plan.py`

Safety evaluator for staging/production import planning.

It requires all of these before returning an allowed import plan:

- target is `staging` or `production`, not local;
- route coverage is `19/19`;
- source/RAG coverage is `19/19`;
- practice coverage is `19/19`;
- metadata audit has `0` bad rows;
- backup is verified;
- offsite backup is verified;
- target tree is clean;
- branch is aligned;
- HEAD is aligned;
- smoke plan is defined.

Even when import planning is allowed, `promotion_allowed` remains `false`; promotion still belongs to the separate post-import smoke/promotion gate.

### `apps/backend/tests/test_algebra_import_execution_plan.py`

TDD coverage:

- local target is blocked even with clean rows;
- production target is blocked without backup/offsite/smoke plan;
- dirty or misaligned target is blocked;
- staging plan is allowed only when all gates pass;
- incomplete source coverage or bad metadata blocks import.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_import_execution_plan.py -q
ModuleNotFoundError: No module named 'scripts.algebra_import_execution_plan'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_import_execution_plan.py -q
5 passed, 3 warnings
```

## CLI Evidence

Blocked local target, despite full clean rows:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_import_execution_plan \
  --target-env local \
  --route-topic-count 19 \
  --source-topic-count 19 \
  --practice-topic-count 19 \
  --metadata-bad-rows 0 \
  --backup-verified \
  --offsite-verified \
  --target-tree-clean \
  --branch-aligned \
  --head-aligned \
  --smoke-plan-defined

{
  "decision": "block_import",
  "import_allowed": false,
  "promotion_allowed": false,
  "blockers": ["target_not_staging_or_production"],
  "production_mutation": false
}
```

Allowed staging import plan, promotion still blocked:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_import_execution_plan \
  --target-env staging \
  --route-topic-count 19 \
  --source-topic-count 19 \
  --practice-topic-count 19 \
  --metadata-bad-rows 0 \
  --backup-verified \
  --offsite-verified \
  --target-tree-clean \
  --branch-aligned \
  --head-aligned \
  --smoke-plan-defined

{
  "decision": "ready_for_staging_import_plan",
  "import_allowed": true,
  "promotion_allowed": false,
  "blockers": [],
  "production_mutation": false
}
```

## Verification Gates

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/scripts/algebra_import_execution_plan.py \
  apps/backend/tests/test_algebra_import_execution_plan.py
exit 0

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_import_execution_plan.py -q
5 passed, 3 warnings
```

## Decision

The next Algebra import step is now guarded by an explicit fail-closed plan gate. Local SQLite evidence can prove row shape and metadata quality, but it cannot authorize import or promotion. Staging/production import planning remains blocked until backup/offsite, clean/aligned target state, and smoke coverage are all explicit.
