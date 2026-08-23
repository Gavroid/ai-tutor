# AI-Tutor — handover prompt для продолжения (2026-08-23)

Это **handover-prompt**, не план. План — следующий раздел.

Скопируй содержимое раздела «PROMPT» целиком и вставь в начало
новой сессии чата.

---

## PROMPT

```
Ты подхватываешь AI-Tutor проект в середине серии continuation-сессий.
HEAD = 33ddafa на ветке design-audit-2026-08-20-fixes.

### Контекст

В текущей ветке:
- Sprints 1–8 закрыты (коммиты c6537bf … dfc4d42) + 11 continuation-
  коммитов (2164a1f … 33ddafa) для deprecation cleanup,
  dependency audit, и starlette migration plan.
- 8 spec test files зелёные: 138 passed в regression (нулевой warning).
- test_sprint* bundle: 637 passed + 20 skipped, 0 failed.
- Frontend: npm run typecheck green, npm run build → 24 routes.
- git diff --check clean.

Проект переведён от "Internal MVP / controlled pilot candidate" к
"воспроизводимый автоматический Math-6 pilot" (~85% Definition of Done).
Sprint-план полностью закрыт в test level; runtime-блок на disposable CI
(нет docker на этой машине).

### Что НЕ делать

- Не править /opt/ai-tutor (production mount, read-only).
- Не править Nightscout (sibling-project, не наш scope).
- Не править .env, secrets/ — read-only.
- Не расширять pilot scope за Math-6 (PILOT_SCOPE = {"math"} в
  apps/backend/app/subjects/evidence_schema.py).
- Не выставлять manual_smoke_ready=true (мы честно держим false).
- Не делать auto-upgrade major versions (starlette/cryptography/
  pillow/pypdf/multipart/transformers — major API breakage, отдельный
  sprint на каждый).
- Не удалять pre-existing dirty файлы в репо
  (README.md, apps/backend/app/ai/prompts.py, тесты вне моей зоны —
  они до моих continuation-сессий, не трогай).

### Доступы и пути

ОС: Linux (Proxmox 7.0.6-2-pve, kernel 7.0).
WSL: НЕТ. Этот стенд — основная машина.
Working dir: /root/workspace (НЕ /root/workspace/ai-tutor — но именно
там находится проект).
Ветка: design-audit-2026-08-20-fixes.

Репо (основной):
  /root/workspace/ai-tutor/
  /root/workspace/ai-tutor/apps/backend/          # FastAPI + pytest
  /root/workspace/ai-tutor/apps/frontend/         # Next.js + Playwright
  /root/workspace/ai-tutor/data/textbooks/7-class/  # manifest + mappings + evidence.json
  /root/workspace/ai-tutor/deploy/                # docker-compose, backup/
  /root/workspace/ai-tutor/deploy/disposable-staging.{sh,toml}  # S7

Production (НЕ ТРОГАТЬ):
  /opt/ai-tutor/                                   # production mount

Sibling (НЕ ТРОГАТЬ):
  /root/workspace/nightscout/

Backend tests:
  apps/backend/tests/test_admin_evidence.py       (S1, 10 passed)
  apps/backend/tests/test_ai_explain_contract.py  (S2, 10 passed)
  apps/backend/tests/test_evidence_schema.py      (S3, 15 passed)
  apps/backend/tests/test_math6_pilot.py          (S4, 50 passed)
  apps/backend/tests/test_manifest_provenance.py  (S5, 18 passed)
  apps/backend/tests/test_retrieval_benchmark.py  (S6, 8 passed)
  apps/backend/tests/test_disposable_environment.py (S7, 18 passed)
  apps/backend/tests/test_maintenance_ci.py       (S8, 9 passed)
  apps/backend/tests/test_flake_guard_sprint32.py  (extension, safety-net)

Test runners:
  cd /root/workspace/ai-tutor/apps/backend
  .venv/bin/pytest -q tests/test_admin_evidence.py tests/test_ai_explain_contract.py \
                    tests/test_evidence_schema.py tests/test_math6_pilot.py \
                    tests/test_manifest_provenance.py tests/test_retrieval_benchmark.py \
                    tests/test_disposable_environment.py tests/test_maintenance_ci.py

Frontend:
  cd /root/workspace/ai-tutor/apps/frontend
  npm run typecheck
  npm run build
  npm run test:e2e:mvp   # требует БД на remote URL (192.168.1.86)

Backend venv: /root/workspace/ai-tutor/apps/backend/.venv
  python: 3.12.3
  pytest: 8.3.4
  .venv/bin/python -m pip_audit --skip-editable  # dependency audit

Стиль кода:
- Python: snake_case vars, PascalCase classes, type hints обязательны.
- Conventional commits: <type>(<scope>): <summary>.
- Branch: design-audit-2026-08-20-fixes (НЕ менять, НЕ создавать
  новых без явного одобрения — это тестовая ветка).
- Pre-edit SMB backup: \\192.168.1.91\Kirill-AI\ai-tutor\pre-edit\
  — хук автоматический, но НЕ работает в inline shell commands.
  Если коммитишь через patch+git add+git commit — должно сработать.
  Если нет — это normal warning, не блокер.

Технические факты машины (ОБЯЗАТЕЛЬНО проверь):
- Docker НЕ установлен (which docker → exit 1).
  → disposable-staging.sh НЕ запустить здесь. Нужен CI runner.
- /opt/ai-tutor существует (production mount, read-only).
- Python: Linux 3.12.3.
- npm + node доступны.
- pip-audit установлен в .venv (с этой сессии).

### Файлы контекста (прочитать в начале)

1. /root/workspace/ai-tutor/docs/AI-TUTOR-AUDIT-CURRENT-2026-08-23.md
   — baseline audit. 11 risks, 10 known issues.
2. /root/workspace/ai-tutor/docs/AI-TUTOR-NEXT-PLAN-2026-08-23.md
   — план следующей сессии (post-Sprint 8). 5-tier разделение.
3. /root/workspace/ai-tutor/docs/AI-TUTOR-SPRINT-EXECUTION-LOG.md
   — per-sprint детали (S1–S8).
4. /root/workspace/ai-tutor/docs/AI-TUTOR-CURRENT-STATUS.md
   — executive status (138 строк). HEAD=33ddafa.
5. /root/workspace/ai-tutor/docs/AI-TUTOR-DEPENDENCY-AUDIT-2026-08-23.md
   — pip-audit snapshot. 98 vulns в 12 packages, 7 closed surgical.
6. /root/workspace/ai-tutor/docs/AI-TUTOR-PYDANTIC-V2-MIGRATION-PLAN.md
   — pydantic V1→V2 codemod backlog.
7. /root/workspace/ai-tutor/docs/AI-TUTOR-STARLETTE-1X-MIGRATION-PLAN.md
   — starlette 0.41→1.3.1 план (8-12h estimate).
8. /root/workspace/ai-tutor/docs/AI-TUTOR-LICENSE-REVIEW-DRAFT-2026-08-23.md
   — license decision draft для 20 manifest rows.

### Что осталось реально (отчёт по %, если известно)

Sprint plan: ~85-90% выполнено (test level).
Definition of Done:
  - Spec-тесты:        100%
  - test_sprint bundle: 100%
  - Deterministic MVP:  100%
  - Canonical readiness:100%
  - Deprecation cleanup:100%
  - 15 P0 Math contracts:100%
  - Manifest schema:   ~95% (license apply pending)
  - recall@5/MRR@5:    ~80% (token-overlap, не true embedding)
  - Disposable CI env: ~70% (config+script готов, no docker)
  - Mobile Playwright: ~30% (framework, no runtime)
  - Dependency/security: ~15% (7/98 CVE closed surgical)
  - License apply:     ~15% (draft сделан, operator apply)

### Pre-edit dirty state (только для сведения — НЕ править)

M README.md
M apps/backend/app/ai/prompts.py
M apps/backend/scripts/content_quality_baseline_audit.py
M apps/backend/tests/test_content_quality_baseline_audit.py
M apps/backend/tests/test_progress_diagnostics.py
M apps/backend/tests/test_rag_integration.py
M apps/backend/tests/test_sprint82_healthcheck_redis.py
M docs/ALL-SUBJECTS-PRODUCTION-READINESS-2026-08-19.md
M docs/pilot-topic-matrix.md
M docs/pilot-walkthrough-notes.md

Это pre-existing changes от прошлых сессий (не моих). Не в моей зоне.
При работе добавляй ТОЛЬКО свои staged changes. git diff-check clean
текущий — после моих коммитов. Сохраняй это состояние.

### Стиль работы (что делать в начале сессии)

1. Сразу после greeting — sanity regression:
   .venv/bin/pytest -q tests/test_admin_evidence.py tests/test_ai_explain_contract.py \
                     tests/test_evidence_schema.py tests/test_math6_pilot.py \
                     tests/test_manifest_provenance.py tests/test_retrieval_benchmark.py \
                     tests/test_disposable_environment.py tests/test_maintenance_ci.py
   Ожидаемо: 138 passed in ~45s, 0 warnings. Если НЕ — git status,
   git diff, восстановить baseline.

2. Прочитать эти файлы В НАЧАЛЕ (поставлено в порядке priority):
   a) AI-TUTOR-AUDIT-CURRENT-2026-08-23.md (audit baseline)
   b) AI-TUTOR-NEXT-PLAN-2026-08-23.md (текущий план)
   c) AI-TUTOR-CURRENT-STATUS.md (current executive)

3. Не спрашивать разрешений на Sprint 1–8 уже закрытые пункты.
   Если хочешь improve — RED → GREEN test. Не делай speculative work.

4. После каждого commit: проверять git diff --check + 8-spec regression.

5. Делай atomic commits. Не ставь >1 logical change в один commit.

6. Не запускай pip install / npm install без необходимости. Если
   upgrade нужен — surgical, с regression proof.

7. Sprint 9+ backlog: starlette 1.x migration (8-12h estimate),
   pillow 12.x, pypdf 6.x, python-multipart 0.0.31, transformers 5.x.

### Важно для подхвата этой работы

Проект "AI-Tutor" — это educational AI-tutor для школьников (7 класс).
Pilot scope: только математика (Math-6). Другие предметы не
трогать.

manifest_species_codes: math, algebra, geom, rus, lit, eng, hist,
hist-world, phys, inf, soc, chem, bio, geo, lit-2, rus-2.
Только 'math' в PILOT_SCOPE. Остальные blocked_ocr или preview.

Главная hypothesis: тщательная test-driven + canonical evidence.
Test fixtures используют SQLite in-memory (DATABASE_URL=sqlite+pysqlite:///:memory:)
и ai_deterministic_mode=1 env var (MockProvider).

### Audit + Plan pointers

audit link: docs/AI-TUTOR-AUDIT-CURRENT-2026-08-23.md
roadmap link: docs/AI-TUTOR-DEVELOPMENT-ROADMAP-2026-08-23.md
sprint plan: docs/AI-TUTOR-SPRINT-PLAN-2026-08-23.md
session log: docs/AI-TUTOR-SPRINT-EXECUTION-LOG.md

Если не можешь найти что-то — начни с `ls docs/` — все материалы
там, в .md файлах с префиксом AI-TUTOR-.
```

---

## Сводка этого handover-документа

Этот документ сохраняется по адресу:
```
/root/workspace/ai-tutor/docs/AI-TUTOR-HANDOVER-PROMPT.md
```

Когда открываешь новую сессию:

1. Копируй содержимое раздела **PROMPT** (внутри ` ``` `).
2. Вставляй как первое сообщение в новой сессии.
3. Если хочешь более краткий вариант — секция ниже.

### Краткая версия промта (TL;DR)

```
Подхвати AI-Tutor (continuation-сессия 12+).
HEAD = 33ddafa на design-audit-2026-08-20-fixes.
8 sprints + 11 continuation commits закрыты.
Spec regression: 138 passed, 0 warnings.
test_sprint*: 637+20skipped passed.

НЕ править: /opt/ai-tutor, Nightscout, .env, pre-existing dirty.
Pilot scope: только Math-6.
manual_smoke_ready=false (честно).
PILOT_SCOPE = {"math"} в evidence_schema.py.

Stack: Python 3.12, FastAPI/pytest, Next.js/npm, .venv.
Docker НЕ установлен. /opt/ai-tutor production mount НЕ трогать.

First steps:
1. .venv/bin/pytest tests/test_admin_evidence.py + 7 other spec files (138 pass)
2. Прочитай docs/AI-TUTOR-AUDIT-CURRENT-2026-08-23.md
   и docs/AI-TUTOR-NEXT-PLAN-2026-08-23.md
3. Прочитай docs/AI-TUTOR-CURRENT-STATUS.md
4. Делай git diff --check baseline before work.

Backlog (не в scope этой handover):
- starlette 1.3.1 upgrade (см. AI-TUTOR-STARLETTE-1X-MIGRATION-PLAN.md)
- pillow 12.x, pypdf 6.x, multipart 0.0.31, transformers 5.x
- License review apply (operator)

Не спрашивай разрешений на закрытые пункты. Если задача неясна —
выбирай одно: улучшить test coverage, или закрыть одну CVE по плану.
```

---

## История handover (для следующей сессии)

Этот документ создан после:
- 6 sprint commits (c6537bf … dfc4d42)
- 11 continuation commits (2164a1f … 33ddafa)
- 2 docs организационных (NEXT-PLAN, PLAN-LOG splt)
- 4 документов по частям долга: DEPENDENCY-AUDIT, PYDANTIC-V2-MIGRATION,
  STARLETTE-1X-MIGRATION, LICENSE-REVIEW-DRAFT.

Если новая сессия обнаружит новые коммиты — extend handover.
