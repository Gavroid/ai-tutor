# P0 Topic Quality Sweep — 2026-08-13

## Scope

Production API smoke for all P0 math topics.

Flow per topic:

1. `POST /api/v1/ai/explain`
2. `POST /api/v1/ai/generate-exercise`
3. `POST /api/v1/ai/check-answer` with wrong answer
4. `POST /api/v1/ai/check-answer` with correct answer
5. If all passed, `PATCH /api/v1/teacher/topics/{id}/status` to mark manual QA `ok`.

## Result

All 15 P0 topics passed the API learning smoke.

| Topic ID | Topic | Result | Notes |
|---:|---|---|---|
| 187 | Среднее арифметическое | PASS | explain/practice/wrong/correct ok; verified source present |
| 188 | Проценты | PASS | explain/practice/wrong/correct ok |
| 189 | Круговые диаграммы | PASS | explain/practice/wrong/correct ok |
| 192 | Разложение числа на простые множители | PASS | explain/practice/wrong/correct ok |
| 193 | Наибольший общий делитель. Взаимно простые числа | PASS | explain/practice/wrong/correct ok |
| 194 | Наименьшее общее кратное | PASS | explain/practice/wrong/correct ok |
| 195 | Приведение дробей к наименьшему общему знаменателю | PASS | explain/practice/wrong/correct ok |
| 196 | Сравнение, сложение и вычитание обыкновенных дробей | PASS | explain/practice/wrong/correct ok |
| 197 | Сложение и вычитание смешанных чисел | PASS | explain/practice/wrong/correct ok |
| 198 | Умножение смешанных чисел | PASS | explain/practice/wrong/correct ok |
| 199 | Нахождение дроби от числа | PASS | explain/practice/wrong/correct ok |
| 201 | Деление смешанных чисел | PASS | explain/practice/wrong/correct ok |
| 203 | Отношения | PASS | explain/practice/wrong/correct ok; verified source present |
| 204 | Пропорции | PASS | explain/practice/wrong/correct ok |
| 225 | Решение уравнений | PASS | explain/practice/wrong/correct ok |

## Observations

- P0 topics have material/chunks/fallback coverage.
- Most topics still have zero follow-up buttons, but this does not block the core learning loop.
- Verified source display is strict; only topics with full topic/page metadata show source chips.

## Follow-Up

- Add follow-up buttons for the P0 topics with `followup_count = 0`.
- Improve verified source metadata coverage for topics where RAG context works but source chips are omitted.
