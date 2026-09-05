# Math Autonomous Quality Lab — Phase 1.4 Explanation Sample Gate — 2026-08-18

## Scope

This increment extends the Math Autonomous Quality Lab beyond deterministic fallback rows by adding an offline explanation-sample gate.

No production deploy, production data mutation, marker advancement, or student AI budget usage was performed. The new path reads a local JSON sample file and never calls the AI provider or production API.

## Added

### `apps/backend/scripts/math_quality_lab.py`

New functions:

- `audit_explanation_samples(samples)` — audits captured explanation outputs for student-facing safety and usefulness.
- `load_explanation_samples(path)` — loads a JSON array of captured explanation samples for offline checks.
- CLI flag `--explanation-samples <path>` — runs the explanation gate and returns exit `0` only when all samples pass.

The explanation gate checks:

- raw JSON / hidden-answer markers;
- `<think>` / reasoning leaks;
- markdown fences and broken table separators;
- raw math markers such as `$$`, `\\frac`, `\\text`;
- provider/protocol wording such as `AI`, `JSON`, `provider`, `fallback`;
- explanations shorter than the runtime retry/fallback threshold (`250` chars);
- missing instructional structure: example/check/rule cues.

### `apps/backend/tests/test_math_quality_lab.py`

New regression coverage:

- bad explanation sample fails with raw JSON, hidden-answer leak, reasoning leak, provider artifact, and short-output codes;
- child-readable structured explanation sample passes cleanly.

## Verification

### RED

Before implementation, the new tests failed at import:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest apps/backend/tests/test_math_quality_lab.py -q
ImportError: cannot import name 'audit_explanation_samples' from 'scripts.math_quality_lab'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest apps/backend/tests/test_math_quality_lab.py -q
9 passed, 3 warnings
```

### CLI Smoke

Good sample:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.math_quality_lab \
  --explanation-samples /tmp/math-explanation-samples-ok.json --json
OK_RC=0
1 topic checked, 1 passed, 0 failed
```

Bad sample:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.math_quality_lab \
  --explanation-samples /tmp/math-explanation-samples-bad.json --json
BAD_RC=1
1 topic checked, 0 passed, 1 failed
issue codes: raw_json, hidden_answer_leak, reasoning_leak, provider_artifact, explanation_too_short, missing_instructional_structure
```

Fallback-bank regression remains green:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.math_quality_lab --json
{'topic_count': 42, 'pass_count': 42, 'fail_count': 0}
```

## Broader Gates

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_math_quality_lab.py \
  apps/backend/tests/test_ai_output_contract.py \
  apps/backend/tests/test_ai_generate_uses_topic_fallback.py \
  apps/backend/tests/test_health.py -q
70 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts --project=chromium
4 passed
```

## Production Read-Only Evidence

Checked at `2026-08-18 22:00 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
backend/frontend/db/redis/prometheus healthy
frontend/grafana/proxy running
```

## Decision

This closes the next safe Quality Lab increment: future real/admin-safe explanation captures can be fed into the local JSON gate before any runtime patch is considered.

No repeated live-output defect was reproduced in this increment, so no student runtime behavior was changed.
