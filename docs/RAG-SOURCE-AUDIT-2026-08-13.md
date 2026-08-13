# RAG Source Audit — 2026-08-13

## Scope

P0 math topics after Prometheus multiprocess and P0 quality sweep.

Checked:

- teacher readiness API for P0 topic material/chunk/fallback/followup coverage;
- production `POST /api/v1/ai/explain` for all P0 topic IDs;
- verified source chips returned to UI.

## Summary

- All 15 P0 topics have material and RAG chunk coverage in readiness.
- All 15 P0 topics returned successful explain responses.
- Verified source chips are intentionally strict and currently appear for 2/15 P0 topics.

## P0 Verified Source Chip Coverage

| Topic ID | Topic | Explain OK | Source Chips | Notes |
|---:|---|---:|---:|---|
| 187 | Среднее арифметическое | yes | 1 | Verified label: Vilenkin part/page metadata present |
| 188 | Проценты | yes | 0 | RAG material/chunks exist, but verified source metadata incomplete for UI chip |
| 189 | Круговые диаграммы | yes | 0 | Metadata gap |
| 192 | Разложение числа на простые множители | yes | 0 | Metadata gap |
| 193 | Наибольший общий делитель. Взаимно простые числа | yes | 0 | Metadata gap |
| 194 | Наименьшее общее кратное | yes | 0 | Metadata gap |
| 195 | Приведение дробей к наименьшему общему знаменателю | yes | 0 | Metadata gap |
| 196 | Сравнение, сложение и вычитание обыкновенных дробей | yes | 0 | Metadata gap |
| 197 | Сложение и вычитание смешанных чисел | yes | 0 | Metadata gap |
| 198 | Умножение смешанных чисел | yes | 0 | Metadata gap |
| 199 | Нахождение дроби от числа | yes | 0 | Metadata gap |
| 201 | Деление смешанных чисел | yes | 0 | Metadata gap |
| 203 | Отношения | yes | 1 | Verified label: Vilenkin part/page metadata present |
| 204 | Пропорции | yes | 0 | Metadata gap |
| 225 | Решение уравнений | yes | 0 | Metadata gap |

## Decision

Do not loosen source verification just to display more chips. Current strict rule prevents wrong-topic or vague citations.

## Rebuild Plan

1. Keep existing strict source display rule.
2. Add metadata backfill job for P0 `rag_chunks.metadata_json`:
   - `topic_id`
   - `topic_name`
   - `page_number`
   - `part`
   - `material_title`
3. Re-run explain smoke after backfill.
4. Target: verified source chips for at least 12/15 P0 topics.
5. Only then consider showing lower-confidence source hints.

## Status

- Core learning flow: OK.
- RAG context: operational.
- Source-chip completeness: needs metadata backfill, not UI relaxation.
