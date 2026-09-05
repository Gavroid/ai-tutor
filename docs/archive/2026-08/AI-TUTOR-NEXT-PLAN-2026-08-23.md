# AI-Tutor — пост-Sprint-8 план (continuation, 2026-08-23)

Дата: 2026-08-23
Основание: фактическое состояние на HEAD `c77a92e` (ветка
`design-audit-2026-08-20-fixes`), плюс ручная разведка этой сессии.
Replacement для `AI-TUTOR-NEXT-SESSION-PROMPT-AUDIT-2026-08-23.md`,
который был закрыт спринтами S1–S8.

---

## 0. Факты на входе (чтобы планирование не ушло в фантазии)

### 0.1 Что уже сделано и зелено

S1–S8 коммиты (`c6537bf` … `c77a92e`, 6 коммитов) дают:

- 8 spec test files, **135 passed, 131 warnings, ~44s**.
  Per-sprint таблица подтверждена прогоном `2026-08-23T12:04Z`,
  см. `AI-TUTOR-CURRENT-STATUS.md`.
- Полный `test_sprint*.py` бандл: **637 passed, 20 skipped, 0 failed**.
- Frontend `npm run typecheck` clean, `npm run build` 24 routes.
- `git diff --check` clean.
- `sprint32_parent_2fa` flake закрыт через
  `asyncio_default_fixture_loop_scope=function` в `pytest.ini`
  (race condition в asyncio scope).

### 0.2 Стек/окружение этой машины

- `/opt/ai-tutor` существует (production mount) — **read-only by rule**.
- `docker` **НЕ установлен** на этой машине. `disposable-staging.sh`
  из S7 здесь НЕ запустить; нужен CI runner / внешний стенд.
- `npm`, `pytest`, `.venv/bin/python` — есть.
- Рабочая директория: `/root/workspace`, основной репо:
  `/root/workspace/ai-tutor`.
- `nightscout/` существует как sibling. В эту сессию не лезу.

### 0.3 Dirty tree на HEAD `c77a92e`

```
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
?? (unttracked: AUDIT_2026-08-22.md, CHECKLIST.md,
    grade7-curriculum/, grade7-humanities/, нескольких docs/*.md,
    AUDIT-CURRENT-2026-08-23.md, NEXT-SESSION-PROMPT-AUDIT-2026-08-23.md,
    SPRINT-PLAN-2026-08-23.md, и т.д.)
```

Это pre-existing dirty с прошлых сессий. Не моё. **Не трогаю** —
выход за scope. Если какие-то из них вредят `git diff --check`,
оставляю до явного одобрения.

### 0.4 Реальные warning-категории (current)

`pytest -W error::Warning` дал 61 collection errors из-за
`DeprecationWarning: 'crypt' is deprecated` (passlib). Это не regression
от моих коммитов — это шум, который уже был в тестах с прошлых сессий.
Inventory:

- `passlib.utils`: `'crypt' is deprecated` — идёт в каждый pytest
  collection (≈61 мест).
- `jose.jwt`: `datetime.datetime.utcnow()` deprecated — идёт в каждый
  jwt-touching тест.
- `pydantic._internal._config`: class-based `config` deprecated — V2
  config требует переход на `ConfigDict`.
- `sqlalchemy.engine.default`: sqlite3 default datetime adapter
  deprecated.
- `pytest-asyncio`: конфигурируется в `pytest.ini` (S1), но
  присутствует в pre-existing test_sprint88 (slow marker).

---

## 1. Приоритеты (отсортированы по убыванию риска и стоимости отсрочки)

### TIER 1 — на этой машине, сегодня, без docker

**T1.1 Фикс `_EVIDENCE_PATH` monkeypatch leak между запусками.
Sprint 1 зафиксил override, но НЕ сброс singleton `_provider_instance`
для `app.ai.service`. Тест `test_evidence_schema.py::test_api_*`
уже работает через `reset_evidence_cache`, но `app.ai.hermes`
singleton `_provider_instance` persist-ит между тестами.
Низкий риск (уже green), но документировать observed state, чтобы
следующая regression была диагностируема.**

Deliverable: regression-тест + comment.

**T1.2 Silent-failure guard в `_save_evidence` — на ошибке записи
evidence.json событие теряется (audit_log не пишется). Это уже было
в S3, но `service.record(...)` в `update_evidence` имеет try/except
спрятанный внутри. Стоит сделать checkpoint-test.**

Deliverable: 1 test ловит это поведение. Если сценарий приемлем — fix
не нужен, только test-as-spec.

**T1.3 Закрыть MAINTAIN debt: 3 deprecation categories.**
Не "переписывать весь passlib/jose/pydantic", а точечно
- passlib `crypt`: заменить на `cryptography` direct или явно
  filter warning через `pytest.ini` filterwarnings.
- jose `utcnow`: заменить на `datetime.now(datetime.timezone.utc)`
  в `apps/backend/app/auth/security.py` (forwarded к jose).
- pydantic class-based `config`: автоматический Pydantic V1→V2
  codemod; НЕ делаем вслепую. Только локально: у нас в коде
  файлы с `class Config:` нужно перечислить и замерить долю.

Минимальный план:
1. Закрыть passlib warning одним `filterwarnings` в `pytest.ini`
   (S1d — чисто noise, не architectural).
2. Перевести `jose` call site на `datetime.now(tz=...)` —
   atomic, в `app/auth/security.py` (S1e).
3. Pydantic V2 migration — **объём сессии**, не этой; оставляю
   пунктом P0 backlog для отдельного спринта, потому что codemod
   полу-вслепую это анти-паттерн и на этой машине без docker
   не выполнить полный Playwright regression.

Deliverable T1.3: pytest.ini filterwarnings для passlib + 1 patch в
security.py + 1 doc `docs/AI-TUTOR-PYDANTIC-V2-MIGRATION-PLAN.md` как
backlog item. Test count: +2, no regression.

**T1.4 Cleanup `CURRENT-STATUS.md`.** Уже 568 строк, раздут. Делю на:
- `AI-TUTOR-CURRENT-STATUS.md` — только executive status (≤200 строк).
- `AI-TUTOR-SPRINT-EXECUTION-LOG.md` — per-sprint детали.

Без удаления содержания, только разделение.

### TIER 2 — на этой машине, но требует бОльшего объёма

**T2.1 Реальный запуск `apps/backend/tests/test_disposable_environment.py` через настоящий CI runner — нельзя (нет docker).** Заменяю на:
- Расширить disposable tests: добавить contract на `GET /health` отдаёт
  меньше (без redis DB-hit), как prometheus_liveness_standard.
- `apps/backend/tests/test_evidence_schema.py` уже есть с CLI test;
  добавить contract что CLI exit code 0 для реального
  `evidence.json` (есть в test_validate_real_evidence_*).

**T2.2 Запустить `apps/frontend/e2e/mvp-student-flow.spec.ts` (новый)**
против локального backend (in-memory SQLite + deterministic mode).
Это можно сделать без docker. На этой машине я могу:
1. Поднять backend на `python3 -m uvicorn` с in-memory SQLite.
2. Прогнать `npm run test:e2e:mvp` с `BASE_URL=http://localhost:8000`.
Но это **долгий** прогон (Playwright требует browser binary).
Избегаю этот план, если реальная выгода низкая.

Skip — оставляю как explicitly deferred в plan.

**T2.3 Reproduce flake-guard в `pytest.ini` для test_sprint*-bundle.**
Сейчас 637 passed. Но в pre-existing test_sprint32 flake-fix был
«случайный» через asyncio scope. Нужно **фиксирующий тест**, который
запускает flake-prone тест 10 раз подряд и валит если хоть один
развалится. Это даёт уверенность что мы не сломали это снова.

Deliverable: 1 файл, ~60 строк. Test type: parametrize retry.

### TIER 3 — за рамками этой машины / требует review

**T3.1 License review 20 manifest rows** (`needs_review` = 20).
Юридическая работа, не код. Я могу только подготовить таблицу
с рекомендациями по license_decision (CC BY? fair_use?) и зоной
риска; затем остановиться.

**T3.2 Mobile viewport Playwright (Sprint 4 §критерий).**
Framework в `mvp-student-flow.spec.ts` готов, но реальный
chromium прогон — на disposable. Skip.

**T3.3 Pydantic V1→V2 codemod (S1.3 back-burner).**
Выделенный sprint. Out of scope этой сессии.

**T3.4 Splits в `apps/backend/scripts/run_backend_groups.sh`
на отдельные parallel jobs в CI.** Не требует правок на этой
машине, это config CI. Заношу в backlog.

---

## 2. План этой сессии (что я фактически буду делать)

В порядке от дешёвого к дорогому:

1. **(T1.1) regex-тест `_provider_instance` singleton state.** (~10 строк)
2. **(T1.4) split `CURRENT-STATUS.md`** на status + execution-log.
   Move-only; всё содержание сохраняется в execution-log. (~30 мин)
3. **(T1.3a)** `filterwarnings` для passlib в `pytest.ini`. (~5 строк)
4. **(T1.3b)** `app/auth/security.py`: `datetime.utcnow()` →
   `datetime.now(tz=utc)`. Atomic, 1 функция. (~20 строк + test)
5. **(T1.3c)** doc `docs/AI-TUTOR-PYDANTIC-V2-MIGRATION-PLAN.md`
   как backlog, чтобы не потерялось.
6. **(T2.1)** expandable disposable contract test на `GET /health`
   payload (schema test). (~40 строк + 2-3 теста)
7. **(T2.3)** flake-guard parametrize runner для test_sprint32.
   (~50 строк)
8. **(T3.1)** license-таблица предложения по 20 manifest rows в
   `docs/AI-TUTOR-LICENSE-REVIEW-DRAFT-2026-08-23.md` (НЕ применяется,
   только draft для человека).
9. **Status sync**: обновить `CURRENT-STATUS.md` (новое executive
   status) + `execution-log`, commit.
10. Smoke regression: pytest --collect-only + 8 spec регрешн.

Hard stop criteria:
- Если pytest красный на 8 spec после любого шага — откат через
  `git stash`.
- Если flake-guard воспроизводит flake (>0/10 fails) — фикс
  иначе план не двигается дальше.
- Если passlib filter ломает ≥1 ранее зелёный тест — откатить.

---

## 3. Что точно НЕ делать в этой сессии

- **Не править `/opt/ai-tutor`** — production mount.
- **Не править Nightscout** — sibling-project, не наш scope.
- **Не делать `git clean` / `git reset` / `git checkout`** на
  pre-existing dirty файлах (вне моих 6 спринтовых коммитов).
- **Не расширять pilot scope** (только Math-6 в `PILOT_SCOPE`).
- **Не запускать `disposable-staging.sh up`** — нет docker.
- **Не делать Playwright полный прогон** — долго.
- **Не менять `.env`, secrets/**.

---

## 4. Решения с отложенным следствием (без вопросов, justified)

- `(T2.1)` расширение disposable tests **БЕЗ docker** — backend tests
  не требуют docker, могут исполняться в памяти. Это допустимо.
- `(T3.1)` Я составлю **только markdown draft** для license review;
  никаких auto-applied изменений в `textbook-manifest.csv`. Operator
  review обязателен.
- `(T1.4)` Разделение файла — semantic rename, не удаление.
  Старый `AI-TUTOR-CURRENT-STATUS.md` остаётся **только**
  как pointer на новый файл и как git history.

---

## 5. Известные риски этой сессии

| Риск | Митигация |
|---|---|
| Изменения сломают существующие тесты | Каждый шаг + регрешн 8 spec |
| Изменения сломают pre-existing dirty файлы | Editрую только SPEC-FILES (Sprint 1-8) + новые .md |
| passlib filter подавит настоящее предупреждение | Только `'crypt' is deprecated` по marker match; другие deprecation остаются |
| pre-edit SMB hook не сработает (как было в прошлой сессии на S5–S8) | Промежуточный коммит на каждом этапе; pre-edit проверяется в `git log -1` через наличие `preedit-...` line в окружении или backup check |
| Time budget этой сессии | Hard cap: после T2.3 → status sync → стоп |
