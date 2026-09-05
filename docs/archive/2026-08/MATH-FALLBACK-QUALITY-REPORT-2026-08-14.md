# Math Fallback Quality Report — 2026-08-14

## Scope

Stage 04 completed fallback quality across all 42 math route topics.

## Completed

- Expanded `apps/backend/scripts/math_fallback_seed.py` to cover every topic in `MATH_TOPIC_PLAN`.
- Added the remaining 17 hand-authored first fallback variants:
  - `203` отношения;
  - `204` пропорции;
  - `205` прямая и обратная зависимость;
  - `206` масштаб;
  - `207` симметрия;
  - `208` окружность, круг, шар;
  - `209` положительные и отрицательные числа;
  - `210` противоположные числа;
  - `211` модуль числа;
  - `212` сравнение чисел;
  - `215` сложение отрицательных чисел;
  - `216` сложение чисел с разными знаками;
  - `217` вычитание рациональных чисел;
  - `218` умножение рациональных чисел;
  - `219` деление рациональных чисел;
  - `223` коэффициент;
  - `225` решение уравнений.
- Updated the editorial matrix to show `42/42` hand-authored first fallback variants.
- Tightened `tests/test_math_fallback_seed.py` so fallback IDs must exactly match all route topics.

## Quality Rules

Every topic fallback now has a deterministic first variant that is:

- single-choice;
- checkable;
- at least 4 options;
- `correct_answer` included in `options`;
- explanation present;
- typical mistakes present;
- no raw model output, raw JSON, broken markdown tables, or broken math markers.

## Local Verification

```text
cd apps/backend
.venv/bin/pytest tests/test_math_fallback_seed.py tests/test_math_practice_variants_seed.py tests/test_health.py -q

12 passed, 3 warnings in 1.00s
```

## Production Backup / Offsite

Required backup was run before production mutation:

```text
backup manifest: /opt/ai-tutor/deploy/backup/_out/manifest-20260814T153114Z.md5
OFFSITE OK: hash verified manifest-20260814T153114Z.md5
SMB total after upload: 184 files
```

## Production Application

As in Stage 03, full git/release deploy was intentionally avoided because the production working tree is currently dirty and on `master`. Safe narrow path used:

1. `rsync` only `apps/backend/scripts/math_fallback_seed.py` to production.
2. `docker compose cp` the script into the live backend container.
3. Run only `python -m scripts.math_fallback_seed --topics 203,204,205,206,207,208,209,210,211,212,215,216,217,218,219,223,225`.

Seed result:

```text
updated: 17 topic IDs
missing: []
```

Script hash matched host/container:

```text
9b4beff80776262eb8777cb19b8c8bef443a2da37624a14adc2c5c98032c1f3b
```

## Production Smoke

Registry smoke for the Stage 04 topics:

```text
stage04_checked=17 failures=[]
topic=203 answer=2:3
topic=208 answer=5 см
topic=215 answer=-7
topic=225 answer=7
```

Production health after seed:

```text
/ready  HTTP=200
/health HTTP=200
backend/db/frontend/prometheus/redis running healthy; grafana/proxy running
```

## Result

Math fallback first-variant quality is now `42/42` for the route plan.

## Remaining Non-Blockers

- The second and third generated fallback variants are still generic helper tasks; they are safe/checkable but less editorial than the first variant.
- Full production marker was not advanced because this was a narrow script + registry seed, not a container rebuild/release deploy.
- Production working tree hygiene should be handled in a dedicated cleanup/deploy-stage before using full release rsync with `--delete`.
