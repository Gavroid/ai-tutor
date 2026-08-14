# Stage 03 — Math Fallback Task Quality Pass 1 Report — 2026-08-14

## Scope

Stage 03 target: replace generic fallback tasks with real school-style deterministic tasks for at least 15 high-impact math topics.

## Completed

- Expanded `apps/backend/scripts/math_fallback_seed.py` from 10 hand-authored topic fallbacks to 25.
- Added first-variant school-style tasks for these additional high-impact route topics:
  - `187` средние значения;
  - `188` проценты;
  - `189` круговые диаграммы;
  - `190` виды треугольников;
  - `191` множества;
  - `192` простые множители;
  - `193` НОД;
  - `194` НОК;
  - `195` общий знаменатель;
  - `196` сложение дробей;
  - `197` смешанные числа;
  - `198` умножение смешанных чисел;
  - `199` дробь от числа;
  - `201` деление смешанных чисел;
  - `202` дробные выражения.
- Kept existing specific fallbacks for `200`, `213`, `214`, `220`, `221`, `222`, `224`, `226`, `227`, `228`.
- Updated `docs/MATH-EDITORIAL-REVIEW-MATRIX-2026-08-14.md` to reflect 25/42 hand-authored first fallback variants.

## Quality Rules Applied

Each fallback row is:

- `single` choice;
- checkable;
- has at least 4 options;
- includes `correct_answer` in `options`;
- includes explanation;
- includes typical mistakes;
- avoids raw JSON / markdown tables / model-generated free text.

## Local Verification

```text
cd apps/backend
.venv/bin/pytest tests/test_math_fallback_seed.py tests/test_math_practice_variants_seed.py tests/test_health.py -q

12 passed, 3 warnings in 1.00s
```

## Production Backup / Offsite

Required backup was run before production mutation:

```text
backup manifest: /opt/ai-tutor/deploy/backup/_out/manifest-20260814T152458Z.md5
OFFSITE OK: hash verified manifest-20260814T152458Z.md5
SMB total after upload: 181 files
```

No secrets were printed in this report.

## Production Application

Because the production working tree is currently dirty and on `master`, a full git/release deploy would risk overwriting unrelated in-flight production files. Stage 03 used a narrower safe path:

1. `rsync` only `apps/backend/scripts/math_fallback_seed.py` to production.
2. `docker compose cp` the same script into the live backend container.
3. Run only `python -m scripts.math_fallback_seed --topics ...` for the 25 target topic IDs.

Seed result:

```text
updated: 25 topic IDs
missing: []
```

Script hash matched local/host/container:

```text
3318891bd2806211edcedb25c06904b465713d0c8d66f5ef87a74a563bf40460
```

## Production Smoke

Registry smoke checked representative topics `187`, `188`, `189`, `200`, `202`, `228`:

```text
topic=187 rows=1 answer_in_options=True
topic=188 rows=1 answer_in_options=True
topic=189 rows=1 answer_in_options=True
topic=200 rows=1 answer_in_options=True
topic=202 rows=1 answer_in_options=True
topic=228 rows=1 answer_in_options=True
```

Production health after seed:

```text
/ready  HTTP=200
/health HTTP=200
backend/db/frontend/prometheus/redis running healthy; grafana/proxy running
```

## Known Limitations

- Stage 03 improved the first deterministic fallback variant, not all three variants for every topic.
- Remaining 17 topics still need hand-authored first variants in Stage 04.
- Full production release marker was not advanced because this was a narrow script + registry seed, not a container rebuild/release deploy.

## Next Stage

Stage 04 should complete fallback quality across all 42 math topics and remove the remaining generic first variants.
