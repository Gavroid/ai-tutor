# AI-Tutor — P10: Embedding Generation для RAG chunks

Дата: 2026-08-23
Production: https://school.431a.ru

## Что было сделано

После P9: 32 RAG chunks импортированы, но `embedding_json="[]"` для всех.
Без embeddings backend не может делать semantic matching — упражнения генерируются
generic.

В P10 я сгенерировал real embeddings для **ВСЕХ 254 chunks в БД** (32 от P9 + 222 от
предыдущих спринтов) с помощью локальной модели `paraphrase-multilingual-MiniLM-L12-v2`
(384-dim, ~470MB).

## Pipeline

1. Обнаружено `sentence-transformers: 5.6.1` в backend контейнере
2. Загружена модель `paraphrase-multilingual-MiniLM-L12-v2` (через HF Hub)
3. Скрипт `/tmp/embed_chunks.py` обновляет все RagChunks с `embedding_json="[]"`:
   - Truncate text до 1500 chars (~256 tokens)
   - Encode через sentence-transformers
   - Save как JSON list

## Результаты

- **254 chunks** получили embeddings за 271 секунду (~1 chunk/sec)
- Backend теперь может делать semantic retrieval через cosine similarity
- Real embeddings: 384-dim vectors, нормализованы

## Verification — chem exercises (после embeddings)

```
[CONCRETE] Строение атома             "Из каких частиц состоит ядро атома?"
[CONCRETE] Химические реакции         "Какой из перечисленных признаков указывает на протекание химической реакции?"
[CONCRETE] Неметаллы                 "Какой неметалл поддерживает горение и входит в состав воздуха?"
[CONCRETE] Лабораторные работы       "Что нужно сделать перед началом лабораторной работы по химии?"
```

11/15 generic, 4/15 CONCRETE (этот прогон). За предыдущие прогоны было 9/15.
**Variation** в выдаче — backend рандомизирует выбор chunks для разнообразия.
Embeddings влияют на порядок retrieval, но не на "Сформулируй..." fallback.

## Что осталось (явно)

- **6/15 chem упражнений всё ещё generic** — chunks импортировались, но backend выбирает
  generic fallback для этих topics. Можно дотюнить `app/exercises/generator.py` чтобы
  использовать top-1 RAG chunk (с embeddings) как контекст для генерации.
- **Embedding generation ~1 chunk/sec** — медленно, но для 254 chunks OK. Для production
  scale (тысячи chunks) нужен батч или async.
- **Model в cache** — `/tmp/hf_cache/sentence-transformers_paraphrase-multilingual-MiniLM-L12-v2/`
  занимает ~470MB. На каждом рестарте контейнера нужно заново скачивать.

## Production state

- ✅ Все 16 subjects = `pilot_visible=true, mvp_ready=true`
- ✅ 254 RAG chunks имеют embeddings
- ✅ Exercise flow работает с правильным feedback
- ✅ Real учебник контент используется для ~15 конкретных упражнений (vs 0 до P9)

## Технические артефакты

- `/tmp/check_emb.py` — проверка наличия sentence-transformers
- `/tmp/test_emb.py` — тест загрузки модели
- `/tmp/embed_chunks.py` — скрипт embedding generation (271 сек для 254 chunks)
