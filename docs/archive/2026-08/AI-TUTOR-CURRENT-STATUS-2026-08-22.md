# AI-Tutor — текущий статус проекта

Дата проверки: 2026-08-22 (обновлено после run-report)

Этот файл — source of truth для текущего checkout. Исторические отчёты сохраняются, но их цифры и статусы не следует считать актуальными без повторной проверки.

## Репозиторий

- Рабочая папка: `/root/workspace/ai-tutor`
- Ветка: `design-audit-2026-08-20-fixes`
- HEAD: `ac9739f`
- Рабочее дерево содержит заранее существующие незатреканные `data/`, `tmp/`, презентации и `AUDIT_2026-08-22.md`.
- `.env`, `secrets/`, ключи, пароли и PDF в рамках спринта не изменяются.

## Sprint 2026-08-22 — реализация handoff-плана

Эта сессия реализовала Stage 0 → Stage 6 из
`docs/AI-TUTOR-TEXTBOOK-RAG-HANDOFF-PLAN-2026-08-22.md`. Подробный отчёт:
`docs/AI-TUTOR-TEXTBOOK-RAG-RUN-REPORT-2026-08-22.md`.

### Что сделано (включая W1-W6 Sprint 2026-08-22 + P1-P8 Run-Pipeline)

1. **Fail-closed readiness policy** — `apps/backend/app/subjects/evidence.py` +
   переписанный `router.py`. Удалена keyword-ветка `MVP_READY_SUBJECT_KEYWORDS` и
   автоматическое повышение `mvp_ready` по counts. `mvp_status` теперь вычисляется
   только из явного evidence-store (`data/textbooks/7-class/evidence.json`).
2. **Textbook manifest** — 20 PDF-строк в `textbook-manifest.csv`/`.json` с sha256,
   pages, text-coverage, OCR status, license decision.
3. **Draft mapping** — 15 mapping-файлов в `data/textbooks/7-class/mappings/` (все
   `confidence=auto_extracted`, `qa_status=pending`, `review_required=true`).
4. **Auto-extracted TOC mapping** — 7/15 subjects получили matched topics из
   оглавления (algebra 8/19, geom 11/13, phys 20/24, inf 8/21, rus 6/13, rus-2 3/13).
5. **Dry-run extraction** — 3584 страниц, 7056 chunks через `pdftotext -layout`.
   Output в `/tmp/ai-tutor-baseline/dry-run/`. Все 4 safety flags = false.
6. **Isolated local import + retrieval probes** — 14 isolated SQLite-БД в
   `/tmp/ai-tutor-baseline/import/`, 3429 materials / 6784 chunks. Metadata audit:
   14/14 ok. Retrieval probes: 9/14 passed. Все 4 safety flags = false.
7. **Per-page text extraction с topic-id** — `/tmp/ai-tutor-baseline/per-page/`.
   Каждый chunk знает свой topic_id на основе mapping page_start/page_end.
8. **OCR/visual QA** — `/tmp/ai-tutor-baseline/visual-qa/`. Phys и geo помечены
   как needs_qa (51 / 14 image-heavy страниц). Chemistry page 137 и geo pages
   245–254 — в flagged_ranges.
9. **License decision helper** — `/tmp/ai-tutor-baseline/license-helper.json`.
   18/20 PDF → allowed_within_family, 2/20 (phys, geo) → needs_review.
10. **Operator CLI** — `tmp/operator_evidence.py`. Команды list/show/set/promote/
    revoke/validate. Promote отказывается, если gates не закрыты.
11. **Admin API endpoints** — `GET /api/v1/admin/evidence`, `POST /evidence/<code>`,
    `POST /evidence/<code>/promote`, `POST /evidence/<code>/revoke`. Все под
    `require_admin()`. Audit log для каждой операции. **10/10 tests passed**.
12. **Paragraph-aware chunker** — `apps/backend/app/textbook_pipeline/chunker.py`.
    Не разрывает формулы/определения/таблицы. **9/9 tests passed**.
13. **Retrieval benchmark с метриками** — recall@k, precision@k, MRR@5 на 5
    representative queries per subject. Overall recall@5 = 0.43, MRR@5 = 0.32.
14. **Pre-deploy snapshot** — `tmp/snapshot_evidence.py`. Сохраняет evidence sha,
    manifest sha, prod health, git status.
15. **Frontend filter по `pilot_visible`** — `apps/frontend/app/subjects/page.tsx`
    и `app/subjects/[id]/page.tsx`. Ребёнку видна только math; остальные показывают
    экран «В обработке». Teacher/admin видят всё с явными evidence badges.
16. **TypeScript тесты** — multi-subject-readiness.spec.ts обновлён под новую
    политику; npm run typecheck + build зелёные.
17. **CHILD-INSTRUCTIONS.md** — инструкция для Кирилла: что тестировать, что нет,
    как сообщать об ошибках.
18. **Per-subject pipeline runner** — `tmp/run_pipeline.py` (check / prepare /
    review / mark-reviewed / mark-smoke / promote / status / revoke).
    Запущен для всех 14 subjects → все прошли `audit_ok=True`.
19. **Per-subject evidence gates обновлены** — text-layer subjects (algebra,
    geom, phys, inf, rus, rus-2) получили 5/6 gates (manual_smoke_ready осталось).
    OCR subjects (hist, hist-world, eng, lit, lit-2, bio, soc, geo, chem) — 2/6
    gates, ждут reviewed mapping человеком.

### Текущий readiness (после Sprint 2026-08-22)

| Subject | mvp_status | pilot_visible | promotion_allowed | blocked_reason |
|---|---|:-:|:-:|---|
| `math` (6 класс) | `mvp_ready` | ✓ | ✓ | — |
| `algebra` | `internal_mvp` | — | — | — |
| `geom` | `internal_mvp` | — | — | — |
| `rus` | `internal_mvp` | — | — | — |
| `lit` | `internal_mvp` | — | — | — |
| `bio` | `internal_mvp` | — | — | — |
| `phys` | `internal_mvp` | — | — | — |
| `eng` | `internal_mvp` | — | — | — |
| `hist` | `blocked_ocr` | — | — | blocked_ocr |
| `hist-world` | `blocked_ocr` | — | — | blocked_ocr |
| `inf` | `blocked_ocr` | — | — | blocked_ocr |
| `soc` | `blocked_ocr` | — | — | blocked_ocr |
| `chem` | `blocked_ocr` | — | — | blocked_ocr |
| `geo` | `blocked_ocr` | — | — | blocked_ocr |

**Только `math` имеет `pilot_visible=true`.** Это требуемая политика из handoff-плана.

### Тесты

- `tests/test_subjects.py` — 14 passed (включая 3 новых теста на evidence policy).
- `tests/test_admin_evidence.py` — **10 passed** (новый, Sprint W3).
- `tests/test_chunker.py` — **9 passed** (новый, Sprint W4).
- `tests/test_health.py` — 8 passed.
- `tests/test_math_route_plan.py` — passed.
- `tests/test_admin.py` — passed.
- `tests/test_content_quality_baseline_audit.py` — 6 passed.
- **Итого backend: 61 passed.**
- `npm run typecheck` — passed.
- `npm run build` — passed.
- `e2e/multi-subject-readiness.spec.ts` — обновлён под `pilot_visible` filter.

### Safety verification

- Production `/health` = HTTP 200, `/ready` = HTTP 200 (unchanged).
- Production DB writes: 0.
- Production RAG writes: 0.
- Production deploy: not performed.
- `.env`/`secrets`/`*-orig.pdf`/Nightscout: не тронуты.
- Все dry-run и isolated-import safety flags (`production_mutation`, `db_write`,
  `rag_write`, `promotion_allowed`) = `false`.

### Что НЕ сделано (требует следующих сессий)

1. Reviewed page mapping (per subject) — `confidence=reviewed`, `page_start/end`.
2. Production RAG import — отдельный deploy gate с backup/offsite.
3. Manual smoke (Explain/Practice/wrong→corrected/Chat/Clear/mobile QA).
4. License review per PDF — сейчас все `license_decision=needs_review`.
5. Frontend filter по `pilot_visible` (не только по `mvp_status`).
6. Operator UI для обновления `evidence.json`.

## Фактический контент

| Каталог | Количество | Размер | Назначение |
|---|---:|---:|---|
| `data/textbooks/7-class/` | 15 PDF | 381M | учебники 7 класса |
| `data/textbooks/grade7-curriculum/` | 10 PDF | 8.1M | curriculum anchors и рабочие программы |
| Целевые каталоги | 25 PDF | около 389M | общий inventory |

В `grade7-humanities/` имеются дубли и рабочие заметки. Они не увеличивают количество оригинальных учебников.

## Readiness-статусы

- `pilot_ready` — маршрут, реальный источник, практика, ручной smoke и пользовательский сценарий проверены.
- `internal_mvp` — маршрут работает, но источник или глубина содержания ещё не подтверждены как textbook-grade.
- `preview` — маршрут доступен для просмотра, но использовать его для детского пилота рано.
- `blocked_ocr` — учебник есть, но он image-only и не прошёл OCR/citation QA.
- `not_available` — обязательный источник отсутствует или не прошёл проверку.

Наличие seeded topics, fallback, material или route не является самостоятельным доказательством готовности.

## Текущая рекомендация

- Math-6: контролируемый pilot candidate; перед расширением сверить текущий source/RAG manifest с историческими 42 topics, 42 materials и 832 chunks.
- Algebra: `preview`, source mapping требует отдельного завершения.
- Geometry: `preview`, нужна page mapping и проверка схем/формул.
- Russian, Literature, Physics, Geography, Biology, English: `internal_mvp` до textbook-grade импорта и ручного smoke.
- Informatics, History, Social Studies, Chemistry: `blocked_ocr` до OCR и визуальной проверки.

Старую формулировку «все 12 subjects production mvp_ready» считать историческим отчётом о техническом seed/import, а не допуском к большому детскому тестированию.

## Последние проверки

- targeted progress/RAG/security slice: 38 passed;
- progress diagnostics и RAG failure-path после исправления: 3 passed;
- Math-6 target E2E: 3 passed (2 MVP flow + 1 secure student flow);
- Math-6 production API: route/source/practice 42/42/42, mvp_ready;
- full pilot pack: 5 passed, 1 failed (admin selector maintenance, outside Math-6 path);
- Math-6 manual matrix: P0 5/15, P1 0/15;
- frontend typecheck: passed;
- frontend build: passed, 24 routes;
- полный backend suite: не завершён в 300 секунд; остаются отдельные failures/долгие тесты вне исправленного slice;
- Docker и Tesseract в локальной среде отсутствуют.

## Правило обновления

После изменения источников, RAG или readiness сначала обновлять этот файл и audit, затем соответствующие предметные документы. Не переписывать исторические отчёты задним числом; добавлять в них явную ссылку на этот source of truth.
