# Stage 1 Final MVP Report — Guided P0 Pilot MVP

Date: 2026-07-30 17:58 MSK
Branch: `mvp-rescue`
Production host: `192.168.1.86`

## Result

Stage 1 — **Guided P0 Pilot MVP** is complete.

The product is ready for the next controlled pilot round on the P0 math topic set.

## Final Stage 1 Scope

Supported subject:

- `Математика (6 класс - повторение пройденного материала)`

Production content state:

- 42 real topics rebuilt from the two Vilenkin 6th grade textbook PDFs.
- 42 topic-scoped learning materials.
- 832 RAG chunks.
- 15 P0 topics with smoke-ready explain/practice.
- 5 P0 topics manually walked through and marked `Manual OK`.

## Manual Walkthrough Completed

The user manually tested these five P0 topics:

| Topic ID | Topic | Manual QA |
|---:|---|---|
| 187 | Среднее арифметическое | Manual OK |
| 188 | Проценты | Manual OK |
| 189 | Круговые диаграммы | Manual OK |
| 196 | Сравнение, сложение и вычитание обыкновенных дробей | Manual OK |
| 225 | Решение уравнений | Manual OK |

User-reported final result after budget UI fix: all tests work.

## Stage 1 Acceptance Criteria

| Criterion | Status |
|---|---|
| Login/logout works | Pass |
| Explain works on manual P0 topics | Pass |
| Practice works on manual P0 topics | Pass |
| Wrong answer gives feedback | Pass |
| Correct answer after wrong answer works | Pass |
| Chat works | Pass |
| Clear works | Pass |
| No misleading sources shown | Pass — sources hidden |
| No recovery/debug banner in lesson flow | Pass |
| AI budget error is understandable | Pass — no longer shown as provider outage |
| P0 smoke coverage | Pass — 15/15 explain + practice smoke OK |

## Key Fixes Completed During Stage 1

- Rebuilt real math curriculum/RAG.
- Hid unreliable student-facing sources.
- Added deterministic fallback bank for P0 practice topics.
- Fixed AI output artefacts:
  - reasoning blocks;
  - escaped JSON;
  - visible `&gt;`/`&amp;gt;`;
  - `$$`, `\frac`, `\text` artefacts;
  - markdown table separators.
- Moved student chat to HTTP path instead of fragile WS path.
- Fixed clear behavior.
- Fixed wrong→correct practice flow.
- Hid Recovery mode banner from MVP lesson flow.
- Fixed frontend 429 budget messaging.

## Current Source of Truth

| File | Purpose |
|---|---|
| `docs/PILOT_PLAN.md` | MVP pilot scope and process. |
| `docs/pilot-topic-matrix.md` | 42-topic readiness matrix. |
| `docs/GLOBAL_DEVELOPMENT_PLAN.md` | Multi-stage product roadmap. |
| `docs/STAGE-1-FINAL-MVP-REPORT.md` | This Stage 1 completion record. |

## Remaining Non-Blocking Risks

| Risk | Notes |
|---|---|
| P1/P2 topics not manually validated | Tracked in topic matrix. |
| Sources hidden | Safer than misleading citations; Stage 3 covers citation-safe sources. |
| AI budget can still affect real sessions after heavy testing | UI now explains limit; Stage 6 should add dedicated test budget/user. |
| WS still not part of stable student path | Student path uses HTTP; harden or remove WS later. |
| Test warnings remain | Not blocking; cleanup after pilot stability. |

## Next Stage Recommendation

Proceed to **Stage 2 — P1 Expansion MVP** only after one more short real-use session confirms no hidden P0 blockers.

Stage 2 should:

1. Add fallback bank for P1 topics.
2. Run P1 explain/practice smoke.
3. Keep P0 regression gates green.
4. Continue hiding sources until exact citation mapping is implemented.
