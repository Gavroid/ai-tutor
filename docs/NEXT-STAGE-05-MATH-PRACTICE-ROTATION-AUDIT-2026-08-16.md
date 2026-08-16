# Next Stage 05 — Math Practice Variant Rotation Audit — 2026-08-16

## Scope

Stage 05 goal: confirm practice does not repeat stale tasks too aggressively.

## Finding

Production registry for representative Math topics had only one fallback row per topic even though the local seed script can produce three variants.

Initial production smoke:

```text
Topic 187: unique_questions=3/3
Topic 190: unique_questions=2/3
Topic 203: unique_questions=1/3
```

This meant some repeated `Practice` clicks could return the same question too often.

## Root Cause

`teacher_content_registry.json` in production had older single-row fallback entries for Math topics. The local `scripts/math_practice_variants_seed.py` already generated 3 checkable variants, but those variants had not been applied to the production registry for the sampled topics.

## Production Fix

Production backup and offsite verification were run before registry mutation:

```text
manifest-20260816T135558Z.md5
OFFSITE OK: hash verified manifest-20260816T135558Z.md5
```

Then `math_practice_variants_seed.py` was synced and applied narrowly to topics `187,190,203`.

Registry verification after fix:

```text
187: 3 rows, 3 unique question_text values
190: 3 rows, 3 unique question_text values
203: 3 rows, 3 unique question_text values
```

Repeat generation smoke after fix:

```text
Topic 187: unique_questions=3/3
Topic 190: unique_questions=3/3
Topic 203: unique_questions=3/3
```

## Gates

```text
cd apps/backend
.venv/bin/pytest tests/test_math_fallback_seed.py tests/test_math_practice_variants_seed.py tests/test_pilot_secure_exercises_v2.py tests/test_health.py -q
23 passed, 35 warnings

cd apps/frontend
BASE_URL=https://192.168.1.86 npx playwright test e2e/mvp-student-flow.spec.ts --grep "student can open topic" --project=chromium
1 passed (17.9s)

/ready HTTP=200
/health HTTP=200
```

## Decision

Stage 05 is closed. Representative Math practice rotation now produces non-repeating variants for sampled topics. Broader application to all Math topics can be done in a later safe registry maintenance pass, but no blocker remains for these pilot-critical topics.

## Next Stage

Proceed to Stage 06 — Parent Report Manual Evidence Pass.
