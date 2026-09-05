# Release Hygiene Phase 2 — Targeted Deploy Manifest — 2026-08-18

## Scope

This phase adds an offline/read-only helper for targeted deploy planning while production remains dirty/on marker-debt mode.

No production deploy, production data mutation, marker advancement, or backup/offsite run was performed because the change is local tooling + docs evidence only.

## Added

### `scripts/targeted_deploy_manifest.py`

Classifies a proposed changed-file list into deploy impact:

- `backend` runtime files → backend test/deploy requirements;
- `frontend` runtime files → frontend typecheck/deploy requirements;
- `docs` files → docs-only, no backup/deploy;
- `ops` / unknown files → manual review required.

The helper outputs:

- ordered affected services;
- classified paths;
- whether production backup/offsite is required;
- required local gates;
- targeted production deploy steps;
- post-deploy smoke steps;
- marker-safety notes.

### `tests/test_targeted_deploy_manifest.py`

Covers:

- backend runtime changes require backup and backend tests;
- frontend runtime changes require backup and frontend typecheck;
- docs-only changes require no backup or deploy;
- mixed backend/frontend changes keep stable service order;
- unknown ops paths are routed to manual review.

## Verification

```text
cd /root/workspace/ai-tutor
apps/backend/.venv/bin/python -m py_compile scripts/targeted_deploy_manifest.py
PYTHONPATH=. apps/backend/.venv/bin/pytest tests/test_targeted_deploy_manifest.py -q
5 passed in 0.01s

git diff --check
exit 0
```

## Manifest Smoke

Docs-only example:

```text
PYTHONPATH=. apps/backend/.venv/bin/python scripts/targeted_deploy_manifest.py \
  docs/NEXT-RELEASE-MARKER-ADVANCEMENT-RUNBOOK-2026-08-16.md --json

services: docs
backup_required: false
required_tests: git diff --check
deploy_steps: []
```

Runtime example:

```text
PYTHONPATH=. apps/backend/.venv/bin/python scripts/targeted_deploy_manifest.py \
  apps/backend/app/ai/service.py apps/frontend/app/teacher/page.tsx

services: backend, frontend
backup_required: True
test: cd apps/backend && .venv/bin/pytest tests/test_ai_output_contract.py tests/test_health.py -q
test: cd apps/frontend && npx tsc --noEmit
deploy: docker compose build backend && docker compose up -d --no-deps backend
deploy: docker compose build frontend && docker compose up -d --no-deps frontend
```

## Production Evidence

Read-only production health at `2026-08-18 21:56 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
backend/frontend/db/redis/prometheus healthy
grafana/proxy running
```

## Decision

The tool supports the recommended Ops / Release Hygiene track without broad destructive deploys.

Production remains in targeted deploy mode. Do not advance `.mvp-rescue-commit` for ad-hoc targeted deploys unless the full marker workflow is intentionally executed.
