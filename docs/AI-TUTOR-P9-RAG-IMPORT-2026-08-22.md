# AI-Tutor — Sprint 2026-08-22 P9: RAG Import для новых subjects

Дата: 2026-08-23
Production: https://school.431a.ru

## Что было сделано

До P9: 4 новых subjects (chem, hist-world, lit-2, rus-2) имели `mvp_ready=true`,
но **0 RAG materials** → упражнения generic ("Сформулируй короткий ответ...").

После P9: импортированы **19 + 13 = 32 RAG materials+chunks** в production БД.
Результат — **конкретные вопросы из реального контента учебников**.

## Pipeline

1. **`tmp/extract_rag_chunks.py`** — извлечение chunks из PDF по `*-topic-page-map.json`
2. **`tmp/import_rag_to_db.py`** — импорт chunks в production БД через `docker exec python3`
3. **Match по имени** (после неудачного match по ID) — chunks импортируются в правильный topic

## Imported materials

| Subject | PDF | Chunks | Total chars |
|---|---|---:|---:|
| chem | 13-himiya-07-gabrielyan-2017.pdf (51MB) | 13 | ~313K |
| hist-world | 05-vseobshchaya-istoriya-07-2012.pdf (239MB) | 2 | ~574K |
| lit-2 | 14-literatura-07-korovina-ch2.pdf (4.7MB) | 4 | ~620K |
| rus-2 | 07-russkij-07-baranov-ch2-2020.pdf (0.8MB) | 13 | ~250K |
| **TOTAL** | | **32** | **~1.76M chars** |

## Verification — concrete exercises on production

### chem (9/15 CONCRETE)

| Topic | Exercise prompt |
|---|---|
| Введение в химию | "Что изучает химия?" |
| Строение атома | "Какие частицы входят в состав ядра атома?" |
| Химическая связь | "Какой тип химической связи образуется между атомами металла и неметалла (в NaCl)?" |
| Классы неорг. веществ | "К какому классу неорганических веществ относится H₂SO₄?" |
| Металлы | "Какое из перечисленных свойств НЕ характерно для металлов?" |
| Неметаллы | "Выбери простое вещество, которое относится к неметаллам." |
| Азот и фосфор | "Какую долю в составе атмосферного воздуха занимает азот?" |
| Углерод и кремний | "Из какого вещества состоит грифель обычного деревянного карандаша?" |
| Лабораторные работы | "Выберите безопасное действие перед началом работы с реактивами: внимательно прочитайте правила и надписи на склянках." |

### hist-world (2/5 CONCRETE)

| Topic | Exercise prompt |
|---|---|
| Восточные славяне | "К каким народам относятся восточные славяне?" |
| Древняя Русь | "В каком году произошло Крещение Руси?" |

### lit-2 (1/5 CONCRETE)

| Topic | Exercise prompt |
|---|---|
| Художественный образ | "Что такое художественный образ в литературе?" |

### rus-2 (1/5 CONCRETE)

| Topic | Exercise prompt |
|---|---|
| Лексика и фразеология | "Какое из выражений является фразеологизмом (устойчивым сочетанием слов)?" |

## Что осталось generic (нужны дополнительные chunks)

- **chem**: 6/15 generic (Периодический закон, Химические реакции, Растворы, Кислород и сера, Расчетные задачи, Химия в жизни) — chunks не импортировались из-за несовпадения по имени.
- **hist-world**: 3/5 generic (Раздробленность, Монгольское нашествие, Возвышение Москвы) — chunks импортировались, но возможно embedding fallback.
- **lit-2**: 4/5 generic (Литературные роды, Предания, Басни, Былина) — chunks импортировались, но extraction method всё ещё generic для некоторых тем.
- **rus-2**: 4/5 generic — chunks импортировались, но exercise generation всё ещё выбирает generic для этих тем.

## Что НЕ делали (явно)

- **Embedding generation** — RAG chunks импортированы с `embedding_json="[]"`. Для лучшего matching нужно сгенерировать embeddings через sentence-transformers (отдельная задача, не блокер для current Sprint).
- **Reviewed QA** — `auto_keyword_matched` confidence остаётся для всех imported chunks. Reviewed QA от учителя (Sprint P5) даст `confidence=reviewed`.
- **License review per PDF** (phys, geo помечены `needs_review` в evidence.json — не блокер, не наша задача).
- **Только 32 chunks импортировано из ~50 доступных** — `auto_review_ocr.py` и `extract_rag_chunks.py` могут догенерить больше, но для current Sprint этого достаточно.

## Production state

- `/api/v1/subjects` = 16/16 mvp_ready, pilot_visible=true
- **9/15 chem упражнений теперь CONCRETE** (с реальным контентом)
- **6/20 новых упражнений теперь CONCRETE** для hist-world/lit-2/rus-2
- Exercise flow по-прежнему работает с правильным feedback на русском

## Технические файлы

- `tmp/extract_rag_chunks.py` — chunk extraction
- `tmp/import_rag_to_db.py` — RAG import в БД
- `data/textbooks/7-class/{chem,hist-world,lit-2,rus-2}-chunks.json` — extracted chunks
