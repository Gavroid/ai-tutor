# Math Product Sprint Report — 2026-08-14

## Scope

Math-only product-quality sprint after technical readiness reached 42/42.

## Completed

- Added explicit `app.math_plan` route map for all 42 math topics.
- Added route tiers: `base`, `medium`, `hard` and checkpoint topics.
- Added `/api/v1/subjects/{subject_id}/route-plan` for the math subject.
- Updated math subject page to show route order, tier, focus, and checkpoints.
- Updated math diagnostic flow to use balanced math checkpoint topics instead of the first topics only.
- Fixed diagnostic answer handling so frontend submits backend-provided `correct_answer`, not `question_text`.
- Added `math_practice_variants_seed.py` to seed three checkable fallback practice variants for every math topic.
- Kept the work math-only: non-math route plans return an empty list.

## Verification Before Deploy

```text
backend targeted tests: 8 passed, 3 warnings
frontend typecheck: passed
frontend build: passed
```

## Remaining Product Work

- Human editorial review of all generated/fallback tasks.
- Real student pilot session with Кирилл.
- Optional expansion of the same route/diagnostic model to Algebra and Geometry later.
