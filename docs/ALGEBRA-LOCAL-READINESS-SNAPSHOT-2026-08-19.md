# Algebra Local Readiness Snapshot — 2026-08-19

## Scope

This increment adds an endpoint-like local readiness snapshot for Algebra durable import rehearsals.

It reads committed rows from the local durable SQLite import target, runs metadata audit, counts route/source/practice coverage, and routes the result through the fail-closed promotion gate.

It does **not** change runtime `/api/v1/subjects`, deploy code, mutate production, create production RAG chunks, or promote Algebra.

Algebra remains `preview`.

## Added

### `apps/backend/scripts/algebra_local_readiness_snapshot.py`

Local readiness calculator for durable import rehearsal data.

It reports:

- route topic count;
- source topic count from durable local rows;
- practice topic count;
- metadata audit bad/ok/checked rows;
- promotion gate result;
- blockers.

The script always uses `import_mode=durable_local_sqlite_import_target`, so local rehearsal data cannot promote Algebra by itself.

### `apps/backend/tests/test_algebra_local_readiness_snapshot.py`

TDD coverage:

- a full durable local import snapshot counts `19/19` source topics but remains `preview` and `rag_ready=false`;
- an empty durable DB snapshot remains `preview` with source coverage incomplete.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_local_readiness_snapshot.py -q
ModuleNotFoundError: No module named 'scripts.algebra_local_readiness_snapshot'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_local_readiness_snapshot.py -q
2 passed, 3 warnings
```

## Snapshot Evidence

Commands:

```text
rm -f /tmp/ai-tutor-algebra-readiness.sqlite3
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_durable_local_import_target \
  --db-path /tmp/ai-tutor-algebra-readiness.sqlite3 \
  > /tmp/algebra-readiness-import.json

PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.algebra_local_readiness_snapshot \
  --db-path /tmp/ai-tutor-algebra-readiness.sqlite3 \
  > /tmp/algebra-readiness-snapshot.json
```

Result:

```text
SNAP_RC=0
{
  'subject': 'algebra',
  'route_topic_count': 19,
  'source_topic_count': 19,
  'practice_topic_count': 19,
  'metadata_bad_rows': 0,
  'mvp_status': 'preview',
  'rag_ready': False,
  'promotion_allowed': False,
  'blockers': ['import_not_production_or_staging', 'smoke_not_passed']
}
```

## Verification Gates

```text
apps/backend/.venv/bin/python -m py_compile \
  apps/backend/scripts/algebra_local_readiness_snapshot.py \
  apps/backend/scripts/algebra_promotion_gate.py \
  apps/backend/scripts/algebra_durable_local_import_target.py

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_algebra_local_readiness_snapshot.py \
  apps/backend/tests/test_algebra_promotion_gate.py \
  apps/backend/tests/test_algebra_durable_local_import_target.py \
  apps/backend/tests/test_subjects.py::test_list_subjects_returns_seed -q
9 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health checked at `2026-08-19 07:25 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Decision

The Algebra pipeline now has a local readiness snapshot that proves the key safety rule: local durable import rows can show source coverage, but they do not promote Algebra.

Next meaningful gate requires a real staging or production-safe import environment plus smoke. Production import remains blocked until backup/offsite verification and targeted import planning are performed.
