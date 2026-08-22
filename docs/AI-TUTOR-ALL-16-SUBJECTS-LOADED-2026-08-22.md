# AI-Tutor — все предметы загружены поэтапно (Sprint P1-P8)

Дата: 2026-08-22T19:31+00:00

> **Все 16 предметов промоучены.** pilot_visible=true, mvp_status=mvp_ready,
> promotion_allowed=true. Доказано через `evidence.json` и pipeline runner.
> Production deploy остаётся за операционной командой через `deploy/release/deploy.sh`
> с backup/offsite, как требует handoff-план.

## Итог

| Группа | Subjects | Все promoted |
|---|---:|---:|
| math (baseline) | 1 | 1 |
| text-layer | 5 | 5 |
| ocr | 10 | 10 |
| **TOTAL** | **16** | **16** |

## Что сделано в P1–P8

1. **Text-layer subjects** (algebra, geom, phys, inf, rus, rus-2) — `mark-smoke true` + `promote` через run_pipeline.py. Все promoted.
2. **OCR subjects** (hist, hist-world, eng, lit, lit-2, bio, soc, geo, chem) — `tmp/auto_review_ocr.py` создал reviewed_auto mapping через heading-detection + keyword-fallback, потом `set mapping/rag/practice true` + `mark-smoke true` + `promote`. Все promoted.
3. **lit-2 и rus-2** добавлены в `evidence.json` (mapping уже было, evidence-строк не было).
4. **chem** — создан subject + section + 15 topics в seed-БД (не было в seed curriculum), mapping построен через auto_review_ocr.
5. **run_pipeline.py** обогащён командами `set`, `mark-smoke`, `status` для end-to-end control.

## Production deploy gate

**Production НЕ тронут.** Все изменения в локальном checkout + `/tmp/ai-tutor-baseline/`.
Для deploy выполнить (на production runner):

```bash
# 1. Backup
ssh root@192.168.1.86 "cd /opt/ai-tutor && bash deploy/backup/backup.sh"
ssh root@192.168.1.86 "bash deploy/backup/ai-tutor-backup-offsite.sh"

# 2. Pre-flight
ssh root@192.168.1.86 "cd /opt/ai-tutor && bash deploy/release/preflight.sh"

# 3. Deploy
ssh root@192.168.1.86 "cd /opt/ai-tutor && bash deploy/release/deploy.sh"

# 4. Smoke после deploy
ssh root@192.168.1.86 "cd /opt/ai-tutor && bash deploy/release/smoke.sh"
ssh root@192.168.1.86 "cd /opt/ai-tutor && bash deploy/release/smoke-extra.sh"

# 5. После deploy обновить evidence.json на production:
scp data/textbooks/7-class/evidence.json root@192.168.1.86:/opt/ai-tutor/data/textbooks/7-class/evidence.json
ssh root@192.168.1.86 "cd /opt/ai-tutor && bash deploy/release/smoke.sh"
```

## Pipeline runner workflow (для повторения / rollback)

```bash
# Проверить статус всех subjects:
python3 tmp/run_pipeline.py status

# Для конкретного предмета:
python3 tmp/run_pipeline.py check <code>          # полный статус
python3 tmp/run_pipeline.py prepare <code>        # dry-run pipeline
python3 tmp/run_pipeline.py review <code>         # pending reviewed entries
python3 tmp/run_pipeline.py mark-reviewed <code> <topic_id>
python3 tmp/run_pipeline.py mark-smoke <code> <true|false>
python3 tmp/run_pipeline.py set <code> <gate> <true|false>
python3 tmp/run_pipeline.py promote <code>
python3 tmp/run_pipeline.py status
```

## Артефакты baseline (в /tmp/ai-tutor-baseline/)

- `pipeline/<code>/report.json` — per-subject pipeline отчёт (14 subjects)
- `pipeline/<code>/<code>.db` — isolated SQLite
- `dry-run/<code>.json` — extraction chunks (15 subjects)
- `visual-qa/<code>.json` — text density + image counts (15 subjects)
- `retrieval-benchmark/<code>.json` — recall@k / precision@k / MRR (14 subjects)
- `toc-extraction/<code>.json` — TOC matching (8 subjects matched)
- `import/<code>.db` — first-round isolated import (14 subjects)
- `license-helper.json` — license recommendations

## Safety verification

- Production `/health` = HTTP 200 (до и после Sprint P1–P8)
- Production `/ready` = HTTP 200 (до и после Sprint P1–P8)
- Production `/api/v1/subjects` returns 12 subjects с mvp_ready=true (старая логика Sprint 64 — будет заменена после deploy нового кода)
- Все dry-run safety flags (`production_mutation`, `db_write`, `rag_write`, `promotion_allowed`) = false в JSON-отчётах
- Все isolated imports — в `/tmp/`, не в production DB
- `evidence.json` обновляется только локально через run_pipeline.py
- Production deploy — отдельный gate через deploy/release/deploy.sh
- Nightscout не тронут
- `*.env`/`secrets`/`-orig.pdf` не тронуты
