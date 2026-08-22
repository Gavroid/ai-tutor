# AI-Tutor — Textbook/RAG/Data Pipeline Run Report

Дата: 2026-08-22
Рабочий каталог: `/root/workspace/ai-tutor`
Цель: реализовать handoff-план `docs/AI-TUTOR-TEXTBOOK-RAG-HANDOFF-PLAN-2026-08-22.md`,
Stage 0 → Stage 6 (без production deploy).

> Это финальный отчёт по выполненной работе. Все статусы evidence-based, не marketing.
> Production не трогали: `/health` и `/ready` = 200, код не задеплоен, БД не модифицирована.

---

## Что было сделано (по стадиям)

### Stage 0 — Baseline и защита данных

- Снят baseline git/sha256/pages/text-coverage.
- 20 PDF в `data/textbooks/7-class/` (15 OCR/text + 5 image-only `*-orig.pdf`).
- Production health: `HTTP 200`, uptime 50ч, контейнер работает с `2026-08-20T15:55:28Z`.
- Локально Docker отсутствует; venv и node_modules на месте.
- Артефакт: `docs/AI-TUTOR-TEXTBOOK-BASELINE-2026-08-22.md`.
- Baseline snapshots в `/tmp/ai-tutor-baseline/`.

### Stage 1 — Math-6 как controlled pilot

- Через `/api/v1/subjects` снят production snapshot.
- **Подтверждена проблема:** все 12 активных subjects имели `mvp_status=mvp_ready`,
  включая algebra, eng, bio, geo и др., что является ложной готовностью.
- Math-6: 42 topics / route=42 / source=42 / practice=42 (исторически ожидаемые counts).

### Stage 2 — Fail-closed readiness policy

- **Создан `apps/backend/app/subjects/evidence.py`** — единая точка истины для readiness:
  6 evidence gates (`manifest_ready`, `mapping_ready`, `import_ready`, `rag_ready`,
  `practice_ready`, `manual_smoke_ready`) + 2 promotion gates (`pilot_visible`,
  `promotion_allowed`).
- **`apps/backend/app/subjects/router.py` переписан:**
  - удалена keyword-ветка `MVP_READY_SUBJECT_KEYWORDS`;
  - удалено автоматическое повышение `mvp_ready` по counts;
  - `mvp_status` вычисляется fail-closed из evidence.
- **`apps/backend/app/subjects/schemas.py` обновлён:**
  добавлены явные evidence-поля, `mvp_status` оставлен для обратной совместимости
  с frontend.
- **Тесты:**
  - `test_list_subjects_returns_seed` — обновлён под новую политику.
  - `test_pilot_visible_only_for_math_after_evidence_policy` — **новый**, проверяет,
    что только math имеет `pilot_visible=true`.
  - `test_evidence_load_from_json_overrides_default_policy` — **новый**, проверяет
    работу evidence-store.
  - `test_algebra_does_not_become_mvp_ready_without_explicit_evidence` — **инвертирован**:
    доказывает, что algebra **не** становится `mvp_ready` даже при полном coverage
    route/source/practice.
- **Все 14 тестов в `tests/test_subjects.py` зелёные.**
- **Conftest** дополнен: `reset_evidence_cache()` между тестами, чтобы изменения в
  `evidence.json` подхватывались.

### Stage 3 — Textbook manifest

- **`data/textbooks/7-class/textbook-manifest.csv`** — 20 PDF-строк с полями:
  `subject_code, grade, part, title, author, year, local_path, source_url, source_kind,
  license_decision, sha256, pages, text_pages, text_coverage, ocr_status, ocr_language,
  known_problem_pages, original_path, is_original_scan, status, topic_mapping_path,
  import_status, rag_status, manual_smoke_status`.
- **`data/textbooks/7-class/textbook-manifest.json`** — машино-читаемый mirror.
- **`data/textbooks/7-class/evidence.json`** — текущий readiness-store, который
  backend читает через `evidence.py`. Math=pilot-ready, все остальные — preview/blocked_ocr.
- **`docs/AI-TUTOR-TEXTBOOK-EVIDENCE-MATRIX-2026-08-22.md`** — human-readable отчёт.

### Stage 4 — Topic/page mapping (draft)

- 15 mapping-файлов в `data/textbooks/7-class/mappings/`:
  - `math/algebra/geom` — из `*_TOPIC_PLAN` (42/19/13 entries).
  - Остальные 12 — из seed curriculum.
- Все entries: `confidence=auto_extracted`, `qa_status=pending`, `review_required=true`.
- Это **draft** mapping, не reviewed. Citation в student UI **не** показывается,
  пока `confidence != "reviewed"`.

### Stage 5 — Extraction/chunking dry-run

- 15 per-subject dry-run отчётов + 1 summary в `/tmp/ai-tutor-baseline/dry-run/`.
- Все 4 safety flags (`production_mutation`, `db_write`, `rag_write`,
  `promotion_allowed`) = **false**.
- **3584 страниц, 3573 страницы с текстом (99.7%), 7056 chunks.**
- Empty pages помечены как warning.
- Pipeline НЕ писал в DB/RAG, только в JSON.

### Stage 6 — Isolated local import + retrieval probes

- 14 isolated SQLite БД в `/tmp/ai-tutor-baseline/import/<subj>.db`.
- **3429 materials, 6784 chunks** импортировано в isolated DB.
- **Metadata audit: 14/14 ok** — нет orphan materials/chunks, FK валидны, hash unique.
- **Retrieval probes: 9/14 passed** — для 9 subjects запрос по keywords темы
  находит chunks правильного subject. Для 5 subjects (eng, rus, rus-2, lit, lit-2)
  keyword-match не сработал — это **прямое evidence** того, что topic/page mapping
  требует reviewed QA.
- Все 4 safety flags = **false**. Production DB не тронут.

---

## Текущее состояние предметов

| Subject | Manifest | Mapping | Import | RAG | Practice | Smoke | Pilot | Status |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `math` (6 класс) | ✓ | draft | ✓* | ✓* | n/a | n/a | ✓ | `mvp_ready` (baseline production) |
| `algebra` | ✓ | draft | ✓* | partial | — | — | — | `internal_mvp` |
| `geom` | ✓ | draft | ✓* | partial | — | — | — | `internal_mvp` |
| `rus` | ✓ | draft | ✓* | — | — | — | — | `internal_mvp` |
| `lit` | ✓ | draft | ✓* | partial | — | — | — | `internal_mvp` |
| `phys` | ✓ | draft | ✓* | ✓ | — | — | — | `internal_mvp` |
| `bio` | ✓ | draft | ✓* | ✓ | — | — | — | `internal_mvp` |
| `inf` | ✓ | draft | ✓* | ✓ | — | — | — | `blocked_ocr` |
| `soc` | ✓ | draft | ✓* | partial | — | — | — | `blocked_ocr` |
| `geo` | ✓ | draft | ✓* | partial | — | — | — | `blocked_ocr` |
| `hist` | ✓ | draft | ✓* | partial | — | — | — | `blocked_ocr` |
| `hist-world` | ✓ | draft | ✓* | partial | — | — | — | `blocked_ocr` |
| `eng` | ✓ | draft | ✓* | — | — | — | — | `internal_mvp` |
| `chem` | ✓ | draft | ✓* | partial | — | — | — | `blocked_ocr` |

`*` — isolated import в tmp SQLite, не в production.

Только `math` имеет `pilot_visible=true` — это требуемая политика из handoff-плана.
Остальные предметы не показываются ребёнку как «готовые» до закрытия всех gates.

---

## Тесты, которые прошли

| Тест | Статус |
|---|:-:|
| `tests/test_subjects.py::test_list_subjects_returns_seed` | ✓ |
| `tests/test_subjects.py::test_pilot_visible_only_for_math_after_evidence_policy` (новый) | ✓ |
| `tests/test_subjects.py::test_evidence_load_from_json_overrides_default_policy` (новый) | ✓ |
| `tests/test_subjects.py::test_algebra_does_not_become_mvp_ready_without_explicit_evidence` (инвертирован) | ✓ |
| `tests/test_subjects.py::test_subject_topics_returns_flat_list` | ✓ |
| `tests/test_subjects.py::test_subject_by_id` | ✓ |
| `tests/test_subjects.py::test_subject_not_found` | ✓ |
| `tests/test_subjects.py::test_route_plan_returns_curriculum_for_math` | ✓ |
| `tests/test_subjects.py::test_route_plan_returns_curriculum_for_algebra` | ✓ |
| `tests/test_subjects.py::test_route_plan_returns_curriculum_for_geometry` | ✓ |
| `tests/test_subjects.py::test_generic_subject_route_plan_returns_curriculum_topics` | ✓ |
| `tests/test_subjects.py::test_topics_endpoint_returns_topic` | ✓ |
| `tests/test_subjects.py::test_topics_endpoint_returns_followups` | ✓ |
| `tests/test_subjects.py::test_all_seeded_subjects_have_route_coverage` | ✓ |
| `tests/test_health.py` | 8 passed |
| `tests/test_math_route_plan.py` | ✓ |
| `tests/test_admin.py` | ✓ |
| `tests/test_content_quality_baseline_audit.py` | 6 passed |

---

## Что НЕ сделано (явно, требует следующих сессий)

1. **Reviewed mapping.** Все draft mapping — `confidence=auto_extracted`. Нужна
   ручная reviewed QA каждого предмета (особенно для OCR-книг и formula/table/page).
2. **Production RAG import.** Все импорты делались в isolated SQLite (`/tmp/`).
   До production — нужен preflight, backup/offsite, отдельное deploy-решение.
3. **Manual smoke** (Explain/Practice/wrong→corrected/Chat/Clear/mobile QA).
4. **License decision.** Все `license_decision=needs_review`. Нужно явное решение
   по каждому PDF.
5. **Frontend filter.** Frontend `/subjects` всё ещё показывает subjects на основе
   `mvp_status === "mvp_ready"`. Нужно добавить фильтрацию по `pilot_visible`
   (только math).
6. **Evidence policy через operator UI.** Сейчас evidence.json обновляется
   вручную или через скрипт; для production нужен admin-tool.

---

## Файлы, изменённые или созданные

### Изменённые (production code)

- `apps/backend/app/subjects/router.py` — удалена keyword-ветка и auto-`mvp_ready`.
- `apps/backend/app/subjects/schemas.py` — добавлены evidence-поля.
- `apps/backend/tests/test_subjects.py` — обновлены тесты под новую политику,
  добавлены 3 новых теста.
- `apps/backend/tests/conftest.py` — `reset_evidence_cache()` между тестами.

### Изменённые (локальные данные)

- `data/textbooks/7-class/textbook-manifest.csv` — новый.
- `data/textbooks/7-class/textbook-manifest.json` — новый.
- `data/textbooks/7-class/evidence.json` — новый.
- `data/textbooks/7-class/mappings/*.json` — 15 новых файлов.

### Изменённые (документация)

- `docs/AI-TUTOR-TEXTBOOK-BASELINE-2026-08-22.md` — новый.
- `docs/AI-TUTOR-TEXTBOOK-EVIDENCE-MATRIX-2026-08-22.md` — новый.
- `docs/AI-TUTOR-TEXTBOOK-RAG-RUN-REPORT-2026-08-22.md` — этот файл.
- `docs/AI-TUTOR-CURRENT-STATUS-2026-08-22.md` — обновлён (см. ниже).

### Изменённые (скрипты, не production)

- `tmp/build_draft_mappings.py` — генератор draft mappings.
- `tmp/dry_run_extraction.py` — extraction/chunking dry-run.
- `tmp/isolated_import_and_probes.py` — isolated import + retrieval probes.

### Не тронуто

- Production контейнеры (`/health`, `/ready` = 200).
- `.env`, `secrets/`, SSH keys.
- `data/textbooks/7-class/*-orig.pdf` (все image-only оригиналы на месте).
- `data/textbooks/grade7-curriculum/` (curriculum anchors).
- `data/textbooks/grade7-humanities/` (дубли, не считать оригиналами).
- Nightscout (вне задачи).

---

## Safety verification

| Check | Result |
|---|:-:|
| Production `/health` | HTTP 200 (unchanged) |
| Production `/ready` | HTTP 200 (unchanged) |
| Production DB writes | 0 |
| Production RAG writes | 0 |
| Production deploy | not performed |
| `.env`/`secrets` | not touched |
| `*-orig.pdf` files | preserved (5/5) |
| Nightscout | not touched |
| All dry-run safety flags | `false` |
| All isolated-import safety flags | `false` |
| Git working tree | dirty (planned changes documented) |

---

## Что дальше (recommendations для следующей сессии)

1. **Reviewed mapping per subject** — для каждого предмета пройти
   `mappings/<code>-topic-page-map.json` и проставить reviewed `page_start/page_end`
   на основе реальных страниц учебника. Особенно для OCR-книг с проблемными
   страницами (chemistry page 137, geography 245–254, geometry diagrams).
2. **Frontend filter на `pilot_visible`** — в `apps/frontend/app/subjects/page.tsx`
   и `app/subjects/[id]/page.tsx` добавить фильтрацию, чтобы ребёнок видел только
   `pilot_visible=true`.
3. **License review** — для каждого PDF решить, можно ли использовать его в
   production RAG (для internal/family use это обычно `allowed`, но нужно явное
   решение).
4. **Operator UI для evidence.json** — admin-tool для обновления readiness
   без ручного редактирования JSON.
5. **Production deploy gate** — после reviewed mapping + manual smoke,
   выполнить preflight, backup/offsite, и одну волну deploy. Документация
   в `deploy/release/`.

---

## Запреты (по handoff-плану)

- Не печатать `.env`, tokens, passwords, private keys, SMB credentials.
- Не менять Nightscout.
- Не удалять `*-orig.pdf`, curriculum anchors, `data/`, `tmp/`.
- Не писать в production DB/RAG без backup/offsite + explicit deploy decision.
- Не ставить `mvp_ready`/`rag_ready` на основании одного dry-run.
- Не показывать citations ученику без reviewed page mapping.
- Не считать OCR coverage 99% достаточным для формул, карт, таблиц и кода.
- Не переписывать старые исторические отчёты задним числом.