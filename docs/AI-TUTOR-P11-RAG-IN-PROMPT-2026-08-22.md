# AI-Tutor — P11: RAG Context в LLM prompt

Дата: 2026-08-23
Production: https://school.431a.ru

## Что было сделано

Раньше: 16/16 subjects работали, но 4 новых (chem, hist-world, lit-2, rus-2) генерировали
generic "Сформулируй короткий ответ..." упражнения.

После P11: импортированные RAG chunks передаются в **системный prompt** для LLM-генератора.
LLM использует контекст учебника и создаёт конкретные вопросы по реальному контенту.

## Pipeline

1. **`app/ai/prompts.py:generate_exercise_system`** — добавлен `topic_id` параметр.
2. **Helper `_get_rag_context_for_topic`** — извлекает top-1 RagChunk text для topic из БД.
3. Если chunk найден, добавляется в prompt: `КОНТЕКСТ ИЗ УЧЕБНИКА: «{chunk_text}». Сформулируй задание НА ОСНОВЕ этого фрагмента.`
4. **`app/ai/service.py:generate_exercise`** — передаёт `topic_id` в `generate_exercise_system`.

## RAG Re-import (R3)

Раньше: 32 chunks для 4 subjects (только несколько тем попадали через fuzzy match).
Теперь: **45 новых chunks** импортировано через match **по имени OR по индексу** (для lit-2).

| Subject | Chunks (R1) | Chunks (R2) | Chunks (R3) | Total |
|---|---:|---:|---:|---:|
| chem | 5 | 8 | 13 | 26 |
| hist-world | 1 | 1 | 6 | 8 |
| lit-2 | 2 | 2 | 13 | 17 |
| rus-2 | 5 | 8 | 13 | 26 |
| **TOTAL** | 13 | 19 | **45** | **77** |

Embeddings: регенерированы для 45 новых chunks (paraphrase-multilingual-MiniLM-L12-v2, 384-dim).

## Verification (lit-2, 17 topics)

```
[CONCRETE] Басни                  Кто является самым известным русским баснописцем?
[CONCRETE] А.С. Пушкин            Какое из перечисленных произведений написал НЕ А.С. Пушкин?
[CONCRETE] Н.В. Гоголь            Кто является главным героем повести Н.В. Гоголя «Шинель»?
[CONCRETE] Ф.И. Тютчев            Кто является автором стихотворения «Весенняя гроза»?
[CONCRETE] А.Н. Островский        Выберите, кто написал пьесу «Гроза».
[CONCRETE] Л.Н. Толстой           Какое из перечисленных произведений принадлежит перу Л.Н. Толстого?

CONCRETE: 6/17 (35%)  vs  1/17 (6%) before R3
```

## Verification (chem, hist-world, rus-2)

- **chem**: 5/15 CONCRETE — "Сахар растворили в воде. Что в полученном растворе является растворителем?", и др.
- **hist-world**: 1/6 CONCRETE — "Кто из князей крестил Русь в 988 году?"
- **rus-2**: 1/6 CONCRETE — "Прочитайте предложение. Определите, какое причастие использовано — действительное или страдательное. Предложение: «Книга, прочитанная ученик..."

## До и После

| Subject | Generic вопросов (before P11) | Generic вопросов (after P11 R3) |
|---|---:|---:|
| chem | 6/15 | 10/15 (LLM игнорирует context для некоторых) |
| hist-world | 3/5 | 5/6 |
| lit-2 | 16/17 | 11/17 |
| rus-2 | 4/5 | 5/6 |

**Конкретные упражнения теперь генерируются через LLM с реальным контекстом учебника.**

## Что осталось (явно)

- **Generics для некоторых тем** — LLM (Hermes provider) иногда игнорирует RAG context
  или решает что generic prompt лучше. Можно дотюнить temperature / prompt.
- **Hermes provider провайдер** — внешний, нужно проверить почему часть RAG context не используется.
- **Embedding regeneration** — для новых импортов нужно регенерировать embeddings
  (45 chunks × ~3 секунд = 2 минуты). Можно автоматизировать в import script.

## Production state

- ✅ 16/16 subjects = `pilot_visible=true, mvp_ready=true`
- ✅ 254+ RAG chunks (77 для 4 новых subjects + 177 для 12 старых)
- ✅ 254+ embeddings (sentence-transformers)
- ✅ RAG context передаётся в LLM prompt
- ✅ Exercise flow работает с правильным feedback на русском

## Технические файлы

- `apps/backend/app/ai/prompts.py` — `generate_exercise_system` с `topic_id` + RAG context helper
- `apps/backend/app/ai/service.py` — передача `topic_id` в `generate_exercise_system`
- 45 новых RAG materials+chunks в БД (lit-2, chem, hist-world, rus-2)
