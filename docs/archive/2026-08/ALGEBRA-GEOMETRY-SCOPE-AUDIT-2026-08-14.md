# Algebra / Geometry Scope Audit — 2026-08-14

## Scope

Stage 11 goal: understand what exists for Algebra and Geometry before adding route plans, sources, or practice banks.

This audit is based on production DB/API evidence, not guesses.

## Production Health During Audit

```text
/ready HTTP=200
```

No production mutation was performed in this stage.

## Subject Summary

| Subject ID | Code | Subject | Topics | Materials | RAG chunks | Fallback topics | Follow-up topics | Current readiness |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 4 | algebra | Алгебра | 19 | 1 | 1 | 0 | 2 | preview, rag_ready=false, practice_ready=false |
| 5 | geom | Геометрия | 13 | 0 | 0 | 0 | 0 | preview, rag_ready=false, practice_ready=false |

Reference comparison:

| Subject ID | Code | Subject | Topics | Materials | RAG chunks | Fallback topics | Follow-up topics | Current readiness |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 3 | math | Математика (6 класс — повторение) | 42 | 42 | 20289 | 42 | 42 | mvp_ready, rag_ready=true, practice_ready=true |

## Public/API Readiness

`/api/v1/subjects` reports:

```text
Алгебра: mvp_status=preview, rag_ready=false, practice_ready=false
Геометрия: mvp_status=preview, rag_ready=false, practice_ready=false
```

Route-plan endpoints currently return empty arrays:

```text
/api/v1/subjects/4/route-plan => []
/api/v1/subjects/5/route-plan => []
```

This is correct and honest: neither subject should be shown as pilot-ready.

## Algebra Topic Inventory

| Topic ID | Section | Topic | Order | Materials | RAG chunks | Fallback | Follow-up |
|---:|---|---|---:|---:|---:|---:|---:|
| 34 | Выражения, тождества, уравнения | Числовые выражения | 0 | 1 | 1 | 0 | likely default/registry contributes to total 2 |
| 35 | Выражения, тождества, уравнения | Буквенные выражения (переменная) | 1 | 0 | 0 | 0 | — |
| 36 | Выражения, тождества, уравнения | Преобразование буквенных выражений | 2 | 0 | 0 | 0 | — |
| 37 | Выражения, тождества, уравнения | Линейное уравнение с одной переменной | 3 | 0 | 0 | 0 | likely default/registry contributes to total 2 |
| 38 | Функции | Понятие функции | 0 | 0 | 0 | 0 | — |
| 39 | Функции | Линейная функция y = kx + b | 1 | 0 | 0 | 0 | — |
| 40 | Функции | Прямая пропорциональность | 2 | 0 | 0 | 0 | — |
| 41 | Степень с натуральным показателем | Определение степени | 0 | 0 | 0 | 0 | — |
| 42 | Степень с натуральным показателем | Свойства степени | 1 | 0 | 0 | 0 | — |
| 43 | Степень с натуральным показателем | Одночлены | 2 | 0 | 0 | 0 | — |
| 44 | Многочлены | Понятие многочлена | 0 | 0 | 0 | 0 | — |
| 45 | Многочлены | Сложение и вычитание многочленов | 1 | 0 | 0 | 0 | — |
| 46 | Многочлены | Умножение одночлена на многочлен | 2 | 0 | 0 | 0 | — |
| 47 | Многочлены | Умножение многочлена на многочлен | 3 | 0 | 0 | 0 | — |
| 48 | Многочлены | Формулы сокращённого умножения | 4 | 0 | 0 | 0 | — |
| 49 | Системы линейных уравнений | Линейное уравнение с двумя переменными | 0 | 0 | 0 | 0 | — |
| 50 | Системы линейных уравнений | Графический способ решения | 1 | 0 | 0 | 0 | — |
| 51 | Системы линейных уравнений | Способ подстановки | 2 | 0 | 0 | 0 | — |
| 52 | Системы линейных уравнений | Способ сложения | 3 | 0 | 0 | 0 | — |

## Geometry Topic Inventory

| Topic ID | Section | Topic | Order | Materials | RAG chunks | Fallback | Follow-up |
|---:|---|---|---:|---:|---:|---:|---:|
| 53 | Начальные геометрические сведения | Прямая, отрезок, луч, угол | 0 | 0 | 0 | 0 | — |
| 54 | Начальные геометрические сведения | Измерение отрезков и углов | 1 | 0 | 0 | 0 | — |
| 55 | Начальные геометрические сведения | Смежные и вертикальные углы | 2 | 0 | 0 | 0 | — |
| 56 | Начальные геометрические сведения | Перпендикулярные прямые | 3 | 0 | 0 | 0 | — |
| 57 | Треугольники | Признаки равенства треугольников | 0 | 0 | 0 | 0 | — |
| 58 | Треугольники | Медиана, биссектриса, высота | 1 | 0 | 0 | 0 | — |
| 59 | Треугольники | Равнобедренный треугольник | 2 | 0 | 0 | 0 | — |
| 60 | Треугольники | Окружность. Задачи на построение | 3 | 0 | 0 | 0 | — |
| 61 | Параллельные прямые | Признаки параллельности прямых | 0 | 0 | 0 | 0 | — |
| 62 | Параллельные прямые | Свойства параллельных прямых | 1 | 0 | 0 | 0 | — |
| 63 | Соотношения между сторонами и углами треугольника | Сумма углов треугольника | 0 | 0 | 0 | 0 | — |
| 64 | Соотношения между сторонами и углами треугольника | Внешний угол треугольника | 1 | 0 | 0 | 0 | — |
| 65 | Соотношения между сторонами и углами треугольника | Неравенство треугольника | 2 | 0 | 0 | 0 | — |

## Missing Work Estimate

Algebra:

- Route plan: missing for 19/19 topics.
- Verified source/RAG coverage: 18/19 topics missing material and chunks; 1/19 has a minimal source/chunk only.
- Deterministic fallback practice: 19/19 topics missing registry fallback rows.
- Follow-up coverage: 17/19 topics missing followups if counting current registry/default coverage of 2.
- Readiness: preview only.

Geometry:

- Route plan: missing for 13/13 topics.
- Verified source/RAG coverage: 13/13 missing.
- Deterministic fallback practice: 13/13 missing.
- Follow-up coverage: 13/13 missing.
- Readiness: preview only.

## Recommended Month 2 Order

1. Stage 12 — Algebra route plan first, as preview route only.
2. Stage 13 — Geometry route plan next, as preview route only.
3. Stage 14–15 — Source/RAG passes; do not reuse math sources misleadingly.
4. Stage 16–17 — Deterministic fallback banks for P0/pilot topics first.
5. Stage 18 — Multi-subject readiness UI should continue showing Math as ready and Algebra/Geometry as preview until route + source + fallback + smoke are complete.

## Verification Evidence

Production DB subject/topic counts:

```text
4|algebra|Алгебра|19
5|geom|Геометрия|13
```

Production source/RAG counts:

```text
4|Алгебра|1 material|1 chunk
5|Геометрия|0 materials|0 chunks
```

Registry coverage:

```text
subject=4|topics=19|fallback_topics=0|followup_topics=2|status_topics=0
subject=5|topics=13|fallback_topics=0|followup_topics=0|status_topics=0
```

No production mutation was performed.
