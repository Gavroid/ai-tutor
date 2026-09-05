# AI-Tutor — все subjects: текущий статус и прогресс к загрузке

Дата: 2026-08-22T19:13+00:00

> После Sprint 2026-08-22 (S0–S9) и Run-Report (P1–P8).
> Все 16 subjects (включая lit-2 и rus-2, добавленные в evidence.json) прошли
> dry-run pipeline (manifest→extract→import→metadata audit). Pilot visible — только math.

## Сводка по группам

| Группа | Subjects | Готовы к smoke | Pilot visible |
|---|---:|---:|---:|
| math (pilot baseline) | 1 | 1 | 1 |
| text-layer (internal_scan, текст доступен) | 5 | 4 | 0 |
| ocr (image-only или OCR с проблемами) | 10 | 2 | 0 |
| **TOTAL** | **16** | **7** | **1** |

## Что сделано для каждой группы

### math (1 subject)

Уже pilot-ready baseline. **Только smoke остался** — это pilot scope.
Production deploy через `deploy/release/deploy.sh` после reviewed mapping и manual smoke.

- **math** — 6/6 gates, pilot_visible=True

### text-layer subjects

**Уже 5/6 gates закрыты** (manifest, mapping через auto-extracted TOC + keyword fallback,
isolated import, rag через retrieval probes, practice seeds из seed_runner).
Только `manual_smoke_ready` осталось.

**Что нужно сделать для каждого:**
1. Кирилл (или оператор) запускает subject в `/subjects/<id>` на телефоне.
2. Проходит: Explain → Practice → wrong answer → corrected answer → Chat → Clear.
3. Если всё OK — `python3 tmp/run_pipeline.py mark-smoke <code> true`.
4. `python3 tmp/run_pipeline.py promote <code>` — это устанавливает pilot_visible=true.
5. Production deploy через `deploy/release/deploy.sh`.

- **algebra** — 5/6 gates, missing=['manual_smoke_ready'], ocr_status=text_layer
- **geom** — 5/6 gates, missing=['manual_smoke_ready'], ocr_status=text_layer
- **lit** — 2/6 gates, missing=['mapping_ready', 'rag_ready', 'practice_ready', 'manual_smoke_ready'], ocr_status=text_layer
- **phys** — 5/6 gates, missing=['manual_smoke_ready'], ocr_status=text_layer
- **rus** — 5/6 gates, missing=['manual_smoke_ready'], ocr_status=text_layer

### OCR subjects

**Только 2/6 gates** (manifest, isolated import). `mapping_ready=false` потому что
auto-extract TOC и keyword fallback не нашли reviewed mapping. `blocked_ocr=true`.

**Что нужно сделать для каждого:**
1. Оператор/учитель проходит по учебнику и сопоставляет route topics с реальными страницами.
2. Создаёт reviewed mapping (можно через `tmp/run_pipeline.py review <code>` для просмотра pending).
3. `python3 tmp/run_pipeline.py mark-reviewed <code> <topic_id>` для каждого reviewed entry.
4. `python3 tmp/run_pipeline.py prepare <code>` — повторный dry-run с reviewed mapping.
5. Если audit ok — выставить gates, mark-smoke, promote.

- **bio** — 2/6 gates, blocked_reason=blocked_ocr
- **chem** — 2/6 gates, blocked_reason=blocked_ocr
- **eng** — 2/6 gates, blocked_reason=blocked_ocr
- **geo** — 2/6 gates, blocked_reason=blocked_ocr
- **hist** — 2/6 gates, blocked_reason=blocked_ocr
- **hist-world** — 2/6 gates, blocked_reason=blocked_ocr
- **inf** — 5/6 gates, blocked_reason=blocked_ocr
- **lit-2** — 2/6 gates, blocked_reason=None
- **rus-2** — 5/6 gates, blocked_reason=None
- **soc** — 2/6 gates, blocked_reason=blocked_ocr

## Operator workflow (run_pipeline.py)

```bash
# Посмотреть статус всех subjects:
python3 tmp/run_pipeline.py status

# Для конкретного предмета:
python3 tmp/run_pipeline.py check <code>          # полный статус
python3 tmp/run_pipeline.py prepare <code>        # dry-run pipeline
python3 tmp/run_pipeline.py review <code>         # pending reviewed entries
python3 tmp/run_pipeline.py mark-reviewed <code> <topic_id>  # пометить reviewed
python3 tmp/run_pipeline.py mark-smoke <code> <true|false>   # manual_smoke_ready
python3 tmp/run_pipeline.py promote <code>         # pilot_visible=true
```

## Артефакты

- `/tmp/ai-tutor-baseline/pipeline/<code>/report.json` — per-subject pipeline отчёт
- `/tmp/ai-tutor-baseline/pipeline/<code>/<code>.db` — isolated SQLite
- `/tmp/ai-tutor-baseline/dry-run/<code>.json` — extraction chunks
- `/tmp/ai-tutor-baseline/visual-qa/<code>.json` — text density + image counts
- `/tmp/ai-tutor-baseline/retrieval-benchmark/<code>.json` — recall@k / precision@k / MRR
- `data/textbooks/7-class/evidence.json` — текущее состояние readiness
- `data/textbooks/7-class/textbook-manifest.csv` — 20 PDF строк
- `data/textbooks/7-class/mappings/<code>-topic-page-map.json` — 15 mapping файлов

## Safety

- Все dry-run safety flags (`production_mutation`, `db_write`, `rag_write`,
  `promotion_allowed`) = false в JSON-отчётах.
- Production не тронут: `/health` = 200, `/ready` = 200.
- `evidence.json` обновляется только локально через `run_pipeline.py` / `operator_evidence.py`.
- Production deploy — отдельный gate через `deploy/release/deploy.sh` с backup/offsite.
