# AI-Tutor Pilot Plan

Date: 2026-07-30
Scope: MVP pilot for `Математика (6 класс - повторение пройденного материала)` only.

## Current MVP Baseline

The student path is working end-to-end on production:

1. Login/logout works for the test student.
2. Subject `Математика (6 класс - повторение пройденного материала)` has a real curriculum rebuilt from the two Vilenkin 6th grade textbook PDFs.
3. Current production curriculum state:
   - 42 topics
   - 42 topic-scoped learning materials
   - 832 total RAG chunks
4. Core topic flow works:
   - Explain
   - Practice
   - Submit wrong answer
   - Submit corrected answer
   - Chat
   - Clear
5. Known noisy UI element `Recovery mode` is hidden in the MVP lesson flow.
6. Student-facing technical artefacts are blocked by regression tests:
   - `<think>` / `&lt;think&gt;`
   - `&amp;gt;` / `&gt;`
   - `$$...$$`
   - `\frac`, `\text`
   - fenced JSON / `correct_answer`
   - markdown table separators

## Pilot Acceptance Criteria

A topic is considered pilot-ready when all checks below are true:

| Check | Meaning |
|---|---|
| Explain OK | Explanation is readable for a 6th/7th grade student and has no raw markup. |
| Practice OK | Practice question is concrete, answerable, and on-topic. |
| Wrong→Correct OK | Wrong answer gives useful feedback; corrected answer is accepted. |
| Chat OK | Chat answers without WS/budget/internal errors. |
| Clear OK | Clear removes exercise, feedback, chat, and input state. |
| Source Discipline OK | No misleading source is shown. Sources stay hidden until exact citation mapping is reliable. |

## Pilot Topic Priority

### P0 — Must Be Reliable Before Child Pilot

These topics are most useful for a short guided pilot and should have deterministic practice fallback:

1. Среднее арифметическое
2. Проценты
3. Круговые диаграммы
4. Разложение числа на простые множители
5. Наибольший общий делитель. Взаимно простые числа
6. Наименьшее общее кратное
7. Приведение дробей к наименьшему общему знаменателю
8. Сравнение, сложение и вычитание обыкновенных дробей
9. Сложение и вычитание смешанных чисел
10. Умножение смешанных чисел
11. Нахождение дроби от числа
12. Деление смешанных чисел
13. Отношения
14. Пропорции
15. Решение уравнений

### P1 — Next Wave

1. Виды треугольников
2. Понятие множества
3. Дробные выражения
4. Прямая и обратная пропорциональные зависимости
5. Масштаб
6. Симметрия
7. Положительные и отрицательные числа
8. Противоположные числа
9. Модуль числа
10. Сравнение положительных и отрицательных чисел
11. Сложение отрицательных чисел
12. Сложение чисел с разными знаками
13. Вычитание рациональных чисел
14. Умножение рациональных чисел
15. Деление рациональных чисел

### P2 — Later / After Pilot Feedback

1. Длина окружности и площадь круга. Шар
2. Изменение величин
3. Сложение с помощью координатной прямой
4. Рациональные числа
5. Свойства действий с рациональными числами
6. Раскрытие скобок
7. Коэффициент
8. Подобные слагаемые
9. Перпендикулярные прямые
10. Координатная плоскость
11. Столбчатые диаграммы и графики

## Execution Plan

### Phase 1 — Lock the Pilot Surface

- Keep the UI quiet and predictable.
- Keep recovery/CGM helper features out of the main lesson surface unless explicitly enabled.
- Keep student-facing sources hidden until citations can be proven exact.

### Phase 2 — Stabilize P0 Practice

- Add regression tests for P0 topic-specific deterministic fallback questions.
- Ensure no fallback exposes `AI`, `JSON`, `резервное`, or generic “Сформулируй короткий ответ”.
- Ensure each fallback has:
  - concrete question text;
  - deterministic correct answer;
  - student-readable explanation;
  - typical mistakes.

### Phase 3 — Topic QA Matrix

- Track all 42 topics in `docs/pilot-topic-matrix.md`.
- For every topic, record:
  - topic id;
  - section;
  - RAG chunk count;
  - priority;
  - fallback status;
  - manual walkthrough status.

### Phase 4 — Pilot Walkthrough

Manual test with Kirill-style account:

1. Open subject 3.
2. Test 3 P0 topics.
3. For each topic:
   - Explain
   - Practice
   - Wrong answer
   - Correct answer
   - Chat question
   - Clear
4. Record issues in the topic matrix.

## Current Known Risks

| Risk | Current Mitigation |
|---|---|
| AI returns invalid JSON for practice | Deterministic fallback per key topic. |
| AI generates off-topic task | Topic drift guards plus deterministic fallback for known topics. |
| AI budget blocks E2E | Reset test user budget only for smoke, or use admin smoke for explain. |
| Misleading source links | Student-facing sources hidden for now. |
| WS chat instability | Student chat uses HTTP endpoint instead of WS. |

## Next Engineering Steps

1. Implement deterministic fallback bank for all P0 topics.
2. Add tests proving P0 fallback coverage.
3. Run backend targeted + frontend typecheck + MVP E2E.
4. Deploy.
5. Run API smoke for P0 sample topics.
6. Update the topic matrix with verified statuses.
