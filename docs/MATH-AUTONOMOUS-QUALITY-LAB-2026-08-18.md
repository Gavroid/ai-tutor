# Math Autonomous Quality Lab — Phase 1.1–1.3 — 2026-08-18

## Decision

Phase 1 has started and the first Math quality-lab slice is complete.

The current deterministic Math fallback bank passed the new autonomous quality checks across all 42 Math pilot topics.

```text
full audit: 42 topics checked, 42 passed, 0 failed
sample audit: 12 topics checked, 12 passed, 0 failed
```

No production mutation was performed. No student AI budget was consumed. No Algebra/Geometry source/RAG work was touched.

## What Was Added

### `apps/backend/scripts/math_quality_lab.py`

Read-only local quality tool for Math pilot fallback content.

It checks student-facing text for:

- raw JSON;
- `<think>` or escaped reasoning markers;
- `correct_answer` / hidden-answer leak markers;
- markdown fences;
- broken markdown table separators;
- raw math markers such as `$$`, `\\frac`, `\\text`;
- provider/protocol wording such as `AI`, `JSON`, `fallback`, `provider`;
- field-specific minimum usefulness thresholds.

It also provides:

- stable default topic sample;
- full fallback-bank audit;
- JSON output;
- Markdown summary output.

### `apps/backend/tests/test_math_quality_lab.py`

Regression tests covering:

- bad student-visible output detection;
- accepted child-readable explanation;
- provider/protocol artifact detection;
- stable default sample topic selection;
- 42/42 Math fallback bank audit;
- sample-only report generation;
- plain serialization of issues.

### `apps/backend/scripts/math_fallback_seed.py`

Changed only import timing: `content_registry` now imports lazily inside `run()`.

Reason: tools that only import `FALLBACKS` for local audits should not require full application settings or DB configuration.

## Topic Sample

The first stable representative sample:

```text
187, 188, 189, 195, 200, 203, 208, 213, 219, 222, 225, 228
```

Rationale:

- first route topic;
- last route topic;
- percentage/fraction/diagram topics;
- proportionality topic;
- geometry measurement topic;
- rational-number operations;
- algebraic expression/equation topics.

## Verification

### RED

Before implementation:

```text
.venv/bin/pytest tests/test_math_quality_lab.py -q
ERROR tests/test_math_quality_lab.py
ModuleNotFoundError: No module named 'scripts.math_quality_lab'
```

### GREEN

After implementation:

```text
.venv/bin/pytest tests/test_math_quality_lab.py -q
7 passed, 3 warnings
```

### Sample CLI

```text
.venv/bin/python -m scripts.math_quality_lab --sample-only --json > /tmp/math-quality-lab-sample.json
{'topic_count': 12, 'pass_count': 12, 'fail_count': 0}
```

### Full CLI

```text
.venv/bin/python -m scripts.math_quality_lab --json > /tmp/math-quality-lab-full.json
{'topic_count': 42, 'pass_count': 42, 'fail_count': 0}
```

### Backend Safety Slice

```text
.venv/bin/pytest \
  tests/test_math_quality_lab.py \
  tests/test_ai_output_contract.py \
  tests/test_ai_generate_uses_topic_fallback.py \
  tests/test_health.py -q
68 passed, 3 warnings
```

## No Fixes Needed Yet

The first deterministic fallback-bank audit found no repeated concrete defects:

- no raw JSON;
- no reasoning leak;
- no hidden answer marker leak;
- no broken math markers;
- no provider/protocol wording;
- no malformed single-choice fallback rows.

Therefore Phase 1.4 currently has no evidence-backed runtime patch to apply.

## Remaining Phase 1 Work

The next quality-lab increment should audit dynamic AI-generated explanations/practice where safe:

1. Add optional admin-safe explain probe mode.
2. Avoid production auth-rate-limit bursts.
3. Avoid student budget burn.
4. Capture actual AI/provider output quality separately from deterministic fallback quality.
5. Patch only repeated, reproduced defects.

## Production Impact

None.

- No deploy.
- No DB migration.
- No production data mutation.
- No backup/offsite required for this local/docs-only slice.
- No Nightscout or external medical systems touched.

## Commit

Pending at report creation.
