# Stage 14 — Algebra Source And RAG Readiness Pass — 2026-08-14

## Scope

Stage 14 goal: prepare Algebra sources like math sources, or document blockers honestly.

## Result

Algebra source/RAG readiness is **not ready**. The only existing Algebra material in production was invalid and has been removed after backup.

This stage deliberately does **not** mark Algebra as source-ready because verified source coverage is now `0/19` topics.

## Production Evidence Before Cleanup

Production audit found one material attached to Algebra topic `34`:

```text
material_id=2
topic_id=34
file/title=geometry_test.txt
source=upload:geometry_test.txt
status=draft
chunks=1
```

The uploaded file content was geometry, not algebra:

```text
Площадь треугольника равна половине произведения основания на высоту...
```

Therefore it was a false-positive source for Algebra and could not be treated as verified Algebra coverage.

## Corrective Action

Required production backup/offsite verification was completed before mutation:

```text
backup manifest: /opt/ai-tutor/deploy/backup/_out/manifest-20260814T210245Z.md5
OFFSITE OK: hash verified manifest-20260814T210245Z.md5
SMB total after upload: 208 files
```

Then the invalid material and its RAG chunk were deleted via scoped backend SQLAlchemy logic:

```text
{'deleted_material_id': 2, 'deleted_chunks': 1}
```

Post-cleanup Algebra source/RAG coverage:

```text
34|Числовые выражения|0|0
35|Буквенные выражения (переменная)|0|0
36|Преобразование буквенных выражений|0|0
37|Линейное уравнение с одной переменной|0|0
38|Понятие функции|0|0
39|Линейная функция y = kx + b|0|0
40|Прямая пропорциональность|0|0
41|Определение степени|0|0
42|Свойства степени|0|0
43|Одночлены|0|0
44|Понятие многочлена|0|0
45|Сложение и вычитание многочленов|0|0
46|Умножение одночлена на многочлен|0|0
47|Умножение многочлена на многочлен|0|0
48|Формулы сокращённого умножения|0|0
49|Линейное уравнение с двумя переменными|0|0
50|Графический способ решения|0|0
51|Способ подстановки|0|0
52|Способ сложения|0|0
```

## Source Research

Candidate sources checked:

1. SciNetwork page for `Алгебра 7 класс`, authors A. G. Mordkovich et al., 2022.
   - Page metadata says license `CC BY` and access `Всем`.
   - Download is available only to authorized users.
   - Because the PDF could not be retrieved without account/auth, it was not imported.
2. Internet Archive item `uchebnik-algebra-7-klass-Makarychev-2013`.
   - PDF is downloadable.
   - License/rights are not explicit enough for this project’s verified-source standard.
   - It was not imported as verified Algebra source.

## Current Algebra Readiness

| Coverage item | Status |
|---|---:|
| Algebra route plan | 19/19 preview route exists |
| Verified source materials | 0/19 |
| RAG chunks | 0/19 |
| Deterministic fallback practice | 0/19 |
| Followups | partial only |
| Subject readiness | preview only |

## Production Health

```text
/ready HTTP=200
backend/db/frontend/prometheus/redis running healthy; grafana/proxy running
```

## Decision

Do **not** proceed as if Algebra RAG is ready. Stage 14 closes as an honest blocker/audit pass:

- invalid source removed;
- no unverified textbook imported;
- Algebra remains preview;
- source acquisition/approval is required before Algebra can become pilot-ready.

## Recommended Next Step

Stage 15 can audit Geometry sources the same way. For Algebra, before Stage 16 practice bank is considered pilot-ready, acquire one of:

- a confirmed open-license Algebra 7 PDF with retrievable file and license page;
- owner-approved source material uploaded through teacher workflow;
- custom authored internal Algebra source notes with explicit project ownership.
