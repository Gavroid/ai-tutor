# Math Autonomous Quality Lab — Phase 1.5 Local Sample Capture — 2026-08-18

## Scope

This increment adds a local read-only sample capture mode for the Math Autonomous Quality Lab.

It does **not** call production, mutate the database, deploy code, or consume student AI budget. The capture source is the deterministic Math fallback bank already used for local quality audits.

## Added

### `apps/backend/scripts/math_quality_lab.py`

New local capture support:

- `build_local_sample_capture(...)` emits explanation and practice samples for selected Math topics.
- `--capture-local-samples` CLI flag prints the captured sample rows as JSON.
- `--sample-only` limits capture to the stable representative topic set.
- missing topics emit a structured `kind=missing` sample instead of crashing.

The local explanation sample builder expands short fallback explanations into a child-readable audit sample with:

- rule section;
- example section;
- common mistake section;
- self-check prompt.

This keeps the explanation gate useful without pretending these are live provider outputs.

### `apps/backend/tests/test_math_quality_lab.py`

New TDD coverage:

- local capture emits explanation + practice samples for selected topics;
- captured explanations can be passed through the explanation gate;
- missing topics are represented as structured missing samples.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest apps/backend/tests/test_math_quality_lab.py -q
ImportError: cannot import name 'build_local_sample_capture' from 'scripts.math_quality_lab'
```

After the first minimal implementation, tests exposed a real quality issue: raw fallback explanations were too short / not structured enough for the stricter explanation gate. The implementation was adjusted to build explicit rule/example/mistake/check samples rather than weakening the gate.

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest apps/backend/tests/test_math_quality_lab.py -q
11 passed, 3 warnings
```

## CLI Evidence

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.math_quality_lab \
  --capture-local-samples --sample-only --json > /tmp/math-local-samples.json

{'samples': 24, 'kinds': ['explanation', 'practice'], 'topics': 12}
```

Captured explanation samples passed the Phase 1.4 explanation gate:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.math_quality_lab \
  --explanation-samples /tmp/math-local-explanations.json --json

{'topic_count': 12, 'pass_count': 12, 'fail_count': 0}
```

## Verification Gates

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_math_quality_lab.py \
  apps/backend/tests/test_ai_output_contract.py \
  apps/backend/tests/test_ai_generate_uses_topic_fallback.py \
  apps/backend/tests/test_health.py -q
72 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts --project=chromium
4 passed
```

A first full Playwright run hit a 240s timeout after admin/parent/teacher passed. The student flow was rerun separately and passed in 2.4s, then the full suite was rerun with a 600s command timeout and passed in 6.5s.

## Production Read-Only Evidence

Checked at `2026-08-18 22:14 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
backend/frontend/db/redis/prometheus healthy
frontend/grafana/proxy running
```

## Decision

Quality Lab now has a safe local capture path for repeatable explanation/practice samples. The next increment can either:

1. add a local per-topic Markdown matrix from captured samples; or
2. move to Release Hygiene Phase 3 / Algebra source pipeline after this Quality Lab slice is committed.
