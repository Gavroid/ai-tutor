# Math Autonomous Quality Lab — Phase 1.6 Sample Matrix — 2026-08-18

## Scope

This increment turns local Quality Lab samples into a compact per-topic Markdown matrix.

No production deploy, production data mutation, marker advancement, or student AI budget usage was performed.

## Added

### `apps/backend/scripts/math_quality_lab.py`

New matrix helpers:

- `build_sample_quality_matrix(samples)` — summarizes captured explanation/practice samples per topic.
- `format_sample_quality_matrix_markdown(rows)` — renders a safe Markdown table.
- `--sample-matrix` CLI flag — prints the matrix from local captured samples.

The matrix intentionally excludes raw sample content and hidden-answer fields. It reports only:

- topic id;
- source;
- explanation status;
- practice status;
- issue count.

### `apps/backend/tests/test_math_quality_lab.py`

New TDD coverage:

- local capture rows summarize into ordered per-topic matrix rows;
- explanation/practice statuses are both visible;
- Markdown output is readable and does not expose `correct_answer`.

## TDD Evidence

### RED

Before implementation:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest apps/backend/tests/test_math_quality_lab.py -q
ImportError: cannot import name 'build_sample_quality_matrix' from 'scripts.math_quality_lab'
```

### GREEN

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest apps/backend/tests/test_math_quality_lab.py -q
13 passed, 3 warnings
```

## CLI Evidence

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/python -m scripts.math_quality_lab \
  --sample-matrix --sample-only > /tmp/math-sample-matrix.md
```

Result summary:

```text
# Math Quality Sample Matrix

| Topic ID | Source | Explanation | Practice | Issues |
|---:|---|---|---|---:|
| 187 | local_fallback_bank | pass | pass | 0 |
| 188 | local_fallback_bank | pass | pass | 0 |
| 189 | local_fallback_bank | pass | pass | 0 |
| 195 | local_fallback_bank | pass | pass | 0 |
| 200 | local_fallback_bank | pass | pass | 0 |
| 203 | local_fallback_bank | pass | pass | 0 |
| 208 | local_fallback_bank | pass | pass | 0 |
| 213 | local_fallback_bank | pass | pass | 0 |
| 219 | local_fallback_bank | pass | pass | 0 |
| 222 | local_fallback_bank | pass | pass | 0 |
| 225 | local_fallback_bank | pass | pass | 0 |
| 228 | local_fallback_bank | pass | pass | 0 |
```

Leak check:

```text
! grep -q 'correct_answer' /tmp/math-sample-matrix.md
exit 0
```

## Verification Gates

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_math_quality_lab.py \
  apps/backend/tests/test_ai_output_contract.py \
  apps/backend/tests/test_ai_generate_uses_topic_fallback.py \
  apps/backend/tests/test_health.py -q
74 passed, 3 warnings

cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts --project=chromium
4 passed
```

## Production Read-Only Evidence

Checked at `2026-08-18 22:23 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
backend/frontend/db/redis/prometheus healthy
frontend/grafana/proxy running
```

## Decision

Quality Lab now has the core offline loop:

1. audit deterministic fallback bank;
2. capture local explanation/practice samples;
3. apply explanation gate;
4. produce a per-topic sample matrix.

Next work can move from Math Quality Lab to the next recommended track: Release Hygiene / marker workflow dry-run, then Algebra source/RAG pipeline.
