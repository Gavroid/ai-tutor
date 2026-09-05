# Stage 15 — Geometry Source And RAG Readiness Pass — 2026-08-15

## Scope

Stage 15 goal: prepare Geometry sources like math sources, or document blockers honestly.

## Result

Geometry source/RAG readiness is **not ready**. Production currently has `0/13` verified source materials and `0/13` RAG chunks for Geometry.

No production mutation was performed in this stage.

## Production Evidence

Geometry topic source/RAG counts from production DB:

```text
53|Прямая, отрезок, луч, угол|0|0
54|Измерение отрезков и углов|0|0
55|Смежные и вертикальные углы|0|0
56|Перпендикулярные прямые|0|0
57|Признаки равенства треугольников|0|0
58|Медиана, биссектриса, высота|0|0
59|Равнобедренный треугольник|0|0
60|Окружность. Задачи на построение|0|0
61|Признаки параллельности прямых|0|0
62|Свойства параллельных прямых|0|0
63|Сумма углов треугольника|0|0
64|Внешний угол треугольника|0|0
65|Неравенство треугольника|0|0
```

Production `/ready` was healthy during the audit.

## Source Research

Candidate sources checked:

1. Google Books / commercial textbook previews.
   - Not suitable for RAG import; no full retrievable open source file.
2. Random public PDFs and school mirrors for Geometry 7–9 textbooks.
   - Content appears to be copyrighted textbook scans/redistributions.
   - License certainty is insufficient.
3. Internet Archive Geometry 7–9 items.
   - Some files are downloadable; one search result indicates `Usage: Attribution-NonCommercial` for a related item.
   - Rights/license are still not sufficient for this project’s verified-source standard without explicit approval.
4. Miscellaneous geometry reference PDFs.
   - Often compiled from copyrighted textbooks, with no clear reusable license.
   - Not imported.

## Current Geometry Readiness

| Coverage item | Status |
|---|---:|
| Geometry route plan | 13/13 preview route exists |
| Verified source materials | 0/13 |
| RAG chunks | 0/13 |
| Deterministic fallback practice | 0/13 |
| Followups | 0/13 |
| Subject readiness | preview only |

## Decision

Do **not** proceed as if Geometry RAG is ready. Stage 15 closes as an honest blocker/audit pass:

- no unverified textbook imported;
- Geometry remains preview;
- source acquisition/approval is required before Geometry can become pilot-ready.

## Recommended Next Step

Stage 16 and Stage 17 can still create deterministic practice banks for preview/pilot topics, but Algebra/Geometry must remain `preview` until verified sources are acquired and indexed.

Acceptable source paths:

- owner-approved uploaded textbook/source files;
- explicitly open-license Geometry 7 source with retrievable file and license page;
- internally authored source notes owned by the project.
