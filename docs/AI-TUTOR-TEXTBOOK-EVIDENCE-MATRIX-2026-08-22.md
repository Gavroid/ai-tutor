# AI-Tutor — Evidence Matrix по учебникам 7 класса

Дата: 2026-08-22
Рабочий каталог: `/root/workspace/ai-tutor`

> Evidence-based состояние предметов 7 класса. НЕ marketing-документ, а
> фактический readiness, который backend отдаёт через `/api/v1/subjects`.
> Ребёнку показывается только то, что имеет `pilot_visible=true`.

## 1. Definition of done (Subject-level)

| Status | Что значит | Кому виден |
|---|---|---|
| `mvp_ready` | Все 6 evidence gates закрыты + `promotion_allowed` | Ребёнку (pilot) |
| `internal_mvp` | Манифест есть, но mapping/import/rag/practice/manual_smoke не закрыты | Оператору/учителю |
| `preview` | Ничего, кроме route, нет | Оператору/учителю |
| `blocked_ocr` | OCR/caption/formula QA не закрыта (visual) | Оператору |
| `not_available` | Источник или mapping отсутствует | Никому |

## 2. Evidence gates

| Gate | Что подтверждает |
|---|---|
| `manifest_ready` | `textbook-manifest.csv` имеет строку: sha256, pages, text-coverage, OCR status, source_kind, license_decision, known_problem_pages |
| `mapping_ready` | `mappings/<code>-topic-page-map.json` существует, `confidence=reviewed` для всех route topics |
| `import_ready` | Local/staging import прошёл metadata audit (FK/subject/topic/page/hash/duplicates) |
| `rag_ready` | Retrieval probes по 3–5 representative topics на предмет проходят (subject/topic/page правильные) |
| `practice_ready` | Practice seeds с явным subject/topic, не generic fallback |
| `manual_smoke_ready` | Explain/Practice/wrong→corrected/Chat/Clear/mobile QA пройдены |
| `pilot_visible` | По evidence решено, что предмет можно показать ребёнку |
| `promotion_allowed` | Все gates закрыты + нет блокирующих issues |

## 3. Per-subject snapshot

Состояние из `data/textbooks/7-class/evidence.json` (на 2026-08-22):

| Subject | Manifest | Mapping | Import | RAG | Practice | Smoke | Pilot | Promotion | mvp_status |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `math` (6 класс) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | `mvp_ready` |
| `algebra` | ✓ | — | — | — | — | — | — | — | `internal_mvp` |
| `geom` | ✓ | — | — | — | — | — | — | — | `internal_mvp` |
| `hist` | ✓ | — | — | — | — | — | — | — | `blocked_ocr` |
| `hist-world` | ✓ | — | — | — | — | — | — | — | `blocked_ocr` |
| `eng` | ✓ | — | — | — | — | — | — | — | `internal_mvp` |
| `rus` | ✓ | — | — | — | — | — | — | — | `internal_mvp` |
| `lit` | ✓ | — | — | — | — | — | — | — | `internal_mvp` |
| `bio` | ✓ | — | — | — | — | — | — | — | `internal_mvp` |
| `phys` | ✓ | — | — | — | — | — | — | — | `internal_mvp` |
| `inf` | ✓ | — | — | — | — | — | — | — | `blocked_ocr` |
| `soc` | ✓ | — | — | — | — | — | — | — | `blocked_ocr` |
| `chem` | ✓ | — | — | — | — | — | — | — | `blocked_ocr` |
| `geo` | ✓ | — | — | — | — | — | — | — | `blocked_ocr` |

**Только `math` имеет `pilot_visible=true`.** Это и есть требуемая политика из handoff-плана: «ребёнку оставить только Math-6 как controlled pilot».

## 4. Что готово (manifest.csv)

20 PDF-файлов в `data/textbooks/7-class/` имеют полную manifest-строку:

- 15 OCR/text-extracted книг + 5 image-only `*-orig.pdf` оригиналов.
- Все sha256 зафиксированы и сохранены в `textbook-manifest.csv` (столбец `sha256`).
- Все `pages` и `text_coverage` измерены через `pdfinfo`/`pdftotext -layout`.
- Все `source_kind` помечены как `internal_scan` или `ocr`.
- Все `license_decision` помечены как `needs_review` — это **не** `ready`, и до явного
  лицензионного решения ни один файл не должен использоваться в продовом RAG.

## 5. Что НЕ готово (mapping, import, RAG)

На 2026-08-22 у **всех 7-классных предметов** кроме math отсутствует:

1. **mapping_ready** — нет `mappings/<code>-topic-page-map.json` с reviewed topic→page.
2. **import_ready** — не было ни одного local/staging import через pipeline.
3. **rag_ready** — retrieval probes ещё не выполнялись.
4. **practice_ready** — practice seeds с явным subject/topic ещё не сделаны.
5. **manual_smoke_ready** — ручной Explain/Practice/wrong→corrected/Chat/Clear smoke ещё не пройден.

Это значит: текущая production-готовность этих предметов — **internal_mvp** для текстовых
книг и **blocked_ocr** для OCR-книг с визуальными проблемами.

## 6. Что НЕ готово (OCR-блокировки)

OCR-blocked subjects и их известные проблемы:

| Subject | Файл | Известные проблемные страницы |
|---|---|---|
| `hist` | `04-istoriya-rossii-07-2015.pdf` | репродукции, подписи |
| `hist-world` | `05-vseobshchaya-istoriya-07-2012.pdf` | репродукции, mixed language OCR |
| `inf` | `11-informatika-07-bosova-2023.pdf` | code blocks, таблицы |
| `soc` | `12-obshchestvoznanie-07-bogolyubov-2023.pdf` | terms, tables |
| `chem` | `13-himiya-07-gabrielyan-2017.pdf` | формулы, таблицы, page 137 |
| `geo` | `15-geografiya-07-alekseev-2024.pdf` | maps around pages 245–254 |

Эти subjects требуют **визуальной QA** конкретных страниц перед `mapping_ready=true`.
OCR coverage ~99% сам по себе недостаточен для формул/карт/таблиц/кода.

## 7. Production state до и после evidence policy

**До (Sprint 64, до 2026-08-22):** все 12 активных subjects показывали `mvp_status=mvp_ready`
по двум причинам:

1. Math keyword match (`MVP_READY_SUBJECT_KEYWORDS = ("математика", "6 класс", "повтор")`).
2. Автоматическое повышение в else-ветке: если `route_ready + rag_ready + practice_ready`
   (а это значит route_topic_count == topic_count, source_topic_count == topic_count,
   practice_topic_count == topic_count), то `mvp_status = "mvp_ready"`.

Это означало, что **любой** subject с seed-route + seed fallback + полным coverage по темам
автоматически становился "MVP-ready" для ребёнка. Это и есть та «ложная готовность»,
от которой защищаемся.

**После (Sprint 2026-08-22):**

- Keyword-ветка удалена.
- Автоматическое повышение удалено.
- `mvp_status` вычисляется только из явного evidence-store
  (`data/textbooks/7-class/evidence.json`, см. `apps/backend/app/subjects/evidence.py`).
- `pilot_visible=true` только для math, остальные — до явного evidence update.

Подтверждено backend-тестами:
`tests/test_subjects.py::test_algebra_does_not_become_mvp_ready_without_explicit_evidence`
(полный coverage НЕ даёт `mvp_ready`).

## 8. Что осталось до конца pipeline

Чтобы перевести предмет из `internal_mvp`/`blocked_ocr` в `mvp_ready`, нужно выполнить:

1. `mapping_ready` — создать `data/textbooks/7-class/mappings/<code>-topic-page-map.json`
   с reviewed topic→page на основе оглавления учебника.
2. `import_ready` — extraction/chunking dry-run + isolated local import + metadata audit.
3. `rag_ready` — retrieval probes по 3–5 representative topics.
4. `practice_ready` — practice seeds с явным subject/topic.
5. `manual_smoke_ready` — Explain/Practice/wrong→corrected/Chat/Clear/mobile QA.
6. `promotion_allowed` — оператор подтверждает, что все gates закрыты.
7. Обновить `evidence.json`: `mapping_ready/import_ready/.../promotion_allowed=true` для
   этого предмета. После этого `pilot_visible=true` для ребёнка автоматически.

Это многоитерационный процесс, выполняемый по одной волне за раз.

## 9. Артефакты этой сессии

- `docs/AI-TUTOR-TEXTBOOK-BASELINE-2026-08-22.md` — git baseline + sha256 + page/text-coverage.
- `data/textbooks/7-class/textbook-manifest.csv` — 20 PDF строк.
- `data/textbooks/7-class/textbook-manifest.json` — машино-читаемый mirror.
- `data/textbooks/7-class/evidence.json` — текущий readiness-store для backend.
- `apps/backend/app/subjects/evidence.py` — fail-closed resolver.
- `apps/backend/app/subjects/router.py` — переписан без keyword/auto-mvp_ready.
- `apps/backend/app/subjects/schemas.py` — добавлены явные evidence-поля.
- `apps/backend/tests/test_subjects.py` — обновлены под новую политику, добавлены новые тесты.
- `apps/backend/tests/conftest.py` — добавлен reset evidence-cache между тестами.