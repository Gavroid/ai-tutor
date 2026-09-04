# CHANGELOG Sprint 3.20+ — сессия 2026-09-04 (P0 infrastructure + quality gates)

**Контекст:** План качества P0–P2 (`/root/workspace/audit-2026-09/13-project-quality-assessment-2026-09-03.md`) реализован полностью в части P0. Параллельно починены побочные баги.

| Sprint | Коммит | Описание | Deploy на проде |
|---|---|---|---|
| 3.20 | `df6bfe1` | **Git filter-repo**: pack 1.08 GiB → 13.43 MiB (×80); push ~8 сек; .gitignore + data/ untracked но на диске | (не нужен — git-only) |
| 1.4 | `319e207` | **Миграция 0026_parent_link_no_self**: CHECK `(parent_id <> student_id) OR (status = 'pending')` — запрет self-link для active. TDD RED→GREEN (4 новых + 2 обновлённых). | `20260904T100403Z-319e207` |
| 3.21 | `113bbeb` | **Telegram bot supervisor fix**: точное match cmdline `"python3 -m app.bot.telegram_bot "` → exit 0 при живом боте (был спам-старт) | `20260904T102318Z-113bbeb` |
| 3.21b | `a50ca73` | Уточнён match (предотвращает supervisor self-kill когда bash-c '...' сам содержит pattern) | (host-only update) |
| 3.21 | `113bbeb` | **smoke.sh env fallback**: 3-уровневая проверка env → /opt/ai-tutor/.env → ssh fetch → fail-fast (вместо silent default `strongpass1`) | то же |
| 3.22 | `369422b` | **pyproject.toml + ruff baseline**: rules E/F/W/I/UP/B, ignore-list с обоснованиями. Bug-fix F821 Undefined `UserCreate` в oauth.py | (не нужен — конфиг) |
| 3.23 | `84729c2` | **Telegram B1 bind fix**: 7 новых тестов + 2 обновлённых + 1 фиксированный. cmd_start → validate_and_bind (прямой DB). Новый endpoint `/api/v1/admin/telegram-code` | `20260904T113203Z-84729c2` |
| 3.24 | `ce80fa3` | **ESLint flat config**: v10 + typescript-eslint v8 (без eslint-config-next — legacy peer-dep). 7 stale eslint-disable директив удалены. `npm run lint` exit 0 | (frontend-only) |
| 3.25 | `d1cbdca` | **mypy baseline**: 13 type-фиксов (context.py, service.py, student/router.py). `Success: no issues found in 7 source files` для app/parents + app/student | `20260904T121630Z-d1cbdca` |
| 3.25b | `56cde46` | **Flaky fix**: `assert code.isupper()` → `assert code == code.upper()` (digits не имеют case, случайная hex-only строка ломала flake-guard) | `20260904T123033Z-56cde46` |

## Итог

- **Все P0-этапы плана закрыты** (Этап 0, 1.1, 1.2, 1.3, 1.4; побочные supervisor + smoke + author rewrite; Этап 2.1, 2.2, 2.3).
- **Full pytest 1521 passed** (+10 к baseline 1511), 30 skipped, 1 xfailed (legacy xfail), 2 warnings.
- **Frontend build:** ✓ Compiled successfully в 3.4s.
- **Frontend lint:** 0 errors, 45 warnings (baseline зафиксирован, уменьшаем).
- **Прод:** `/health=200`, alembic=0026, latest deploy `20260904T123033Z-56cde46`.
- **HEAD `56cde46`** на remote `design-audit-2026-08-20-fixes`.

## Известные issues (для следующих sprint'ов)

- **#1 flaky-test в Sprint 32 (now fixed)** — закрыт в 3.25b.
- **#2 doc-archive**: `docs/` = 213 файлов, нужен INDEX.md и `docs/archive/2026-07|08/*.md`.
- **#3 master CI gate**: ветка `main` имеет `caa81c985...` (Sprint 108), но в git remote `main` нет branch protection rule на `Release Gate / gate` — проверить в GitHub UI.
- **#4 smoke green через реальный prod cred**: требует владельца для выбора test-user (НЕ менять whitelist).
- **#5 263 файла ruff --fix + 282 файла ruff format** — unstaged, deferred to Sprint 3.26+.

## Детальные отчёты

- `/root/workspace/audit-2026-09/11-audit-2026-09-03-3rd-party.md` (D4 с append)
- `/root/workspace/ai-tutor/docs/backlog/2026-09-04-sprint-3.26+.md` (handoff для следующей сессии)
