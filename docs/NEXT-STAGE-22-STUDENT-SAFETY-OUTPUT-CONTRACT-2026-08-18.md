# Next Stage 22 — Student Safety Output Contract Pass — 2026-08-18

## Decision

Stage 22 is complete. Student-facing AI output now has a backend-level safety cleanup contract covering explain, hint, check, generate exercise, quiz fallback, and chat outputs.

The main fixed risk was not frontend rendering. It was backend fallback/structured paths that could pass raw provider content through to students when the model returned `<think>`, fenced JSON, `correct_answer`, broken math markers, or markdown fence noise.

## Files Changed

- `apps/backend/app/ai/service.py`
- `apps/backend/tests/test_ai_output_contract.py`

## Regression Coverage Added

New backend tests cover:

- generated exercise visible fields are cleaned: question, options, correct answer, explanation, typical mistakes;
- structured `check_answer` explanations and first errors are cleaned;
- fallback `check_answer` does not surface raw provider JSON;
- quiz fallback does not surface raw provider JSON;
- `<think>` / escaped think blocks do not survive;
- fenced JSON and `"correct_answer"` leak markers do not survive;
- broken LaTeX markers like `$$`, `\frac`, `\text` are normalized;
- markdown table/fence artefacts are stripped from student-visible text.

## Backend Fix

Added shared `_clean_student_visible_text(...)` in `app/ai/service.py`.

It removes:

- provider reasoning blocks (`<think>...</think>` and escaped variants);
- JSON objects containing answer/exercise/check keys;
- markdown code-fence markers, including inline ````json ... ``` `` cases;
- broken display/inline math markers;
- visible markdown artefacts already handled by `sanitize_output`.

Applied the cleaner to:

- `explain_topic` model response and retry response;
- `hint` response;
- `check_answer` structured fields and fallback content;
- generated exercise structured fields;
- quiz structured fields and fallback content;
- chat response before incomplete-fragment trimming.

## TDD Evidence

Initial focused test run failed on 4 expected leak paths:

```text
FAILED test_valid_generated_exercise_sanitizes_all_student_visible_fields
FAILED test_check_answer_structured_response_sanitizes_explanation
FAILED test_check_answer_fallback_does_not_surface_raw_provider_json
FAILED test_generate_quiz_fallback_does_not_surface_raw_provider_json
```

After the backend fix:

```text
.venv/bin/pytest tests/test_ai_output_contract.py -q
52 passed, 3 warnings
```

Broader backend AI/safety slice:

```text
.venv/bin/pytest \
  tests/test_ai_output_contract.py \
  tests/test_ai_output_regression_pack.py \
  tests/test_ai.py \
  tests/test_sprint8.py \
  tests/test_health.py -q
83 passed, 13 warnings
```

Existing regression pack also remained green:

```text
.venv/bin/pytest tests/test_ai_output_regression_pack.py tests/test_ai.py tests/test_sprint8.py -q
23 passed, 13 warnings
```

## Student Browser Smoke

Local/frontend smoke:

```text
npx playwright test e2e/mvp-student-flow.spec.ts --project=chromium
2 passed
```

LAN production smoke after targeted deploy:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/mvp-student-flow.spec.ts --project=chromium
2 passed
```

The smoke covers:

- student login;
- topic open;
- AI explain;
- practice generation;
- answer submission;
- clean feedback;
- chat message path;
- budget error display;
- no visible raw AI garbage in the main student surface.

## Production Deployment

A targeted backend deploy was required because this stage fixes student-facing backend output.

Backup/offsite before deploy:

```text
manifest-20260818T075953Z.md5
OFFSITE OK: hash verified manifest-20260818T075953Z.md5 (a89afa2bf6d59c089780c8122efbef58)
```

Deploy method:

```text
rsync apps/backend/app/ai/service.py -> production
cd /opt/ai-tutor/deploy
docker compose build backend
docker compose up -d --no-deps backend
```

Production health after deploy:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
backend running healthy
frontend running healthy
db running healthy
redis running healthy
prometheus running healthy
grafana/proxy running
```

The production marker was not advanced because deploy was targeted and the production tree remains in dirty/master-safe mode.

## Production Impact

- Backend service was rebuilt/recreated.
- No DB migration.
- No production data mutation.
- No Nightscout or external medical system touched.
- Parent privacy boundary unchanged.
- Algebra/Geometry preview status unchanged.

## Done Criteria

- Sweep explain/practice/check outputs for raw JSON, `<think>`, broken markdown, answer leaks: complete.
- Regression tests added for leak patterns: complete.
- Student browser smoke passed: complete.
- Mobile/readability risk reduced by backend math/markdown cleanup: complete.
- Backup/offsite before production deploy: complete.
- Production health verified after deploy: complete.
- Commit: pending at report creation.
