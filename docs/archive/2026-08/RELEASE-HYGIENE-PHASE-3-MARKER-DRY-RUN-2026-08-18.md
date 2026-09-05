# Release Hygiene Phase 3 — Marker Advancement Dry Run — 2026-08-18

## Scope

This phase adds and runs a read-only marker advancement dry-run checker.

No production deploy, production data mutation, backup/offsite run, or marker advancement was performed. The production backup/offsite gate remains mandatory before any future runtime production mutation.

## Added

### `scripts/release_marker_dry_run.py`

Offline helper that evaluates whether `.mvp-rescue-commit` can be advanced from read-only release state.

Inputs:

- local target `HEAD`;
- production marker value;
- production git `HEAD`;
- production branch/status header;
- production dirty-path list;
- intended release branch, default `mvp-rescue`.

Outputs:

- `decision`;
- `can_advance_marker`;
- current/target marker;
- production branch/head;
- dirty path count/sample;
- blockers;
- recommended mode;
- required gates before mutation.

Exit behavior:

- `0` when not blocked;
- `2` when marker advancement is blocked by release hygiene.

### `tests/test_release_marker_dry_run.py`

TDD coverage:

- dirty production tree blocks marker advancement;
- branch mismatch blocks marker advancement;
- production HEAD mismatch blocks marker advancement;
- clean/aligned state allows marker advancement;
- already-current marker is treated as a no-op.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=. apps/backend/.venv/bin/pytest tests/test_release_marker_dry_run.py -q
ModuleNotFoundError: No module named 'scripts.release_marker_dry_run'
```

### GREEN

```text
PYTHONPATH=. apps/backend/.venv/bin/pytest tests/test_release_marker_dry_run.py -q
3 passed in 0.01s
```

Combined release tooling tests:

```text
apps/backend/.venv/bin/python -m py_compile scripts/release_marker_dry_run.py
PYTHONPATH=. apps/backend/.venv/bin/pytest \
  tests/test_release_marker_dry_run.py \
  tests/test_targeted_deploy_manifest.py -q
8 passed in 0.03s
```

## Production Dry Run Evidence

Read-only production state captured from `/opt/ai-tutor`:

```text
local_head=b7ffe89
production_marker=6e698a0
production_branch=master
production_head=cb99f2b
production_dirty_path_count=120
```

Dry-run result:

```json
{
  "decision": "blocked",
  "can_advance_marker": false,
  "target_marker": "b7ffe89",
  "current_marker": "6e698a0",
  "production_head": "cb99f2b",
  "production_branch": "master",
  "intended_branch": "mvp-rescue",
  "dirty_path_count": 120,
  "blockers": [
    "production_tree_dirty",
    "production_branch_mismatch",
    "production_head_mismatch"
  ],
  "recommended_mode": "targeted_deploy"
}
```

## Verification Gates

Backend / release tooling:

```text
PYTHONPATH=. apps/backend/.venv/bin/pytest \
  tests/test_release_marker_dry_run.py \
  tests/test_targeted_deploy_manifest.py -q
8 passed in 0.03s

PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_health.py \
  apps/backend/tests/test_math_quality_lab.py -q
21 passed, 3 warnings
```

Frontend:

```text
cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test \
  e2e/pilot.spec.ts:37 e2e/pilot.spec.ts:68 e2e/pilot.spec.ts:85 \
  --project=chromium --reporter=list
3 passed

BASE_URL=https://192.168.1.86 npx playwright test \
  e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health checked at `2026-08-18 22:35 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Decision

Marker advancement remains **blocked**. Continue targeted deploy mode only.

Do not write `.mvp-rescue-commit`, do not run broad destructive sync, and do not claim release marker recovery until production is clean/aligned with the intended branch and a backup/offsite + smoke-backed release flow is actually executed.
