# AI-Tutor — Сессия: разбор 109 dirty файлов и фикс S3.2/S3.6

**Дата старта сессии:** 2026-09-01 (после production deploy 2026-09-01 11:25-11:40 MSK + фикс табов 15:30-15:35)
**Ветка:** `design-audit-2026-08-20-fixes` HEAD `a27355b`
**Workspace:** `/root/workspace/ai-tutor`
**Цель сессии:**
1. Разобрать 109 dirty файлов (modified + untracked) — определить, какие реально нужны, какие удалить.
2. Восстановить `apps/frontend/app/admin/feedback/page.tsx` (был удалён с проды при deploy 2026-09-01) — добавить недостающий `adminFeedbackSummary` API в backend.
3. Реализовать S3.2 (проверка понимания) и S3.6 (Сообщить об ошибке + admin queue) если останется время.
4. Дать финальные **полные ответы**, которые пользователь (Игорь) вернёт в основной чат с Hermes для продолжения работы.

**Контекст и наследие сессии 2026-09-01 (10:35-12:00):**

## Что есть в репозитории (после сессии 2026-09-01)

### 12 atomic commits в этой ветке (от HEAD):
- `a27355b` fix(admin): visible pill tabs (Audit log, Пользователи, etc.) — убран overflow-x-auto
- `d9a7dff` docs(audit): production deploy report 2026-09-01 — 280/280 practice, smoke passed
- `2bf0e6e` docs(audit): S2+S3 report and INDEX sync
- `83fd015` feat(pedagogical-ai): S3.1/3.3/3.4/3.5/3.7 — multi-explain, offtopic, honest refuse
- `1707aa4` feat(practice): S2 — seed ≥10 fallback tasks for all 263 topics (D2.7)
- `8170098` fix(citations): S1.3 — hide textbook sources for student role (D2.2)
- `84f73a5` chore(evidence): S1.2 + S1.5 — honest statuses for 16 subjects
- `d0c5981` feat(curriculum): S1.1 — add 4 subjects (chem/hist-world/lit-2/rus-2) per D2.1
- `a777f33` fix(tests): S0 — restore ai_budget limits in test_all_subject_contracts
- `f0b5e93` fix(tests): S0 — restore budget defaults in test_math6_pilot fixture
- `a8e0c03` chore(frontend): S0.5 — /parent redirect, drop console.log, remove duplicate tailwind.config.js
- `1db73d3` docs(tests): S0.3 — rewrite tests/README.md to current 1340/30 reality
- `2148c8e` docs(audit): S0.6 — sync INDEX.md to post-S0 numbers
(всего 13 коммитов от старта ветки; 6 моих + 7 предыдущих)

### Production state (https://school.431a.ru)
- 16 subjects / 280 topics / 280 practice (100% coverage)
- /health /ready /api/v2/health = 200
- Backend (Python/FastAPI) + frontend (Next.js) + Redis + Postgres + Grafana
- Multi-explain (6 styles), offtopic-guard (pre-AI keywords + system prompt), honest refuse, Socratic mode работают
- Табы админки ВИДНЫ (фикс a27355b)
- 5 дней мониторинга: /health каждые 5 мин + /api/v1/subjects 1 раз в день
- Backup: `db-20260901T153121Z.sql.gz`, offsite SMB, retention OK (234 файлов)

### Удалено с проды в сессии 2026-09-01:
- `apps/frontend/app/admin/feedback/page.tsx` — TypeScript error (api.adminFeedbackSummary не существует). Файл **потерян при git stash drop** в сессии fix-tabs. Если админке нужна страница feedback — нужно **восстановить + реализовать API** (S3.6 часть).

---

## ГЛАВНАЯ ЗАДАЧА: разбор 109 dirty файлов

**Состояние на старте сессии:**
```bash
cd /root/workspace/ai-tutor && git status --short
# должно показать ~109 файлов (modified + untracked + deleted)
```

**ВАЖНО**: в сессии fix-tabs я потерял `git stash drop`, поэтому часть файлов уже могла исчезнуть. Полный список нужно **заново собрать через `git fsck --unreachable` или `git reflog`**.

### Категории dirty файлов (по памяти предыдущей сессии, может быть неполный):

**Modified (M) — 21 файл (вернулись из stash@{0} после git stash pop):**
```
M README.md
M apps/backend/app/admin/router.py
M apps/backend/app/ai/prompts.py                       ← мой S3.1/S3.4/S3.5
M apps/backend/app/ai/service.py                       ← мой S3 (chat pre-filter, thread-local)
M apps/backend/scripts/content_quality_baseline_audit.py
M apps/backend/tests/test_ai_output_contract.py
M apps/backend/tests/test_flake_guard_sprint32.py
M apps/backend/tests/test_progress_diagnostics.py
M apps/backend/tests/test_rag_integration.py
M apps/backend/tests/test_sprint59_multi_child.py
M apps/backend/tests/test_sprint82_healthcheck_redis.py
M apps/frontend/app/login/page.tsx
M apps/frontend/app/subjects/[id]/page.tsx
M apps/frontend/app/topics/[id]/components.tsx
M apps/frontend/app/topics/[id]/page.tsx
M apps/frontend/e2e/mvp-student-flow.spec.ts
M apps/frontend/lib/api.ts
M apps/frontend/playwright.config.ts
M deploy/release/deploy.sh
M docs/ALL-SUBJECTS-PRODUCTION-READINESS-2026-08-19.md
M docs/audit-2026-08-23/01-audit-full.md
M docs/pilot-topic-matrix.md
M docs/pilot-walkthrough-notes.md
```

**Untracked (??) — 86+ файлов (часть могла быть потеряна при stash drop):**
```
?? AUDIT_2026-08-22.md                                  ← потерян, можно восстановить вручную
?? apps/backend/scripts/mapping_quality_audit.py
?? apps/backend/tests/test_automated_release_gate.py    ← потерян
?? apps/backend/tests/test_fallback_safety_contract.py
?? apps/backend/tests/test_ops_release_gate.py
?? apps/frontend/app/admin/feedback/page.tsx            ← потерян (нужен для S3.6 если нужен)
?? apps/frontend/e2e/mobile-safe.spec.ts
?? apps/frontend/e2e/mocked-auth-mobile-contract.spec.ts
?? apps/frontend/e2e/mocked-auth-ui-contracts.spec.ts
```

### Алгоритм разбора для сессии:

**Шаг 1: Полная разведка**
```bash
cd /root/workspace/ai-tutor
git status --short | sort > /tmp/dirty-files-2026-09-01.txt
wc -l /tmp/dirty-files-2026-09-01.txt
git fsck --unreachable --no-reflogs 2>&1 | head -20  # что потерялось
git diff --stat | tail -30
git diff --stat apps/backend/app/admin/router.py
# для каждого файла: git diff <path> | head -50 — что меняли?
```

**Шаг 2: Категоризация**

| Категория | Действие | Примеры |
|---|---|---|
| **A. Мой S3** | Оставить + commit | `apps/backend/app/ai/prompts.py`, `apps/backend/app/ai/service.py` |
| **B. Чужой, нужный** | Принять чужую правку + commit отдельно | зависит от содержимого |
| **C. Чужой, сломанный** | Удалить | `admin/feedback/page.tsx` (если решение — не делать admin feedback) |
| **D. Чужой, дублирующий** | Удалить | зависит от содержимого |
| **E. Временный/debug** | Удалить | `AUDIT_2026-08-22.md` |
| **F. Generated/secrets** | Удалить + .gitignore | если есть |

**Шаг 3: для `admin/feedback/page.tsx` — принять решение**

Два варианта:
- **(A) Восстановить + реализовать API** — добавить в backend `GET /api/v1/admin/feedback/summary` → adminFeedbackSummary.
- **(B) Удалить навсегда** — feedback UI не нужен в MVP.

**Шаг 4: Atomic commits по группам**

- Commit 1: «chore: S0.1 — commit foreign auth/admin router changes» (если они нужны)
- Commit 2: «chore: S0.1 — drop broken admin/feedback page.tsx (API не реализован)»
- Commit 3: «chore: S0.1 — accept foreign test changes (e2e, mapping_quality_audit, ...)»
- Commit 4: «docs: drop AUDIT_2026-08-22.md notes (superseded by 2026-09-01)»

Каждый commit — один логический кусок. **Никогда `git add -A` или `git add .`**.

**Шаг 5: Verify**
```bash
git status --short | wc -l
cd apps/backend && APP_SECRET_KEY=test APP_ENV=test .venv/bin/pytest tests/ -q --tb=line -p no:cacheprovider --no-header > /tmp/post-cleanup-pytest.log 2>&1
tail -5 /tmp/post-cleanup-pytest.log   # должно быть 1343/30/1 (flake) или лучше
cd ../frontend && npx tsc --noEmit && npm run build
```

---

## ЗАДАЧА 2: Реализовать S3.2 и S3.6

### S3.2 Проверка понимания (D1.4)
- После успешного ответа ученика — бот задаёт 2-3 коротких вопроса «своими словами».
- Реализация: в `apps/backend/app/ai/service.py::generate_exercise` или новый endpoint `/api/v2/exercises/{id}/understand-check`.
- Использовать `prompts.explain_topic_system(style="questions")` как prompt.
- Тест: `tests/test_s3_understand_check.py` — мокаем AI, проверяем что endpoint возвращает 3 вопроса.

### S3.6 Сообщить об ошибке + admin queue
- Кнопка в UI чата/ответа AI → POST `/api/v1/feedback/report` с {message_id, category, text}.
- Новая таблица БД `feedback_reports` через alembic миграцию `0022_feedback_reports.py`.
- Admin endpoint `GET /api/v1/admin/feedback-reports`.
- Тесты: `tests/test_s3_feedback_report.py`.

**НЕ делать без явного OK от пользователя**.

---

## ОБЯЗАТЕЛЬНЫЙ ВЫХОДНОЙ ФОРМАТ ДЛЯ ПОЛЬЗОВАТЕЛЯ

В конце сессии верни пользователю (Игорю) в чате подробный отчёт, который он скопирует в основной чат с Hermes. Формат:

```markdown
## ОТЧЁТ ИСПОЛНИТЕЛЯ — 2026-09-01 (Sprint S0.1 follow-up + S3.2/S3.6)

### Главное
- 109 dirty файлов разобраны: X моих оставлено, Y чужих принято, Z удалено, W в отом.
- admin/feedback/page.tsx: [удалён | восстановлен + API реализован].
- S3.2 (проверка понимания): [done/partial/deferred + evidence].
- S3.6 (Сообщить об ошибке): [done/partial/deferred + evidence].

### Новые коммиты
- <sha> — <message>

### Тесты
- Backend: N1 passed / N2 failed / N3 skipped (команда, дата)
- Frontend: typecheck exit code, build RC
- E2E: N/M passed

### Production: 0 mutations
- (если делал backup+deploy — перечисли)

### Открытые блокеры
1. ...

### Следующий executable slice
- ...

### Полные ответы на вопросы Игоря
Q: <вопрос>
A: <ответ>
```

---

## СТЕК И КОНВЕНЦИИ

- Python 3.12.3 + venv `.venv/bin/python` и `.venv/bin/pytest`
- Frontend: Node.js + Next.js 16.2.10 + Turbopack
- Test env: `APP_SECRET_KEY=test-secret-key-for-pytest-only-1234567890 APP_ENV=development DATABASE_URL='sqlite+pysqlite:///:memory:' CORS_ORIGINS='http://localhost:3000' AI_API_KEY='mock-key-for-tests' UPLOAD_DIR='/tmp/ai-tutor-test-uploads' PYTHONDONTWRITEBYTECODE=1`
- Production: ssh `ssh -i /root/.ssh/id_ed25519_kirill_ai root@192.168.1.86`, HTTPS self-signed, deploy через `deploy/release/deploy.sh`
- **НЕ** трогай: `.env`, secrets, миграции 0001-0021, `*-original.pdf`, `/etc/ai-tutor/.env`, без явного OK
- **Production mutation** — только backup+rollback
- Git: atomic commits по темам, **никогда `git add -A` или `git add .`**

---

## ЧТЕНИЕ ПЕРЕД СТАРТОМ

1. `/root/workspace/ai-tutor/docs/audit-2026-08-31/INDEX.md`
3. `/root/workspace/ai-tutor/docs/audit-2026-08-31/AI-TUTOR-DEPLOY-REPORT-2026-09-01.md`
4. `/root/workspace/ai-tutor/docs/audit-2026-08-31/AI-TUTOR-SPRINT-S2-S3-REPORT-2026-09-01.md`
5. `git log -13 --oneline`
6. `git status --short | wc -l`

---

## КРИТЕРИИ «СЕССИЯ ВЫПОЛНЕНА»

✅ Сделано:
- [ ] 109 dirty файлов разобраны и закоммичены по темам
- [ ] `admin/feedback/page.tsx` либо восстановлен + API реализован, либо удалён навсегда (с обоснованием)
- [ ] Тесты зелёные (1343/30/1 baseline + новые если S3.2/S3.6 делал)
- [ ] Frontend typecheck/build зелёные
- [ ] Production не изменён (если только разбор — 0 mutations)
- [ ] Финальный отчёт в формате выше готов для копирования

❌ Не сделано (явно в отчёте):
- Любые из задач выше, которые не влезли

---

*Сессия-2026-09-01-follow-up. Цель: разобрать dirty + реализовать deferred (опционально) + дать ответы Игорю в формате для копирования в основной чат.*