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
| 3.26 | `599827b` | **ruff --fix batch**: 21 autofix (I001 unsorted-imports + W292 newline) в 257 файлах. Behavior не менялся. | (не нужен — git-only) |
| 3.27 | `46b94a5` | **ruff format batch**: 284 файла отформатированы (whitespace only). Поведение идентично. | (не нужен — git-only) |
| 3.28 | `61334f2` `06783ac` | **God-file split (Этап 3, шаг 1/4)**: dataclasses `CheckResult`/`GeneratedExercise` → `app/ai/datatypes.py`; `QuizQuestion`/`Quiz` → `app/ai/quiz_types.py`. service.py 1561 → 1522 строк (-39 LOC). Re-export для backward compat. Snapshot test публичного API 8/8 passed. | (не нужен — behavior unchanged) |
| 3.29 step 1 | `2fd6fc5` | God-file split (Этап 3): `explain_topic` body → `app/ai/_explain.py` (function-based extraction). service.py 1522 → 1438 (-84 LOC). | (не нужен — behavior unchanged) |
| 3.29 step 2 | `87749b8` | God-file split: `_build_rag_context` body → `app/ai/_rag.py`. 1438 → 1313 (-125 LOC). | (не нужен) |
| 3.29 step 3 | `6b890d5` | God-file split: `hint` + `hint_at_level` + `_hint_with_level` + `check_answer` → `app/ai/_dialog.py`. 1313 → 1236 (-77 LOC). | (не нужен) |
| 3.29 step 4 | `f6140d6` | God-file split: `generate_exercise` + `generate_quiz` → `app/ai/_generation.py`. 1236 → 1145 (-91 LOC). | (не нужен) |
| 3.29 step 5 | `78feb69` | God-file split: `chat` → `app/ai/_chat.py`. 1145 → **1099** строк (-46 LOC). | (не нужен) |
| 3.31 | `4503dba` | **pytest-xdist -n 4**: 9:32 → 2:46 (×3.46 speedup). requirements-dev.txt + ci.yml + release-gate.yml. Flake-guard 3/3 pass (166s, 166s, 164s). | (CI/dev only — нет prod impact) |
| 3.36 | `a6890b0` | **mypy strict expansion**: app.auth/* (security.py, oauth.py, router.py) → 0 errors. Plus app.users.twofa, app.observability_otel.py (с type: ignore[misc]), notifications/service.py list() fix. | (не нужен — pure type annotations) |
| 3.36a | `af5ac3c` | **mypy app/ai type fixes**: реальный баг — app/ai/router.py:559 импортировал AIMessage/AIRequest из app.ai.models (где их нет), фикс на app.ai.types. types.py: dict → dict[str, Any] в AIRequest/AIResponse. _explain.py: явная type annotation rag_context: str \| None. | (не нужен) |
| 3.37 | (pending) | **Snapshot-тесты для 6 публичных страниц × 2 viewport**: e2e/snapshots-public.spec.ts (12 snapshots: landing, login, register, forgot-password, link-parent, offline × desktop/mobile). maxDiffPixelRatio=0.02. GitHub Action snapshots.yml (manual trigger). 12 passed in 5.9s, 0 diff на repeat run. | (не нужен — фронт-only) |
| 3.38 | `ce226b1` | **Content-Security-Policy (report-only)**: `app/middleware/csp.py` + `app/admin/csp_report_router.py` (POST /api/v1/csp-report). 9 directives, включая `frame-ancestors 'none'` (анти-clickjacking). CSP_ENFORCE env для переключения в enforce mode. | (требует deploy для активации на проде; default report-only безопасный) |
| 3.39 | (skipped) | **passlib → bcrypt-direct migration**: план vague. passlib 1.7.4 + bcrypt 4.0.1 работает (только шумный deprecation warning). Низкий приоритет, deferred. | — |
| 3.40 | `fce711c` | **diff-cover coverage gate**: requirements-dev.txt + pyproject.toml [tool.diff_cover] + CI workflow. Baseline: 85% на diff vs origin/main (pass, threshold 80%). | (CI/dev only) |
| 3.41 | `d066c53` | **doc-archive**: 140 исторических отчётов `git mv` → `docs/archive/2026-08/`. 215 → 76 файлов в корне `docs/`. INDEX.md (5.7 KB) с категориями. archive/README.md (1 KB). | (docs only) |
| 3.42 | `333944f` | **Dependabot**: `.github/dependabot.yml` — 3 ecosystems (pip, npm, github-actions). Weekly по понедельникам 09:00 MSK. 4 groups (patch/dev-minor/prod-minor/major). 10 PR limit. | (CI only; ручная активация через GitHub UI) |

## Итог

- **Все P0-этапы плана закрыты** (Этап 0, 1.1, 1.2, 1.3, 1.4; побочные supervisor + smoke + author rewrite; Этап 2.1, 2.2, 2.3; **Этап 3 god-file split полностью — Sprint 3.28 dataclasses + 3.29 steps 1-5 method bodies → 5 модулей**; **Этап 4.3 xdist — Sprint 3.31**; **Этап 5 type safety — Sprint 3.36 + 3.36a**; **Sprint 3.37 snapshot-тесты для публичных страниц**; **Sprint 3.38 CSP**; **Sprint 3.40 diff-cover**; **Sprint 3.41 doc-archive**; **Sprint 3.42 Dependabot**).
- **Full pytest 1530 passed** (+10 к baseline 1511 → +9 от Sprint 3.28), 30 skipped, 1 xfailed (legacy xfail), 2 warnings sequential / 5 warnings параллельный (Pydantic × 4 workers + 1 pre-existing RuntimeWarning).
- **pytest-xdist -n 4:** 572s → 165s (×3.46 speedup). Flake-guard 3/3 pass.
- **diff-cover:** coverage 85% на diff vs origin/main (threshold 80%, pass).
- **Frontend build:** ✓ Compiled successfully в 3.4s.
- **Frontend lint:** 0 errors, 45 warnings (baseline зафиксирован, уменьшаем).
- **Снапшоты:** 12 baseline (6 страниц × 2 viewport) в `e2e/snapshots-public.spec.ts-snapshots/`. Repeat run 0 diff.
- **CSP:** middleware активен в report-only mode. Переключение через env `CSP_ENFORCE=true` после verification.
- **Прод:** `/health=200`, alembic=0026, latest deploy `20260904T123033Z-56cde46` (Sprint 3.25b flaky fix). После этого — **15+ refactor/type/CI/docs commits без deploy** (Sprint 3.28 + 3.29 step 1-5 + 3.31 xdist + 3.36 + 3.36a + 3.37 + 3.38 + 3.40 + 3.41 + 3.42).
- **HEAD `(c658608 + Sprint 3.36/3.36a/3.37/3.38/3.40/3.41/3.42 commits)`** на remote `design-audit-2026-08-20-fixes`.
- **service.py: 1561 → 1099 строк за 2 sprint'а (-462 LOC, -29.6%)**.

## Известные issues (для следующих sprint'ов)

- **#1 flaky-test в Sprint 32 (now fixed)** — закрыт в 3.25b.
- **#2 doc-archive**: `docs/` = 213 файлов, нужен INDEX.md и `docs/archive/2026-07|08/*.md`.
- **#3 master CI gate**: ветка `main` имеет `caa81c985...` (Sprint 108), но в git remote `main` нет branch protection rule на `Release Gate / gate` — проверить в GitHub UI.
- **#4 smoke green через реальный prod cred**: требует владельца для выбора test-user (НЕ менять whitelist).
- **#5 263 файла ruff --fix + 282 файла ruff format** — unstaged, deferred to Sprint 3.26+.

## Детальные отчёты

- `/root/workspace/audit-2026-09/11-audit-2026-09-03-3rd-party.md` (D4 с append)
- `/root/workspace/ai-tutor/docs/backlog/2026-09-04-sprint-3.26+.md` (handoff для следующей сессии)
