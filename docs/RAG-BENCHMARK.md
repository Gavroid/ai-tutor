# RAG Benchmark Report (Sprint 43)

**Дата:** 2026-07-24
**Production:** 192.168.1.86 (LXC, 4GB RAM)
**RAG mode:** hash-based pseudo-embeddings (Sprint 20 fallback)
**Total questions:** 27

## Метрики

| Метрика | Значение |
|---------|----------|
| Recall@3 | 0.00% |
| Recall@5 | 0.00% |
| MRR (Mean Reciprocal Rank) | 0.000 |

## По предметам

| Subject | n | Recall@3 | Recall@5 | MRR |
|---------|---|----------|----------|-----|
| Biology | 3 | 0.00% | 0.00% | 0.000 |
| Chemistry | 3 | 0.00% | 0.00% | 0.000 |
| English | 3 | 0.00% | 0.00% | 0.000 |
| Geography | 3 | 0.00% | 0.00% | 0.000 |
| History | 3 | 0.00% | 0.00% | 0.000 |
| Informatics | 3 | 0.00% | 0.00% | 0.000 |
| Math | 3 | 0.00% | 0.00% | 0.000 |
| Physics | 3 | 0.00% | 0.00% | 0.000 |
| Russian | 3 | 0.00% | 0.00% | 0.000 |

## По сложности

| Difficulty | n | Recall@3 | Recall@5 | MRR |
|------------|---|----------|----------|-----|
| easy | 9 | 0.00% | 0.00% | 0.000 |
| hard | 6 | 0.00% | 0.00% | 0.000 |
| medium | 12 | 0.00% | 0.00% | 0.000 |

## Не найдено (Recall@5 = 0)

- **Что такое переменная?** (expected: Переменные / Math)
- **Как решать линейные уравнения?** (expected: Линейные уравнения / Math)
- **Что такое теорема Пифагора?** (expected: Теорема Пифагора / Math)
- **Что такое существительное?** (expected: Имя существительное / Russian)
- **Как определить спряжение глагола?** (expected: Спряжение глагола / Russian)
- **Что такое причастный оборот?** (expected: Причастный оборот / Russian)
- **What is Past Simple?** (expected: Past Simple / English)
- **How to use articles a/an/the?** (expected: Articles / English)
- **What is Present Perfect?** (expected: Present Perfect / English)
- **Что такое фотосинтез?** (expected: Фотосинтез / Biology)
- **Как устроена клетка?** (expected: Строение клетки / Biology)
- **Что такое ДНК?** (expected: ДНК / Biology)
- **Когда была Куликовская битва?** (expected: Куликовская битва / History)
- **Что такое Реформация?** (expected: Реформация / History)
- **Когда отменили крепостное право?** (expected: Отмена крепостного права / History)
- **Что такое атмосферное давление?** (expected: Атмосферное давление / Geography)
- **Самые большие страны мира?** (expected: Крупнейшие страны / Geography)
- **Что такое течение Гольфстрим?** (expected: Гольфстрим / Geography)
- **Что такое сила тяжести?** (expected: Сила тяжести / Physics)
- **Закон Ньютона?** (expected: Законы Ньютона / Physics)
- **Что такое электрический ток?** (expected: Электрический ток / Physics)
- **Что такое атом?** (expected: Строение атома / Chemistry)
- **Что такое химическая реакция?** (expected: Химические реакции / Chemistry)
- **Периодический закон Менделеева?** (expected: Таблица Менделеева / Chemistry)
- **Что такое переменная в Python?** (expected: Переменные в Python / Informatics)
- **Как работает цикл for?** (expected: Циклы for / Informatics)
- **Что такое алгоритм?** (expected: Алгоритмы / Informatics)

**Итого:** 27/27 = 100.0%

## Рекомендация

❌ **НЕДОСТАТОЧНО.** Hash-based НЕ справляется с retrieval.
**Требуется миграция на real embeddings:**
- OpenAI text-embedding-3-small (API, $0.02/1M tokens)
- Или self-hosted: paraphrase-multilingual-MiniLM-L12-v2 (~200MB RAM)

*MRR 0.000 — Mean Reciprocal Rank (1.0 = perfect, 0.0 = no relevant in top-k).*
