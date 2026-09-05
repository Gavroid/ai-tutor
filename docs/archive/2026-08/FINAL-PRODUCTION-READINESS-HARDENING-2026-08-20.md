# Final Production Readiness Hardening — 2026-08-20

## Scope

This final pass added an explicit all-subject production audit gate and re-ran the full readiness/smoke evidence after the all-subject MVP promotion and content-quality passes.

No production data mutation or deploy was required in this pass.

## Added

- `apps/backend/scripts/production_all_subjects_audit.py`
- `apps/backend/tests/test_production_all_subjects_audit.py`

The audit is fail-closed and checks:

- expected subject count;
- every subject is `mvp_ready`;
- every subject has `route_ready`, `rag_ready`, and `practice_ready`;
- `topic_count == route_topic_count == source_topic_count == practice_topic_count`;
- total topic count.

It supports `--insecure` for the LAN self-signed TLS endpoint.

## TDD Evidence

RED:

```text
ModuleNotFoundError: No module named 'scripts.production_all_subjects_audit'
```

GREEN:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_production_all_subjects_audit.py -q
2 passed, 3 warnings
```

## Production Audit

Command:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.production_all_subjects_audit \
  --base-url https://192.168.1.86 \
  --insecure
```

Result:

```json
{
  "ok": true,
  "subject_count": 12,
  "total_topics": 225,
  "problems": []
}
```

## Regression / Smoke

Backend regression:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_production_all_subjects_audit.py \
  apps/backend/tests/test_remaining_subjects_internal_source_manifest.py \
  apps/backend/tests/test_subjects.py \
  apps/backend/tests/test_rag_metadata_audit.py -q
25 passed, 3 warnings
```

Student smoke:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

Production health and hygiene:

```text
READY_HTTP=200
HEALTH_HTTP=200
prod_status=0
marker=801bbb0
head=5c95974
backend/frontend/db/redis healthy
```

## Decision

The current AI-Tutor production state is complete for this plan:

- all 12 seeded subjects are production `mvp_ready`;
- all 225 seeded topics have route/source/practice coverage;
- student smoke passes;
- production git tree is clean;
- remaining work is now a new phase: deeper textbook-grade curriculum/source quality, not MVP readiness.
