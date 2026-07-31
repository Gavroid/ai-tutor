# Stage 3B UX Polish Closure Report

Date: 2026-07-31 15:49 MSK
Branch: `mvp-rescue`
Production marker before docs update: `0cf69d4`

## Result

Stage 3B — **Lesson UX Polish after Citation-Safe Sources** is closed.

This stage was focused on manual walkthrough issues found after Stage 3:

- source label position and text overflow;
- clickable follow-up choices after explanations;
- removing answer-copy UX;
- practice repetition after pressing `Практика` / `Следующее задание`;
- residual LaTeX-like text artefacts in explanations.

## Completed Changes

### 1. Source label and text layout

- Verified source label is displayed before explanation text.
- Assistant message bubbles use overflow protection.
- Long lines and formula-like text now use break-word styling.
- Raw RAG snippets are still not displayed to the student.

### 2. Guided follow-up buttons

Added topic-aware follow-up buttons:

- `Среднее арифметическое`:
  - `Среднее чисел`
  - `Средняя скорость`
  - `Средний вес`
- `Наибольший общий делитель. Взаимно простые числа`:
  - `Попробовать самому`
  - `Второй способ`
- Sequential topics such as equations can show `Далее`.

Current implementation is intentionally simple and frontend-driven. It is good enough for MVP pilot, but should later move into structured backend/teacher-authored subtopic metadata.

### 3. Copy prevention

- Removed the visible `Копировать` button.
- Lesson area prevents `copy` and `cut` events.
- Lesson area uses `select-none` to reduce casual copying.

This is UX-level friction, not DRM/security. It prevents easy copying during lessons but does not attempt to block screenshots, DevTools, or accessibility tooling.

### 4. Practice rotation

- `Практика` now advances a small seed instead of always requesting the same auto difficulty.
- `Следующее задание` appears after a correct answer.
- For the GCD topic, deterministic fallback now rotates across:
  - `18 и 24` → `6`
  - `12 и 25` → `1`
  - `30 и 45` → `15`

### 5. Text artefact cleanup

Sanitizer now normalizes:

- `\dots` / `\ldots` → `…`
- `x_1`, `x_2`, `x_n` → `x1`, `x2`, `xn`

## Verification

Local gates:

- Backend targeted: `62 passed`
- Frontend typecheck: passed
- MVP E2E: `2 passed`

Production smoke:

- `/ready`: ready, HTTP 200
- Prod marker: `0cf69d4`
- GCD practice rotation smoke: difficulty 1/2/3 returned three different questions.

## Remaining Known Limitations

- Follow-up buttons are hardcoded by topic name in frontend.
- Practice rotation uses difficulty as a temporary seed for deterministic fallbacks.
- Sanitizer still may need future improvements for advanced math notation (`\bar{x}`, `\sum`, `\approx`) if real model output continues to produce it.
- Source labels are page-level verified, not quote-level semantic citations.

## Status

Closed for MVP purposes.

Next stage: **Stage 4 — Teacher Content Workflow MVP**.
