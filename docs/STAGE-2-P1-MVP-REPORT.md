# Stage 2 P1 Expansion MVP Report

Date: 2026-07-30
Branch: `mvp-rescue`
Production host: `192.168.1.86`

## Result

Stage 2 — **P1 Expansion MVP** is complete.

The supported math pilot surface now covers:

- 15 P0 topics with fallback + explain/practice smoke readiness.
- 15 P1 topics with fallback + explain/practice smoke readiness.
- 30 total pilot-ready topics by automated smoke gates.

## Scope Completed

P1 topics completed:

| Topic ID | Topic | Explain QA | Practice QA |
|---:|---|---|---|
| 190 | Виды треугольников | Smoke OK | Smoke OK |
| 191 | Понятие множества | Smoke OK | Smoke OK |
| 202 | Дробные выражения | Smoke OK | Smoke OK |
| 205 | Прямая и обратная пропорциональные зависимости | Smoke OK | Smoke OK |
| 206 | Масштаб | Smoke OK | Smoke OK |
| 207 | Симметрия | Smoke OK | Smoke OK |
| 209 | Положительные и отрицательные числа | Smoke OK | Smoke OK |
| 210 | Противоположные числа | Smoke OK | Smoke OK |
| 211 | Модуль числа | Smoke OK | Smoke OK |
| 212 | Сравнение положительных и отрицательных чисел | Smoke OK | Smoke OK |
| 215 | Сложение отрицательных чисел | Smoke OK | Smoke OK |
| 216 | Сложение чисел с разными знаками | Smoke OK | Smoke OK |
| 217 | Вычитание рациональных чисел | Smoke OK | Smoke OK |
| 218 | Умножение рациональных чисел | Smoke OK | Smoke OK |
| 219 | Деление рациональных чисел | Smoke OK | Smoke OK |

## Engineering Work Completed

- Added deterministic fallback bank for all 15 P1 topics.
- Added regression coverage:
  - `test_generate_exercise_p1_fallback_bank_is_student_ready`
  - short explain fallback regression for overly short model output.
- Added explain fallback for `Деление рациональных чисел`.
- Added minimum explain quality threshold: model output shorter than 250 chars falls back to safe instructional text.
- Updated `docs/pilot-topic-matrix.md` for P1 smoke readiness.

## Verification

Local gates:

- Backend targeted: `57 passed`
- Frontend typecheck: passed
- MVP E2E: `2 passed`

Production smoke:

- `/ready`: ready, HTTP 200
- P1 practice smoke: 15/15 passed
- P1 explain smoke: 15/15 passed
- Sources: hidden for all checked topics
- No visible technical artefacts in smoke checks

## Remaining Work After Stage 2

Non-blocking for this MVP:

1. Manual QA for P1 topics remains `TODO`.
2. P2 topics still need fallback and smoke readiness if they become pilot scope.
3. Source links remain hidden until citation-safe source mapping is implemented.
4. Dedicated E2E/test-user AI budget isolation is still recommended.
5. WS remains outside the stable student path; HTTP chat remains the supported MVP path.

## Next Recommended Stage

Proceed with one of two paths:

1. **Manual validation path:** run manual walkthrough on 5–10 P1 topics and update matrix.
2. **Stage 3 engineering path:** implement citation-safe RAG sources so sources can be safely shown again.

Do not expand to new subjects until P1 manual feedback is collected or explicitly waived.
