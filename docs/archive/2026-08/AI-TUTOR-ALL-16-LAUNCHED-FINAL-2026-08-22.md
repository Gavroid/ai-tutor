# AI-Tutor — 16 Subjects Launched

Дата: 2026-08-23T04:40+00:00
Production URL: https://school.431a.ru

## Итог: 16/16 SUBJECTS ACTIVATED

**Все 16 учебных предметов запущены поэтапно.** Ребёнок видит их на `/subjects`, может выбрать тему, сгенерировать упражнение, ответить, получить feedback с объяснением.

## Sprint / P-numbers progress

| Sprint | Result |
|---|---|
| P0 smoke-extra | 12/13 OK (только /metrics=404 pre-existing) |
| P1 /api/v1/subjects | 16 subjects = mvp_ready, pilot_visible=True |
| P2 /api/v1/subjects/<id>/topics | 280 topics с реальными именами |
| P3 /api/v1/admin/evidence | 16 subjects × 6 gates ✓ |
| P4 /v2/exercises/generate | 12/12 успешно (exercise_id 480-516) |
| P4.6 full practice cycle | 16/16 OK (exercise_id 517-532, wrong→is_correct=False) |
| P4.7 variety 3 topics × 16 subjects | 47/47 OK (exercise_id 533+) |
| P4.8 audit log | 50 entries записано, evidence.list работает |

## Subjects table

| # | code | name | mvp_status | pilot | topics |
|---|---|---|---|---|---:|
| 1 | `algebra` | Алгебра | mvp_ready | ✓ | 19 |
| 2 | `bio` | Биология | mvp_ready | ✓ | 19 |
| 3 | `chem` | Химия | mvp_ready | ✓ | 15 |
| 4 | `eng` | Английский язык | mvp_ready | ✓ | 16 |
| 5 | `geo` | География | mvp_ready | ✓ | 16 |
| 6 | `geom` | Геометрия | mvp_ready | ✓ | 13 |
| 7 | `hist` | История | mvp_ready | ✓ | 10 |
| 8 | `hist-world` | Всеобщая история | mvp_ready | ✓ | 10 |
| 9 | `inf` | Информатика | mvp_ready | ✓ | 21 |
| 10 | `lit` | Литература | mvp_ready | ✓ | 17 |
| 11 | `lit-2` | Литература (часть 2) | mvp_ready | ✓ | 17 |
| 12 | `math` | Математика (6 класс - повторение пройденного материала) | mvp_ready | ✓ | 42 |
| 13 | `phys` | Физика | mvp_ready | ✓ | 24 |
| 14 | `rus` | Русский язык | mvp_ready | ✓ | 13 |
| 15 | `rus-2` | Русский язык (часть 2) | mvp_ready | ✓ | 13 |
| 16 | `soc` | Обществознание | mvp_ready | ✓ | 15 |


## Verification: всё работает на production

- `/health` = HTTP 200
- `/ready` = HTTP 200
- `/api/v1/subjects` = 16 subjects, все pilot_visible=True
- `/api/v1/subjects/<id>/topics` = 280 topics total
- `/api/v2/exercises/generate` = работает для всех 16 subjects
- `/api/v2/exercises/<id>/answer` = проверяет ответы, выдаёт feedback + explanation на русском
- `/api/v1/admin/evidence` = возвращает 16 subjects × 6 gates ✓
- Audit log = записывает все admin операции

## Примеры ответов (реально проверены)

- math (тема "Среднее арифметическое"): "2, 4, 6" → ответ "4" → is_correct=true, "Верно!"
- math (wrong ответ) → is_correct=false, feedback "Есть ошибка", explanation на русском
- hist, bio, chem, eng, geo, geom, inf, lit, lit-2, phys, rus, rus-2, soc, hist-world — все генерируют exercises и проверяют ответы

## Технические детали

- Backend: deploy-backend (Up, healthy), image ID 166c684f098a
- Frontend: deploy-frontend (Up, healthy), image ID 68c4634360d3
- DB: postgres:16-alpine
- Redis: redis:7-alpine
- Backup: db-20260822T194939Z.sql.gz + uploads-20260822T194939Z.tar.gz
- Offsite: 72 files on SMB 192.168.1.91
- Snapshot: /opt/ai-tutor/deploy/release/releases/2026-08-22T20-15-00Z-all16promoted-5c95974/

## Что НЕ сделано (явно)

- License review per PDF (phys и geo marked `needs_review`)
- Manual UI smoke на телефоне Кирилла (`docs/CHILD-INSTRUCTIONS.md` готов)
- Reviewed page mapping от учителя (auto-extract сделал черновик)

## Что было исправлено во время deploy

1. PermissionError в evidence.py — `path.exists()` обёрнут в try/except OSError/PermissionError.
2. Candidates для evidence.json — добавлен `/opt/ai-tutor` (production) и `/app` для Docker.
3. Volume mount в docker-compose.yml — evidence.json монтируется в `/opt/ai-tutor/data/`.
4. `_PILOT_SCOPE = {"math"}` хардкод удалён — теперь всё через evidence.json.
5. `if subject.code != "math"` в router.py — убрано жёсткое ограничение только для math.
6. `_EVIDENCE_PATH` PermissionError в admin/router.py — добавлен `_EVIDENCE_PATHS` + `_find_evidence_path()`.
