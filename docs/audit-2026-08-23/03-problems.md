# AI-Tutor — Проблемы (приоритезированный список)

**Дата:** 2026-08-23
**Цель:** категоризация ВСЕХ найденных проблем по severity (P0-P3) и effort (S/M/L).

**Severity:**
- **P0** — блокер для передачи Кириллу. Без fix нельзя.
- **P1** — серьёзная проблема. После fix можно передавать.
- **P2** — желательно до передачи, но не блокер.
- **P3** — тех. долг / polish.

**Effort:**
- **S** — часы (1-4 ч).
- **M** — дни (1-5 дней).
- **L** — недели (1-4 недели).

---

## P0 — блокеры (НЕЛЬЗЯ передать Кириллу без fix)

### P0-1 ❌ Fail-closed evidence-store сломан на проде

**Severity:** P0 (блокирует)
**Effort:** S (1-2 дня)
**Доказательство:**
- `evidence.json` на проде содержит `promotion_allowed=true AND blocked_reason=blocked_ocr` для 5 предметов (`hist`, `hist-world`, `eng`, `bio`, `chem`).
- API `/api/v1/subjects` возвращает `mvp_status=mvp_ready, pilot_visible=true, promotion_allowed=true` для 16/16.
- UI одновременно показывает «ПРАКТИКА 0/10» для hist-world, 0/17 для lit-2, 0/13 для rus-2, 0/15 для chem.

**Что не так:**
1. `evidence_to_dict()` и `router._subject_out()` не валидируют `promotion_allowed ⇒ blocked_reason IS NULL`.
2. Нет валидатора `evidence.json` при загрузке (даже на старте).
3. `evidence.json` на проде переписан руками без проверки инвариантов.

**Что делать:**
- Добавить `validate_evidence_invariants(data: dict)` в `evidence.py`. Бросать ValueError при нарушении. Вызывать при импорте из JSON.
- Переписать `evidence.json`: только `math` имеет все 6 гейтов true. Остальные — `preview`/`internal_mvp`/`blocked_ocr`, `pilot_visible=false`, `promotion_allowed=false`.
- Добавить `test_evidence_invariants.py` со всеми контраргументами.
- Расширить UI на `/subjects` — показывать статус-чип, а не только зелёный «MVP-ready». Использовать `blocked_reason` для amber/red бейджа.

**Почему опасно для Кирилла:**
Кирилл увидит «Всеобщая история», откроет, попадёт в topic, попросит практику — генератор выдаст generic fallback без привязки к учебнику. Ребёнок не сможет отличить, что это заглушка.

---

### P0-2 ❌ MVP E2E падает на Explain

**Severity:** P0 (невозможно проверить полный student flow)
**Effort:** M (2-3 дня на root cause + fix + regression)

**Доказательство:** `AI-TUTOR-AUDIT-CURRENT-2026-08-23.md` §6, `AI-TUTOR-NEXT-PLAN-2026-08-23.md` TIER 1.

- `tests/test_ai_explain_contract.py` — 10/10 passed, но smoke на проде падает.
- `npm run test:e2e:mvp` → 1 passed, 1 failed. `mvp-student-flow` падает на Explain.

**Что нужно:**
1. Contract tests для `POST /api/v1/ai/explain`:
   - success on P0 topic
   - 404 на unknown topic
   - 401 без auth
   - 429 при budget exhausted
   - 504 на provider timeout
   - 422 на malformed output (вернул не JSON)
   - 200 при RAG failure (graceful fallback)
2. Fix root cause (AI provider integration OR frontend pagination OR websocket stream).
3. Полный Playwright flow на deterministic provider:
   - open math topic → «Объяснить» → видим markdown
   - «Практика» → видим задание
   - wrong answer → видим feedback
   - correct answer → видим «next topic»
   - «Чат» → вопрос про то же → контекстный ответ
   - «Сделать паузу» → draft сохранён → refresh → restore

**Почему опасно для Кирилла:**
Если Explain падает в рабочем сценарии, у ребёнка нет объяснения. Он закроет вкладку и не вернётся.

---

### P0-3 ⚠️ `admin@example.com / Strongpass1!` не работает (smoke-блок)

**Severity:** P0 (нельзя проверить admin / parent / teacher сценарии)
**Effort:** S (30 мин)

**Доказательство:**
- `curl -X POST /api/v1/auth/login {"email":"admin@example.com","password":"Strongpass1!"}` → не возвращает токен (4 байта в ответе, не JSON token).
- `parent@example.com / Strongpass1!` → 401 Invalid credentials.

**Что нужно:**
1. Найти актуальные credentials из `seed_users.py` или `PILOT_SEED_TOKEN` (если они в env).
2. Либо задать новый password через `python3 -m app.scripts.seed_users --admin admin@example.com "..."` с токеном.
3. Задокументировать credentials в `/root/.ai-tutor-secrets/` (или в password manager).

**Почему опасно для Кирилла:**
Не страшно для ребёнка — но родитель не сможет зайти в дашборд, если его account не активирован.

---

### P0-4 ⚠️ `/api/v1/ai/exercises/generate` возвращает 404

**Severity:** P0 (часть student-flow не работает на API level)
**Effort:** S (1-2 ч на проверку реального endpoint)

**Доказательство:**
```
curl POST /api/v1/ai/exercises/generate {"topic_id": 121}
→ {"detail":"Not Found"}
```

**Возможные причины:**
- Endpoint называется иначе (`/exercises/generate` без `/ai`, или `/practice/generate`).
- Перенесён в v2 (`/api/v2/exercises/generate`).
- Требует auth формата (`POST /api/v1/exercises/generate` без `/ai/`).

**Что делать:**
- Проверить `apps/backend/app/ai/router.py` и `app/exercises/` — найти правильный путь.
- Если не существует — реализовать (это часть основного flow).
- Добавить OpenAPI schema для всех AI endpoints.

---

### P0-5 ⚠️ Async warnings (4 категории, 131 в спек-тестах)

**Severity:** P0 (маскирует реальные баги)
**Effort:** S (1-2 дня, в основном механическая замена)

**Из `AI-TUTOR-NEXT-PLAN-2026-08-23.md`:**
1. `passlib.utils: 'crypt' is deprecated` — заменить passlib.crypt на прямой bcrypt или argon2.
2. `jose.jwt: datetime.utcnow() deprecated` — заменить на `datetime.now(timezone.utc)` (частично сделано в commit `e66e7c9`, но остались).
3. `pydantic._internal._config: class-based config deprecated` — V2 migration (отдельный план).
4. `sqlalchemy.engine.default: sqlite3 default datetime adapter` — sqlite3 driver warnings.

**Конкретный опасный warning** (из `AI-TUTOR-SPRINT-EXECUTION-LOG.md`):
- `tests/test_email_per_lesson.py::test_notification_on_milestone_attempts` — coroutine never awaited. **Milestone email может не уходить к родителю**, а тест «зелёный» из-за `pass`.
- `tests/test_notifications.py::test_email_dry_run_without_smtp` — `asyncio.run` внутри sync-функции.

**Что делать:**
1. Запустить полный backend suite с `pytest -W error::RuntimeWarning` и починить реальные cause'ы.
2. Заменить milestone-email coroutine на `await` или `asyncio.run_until_complete`.
3. Заменить `datetime.utcnow()` во всех callers.
4. Написать regression test для milestone email (с mock SMTP, который проверяет вызов).

**Почему опасно для Кирилла:**
Если milestone-email не уходит, родитель не получит уведомления, что Кирилл достиг milestone (5, 10, 20 попыток). Это критическая функция для родительского контроля.

---

## P1 — серьёзные проблемы (можно передавать после fix)

### P1-1 ⚠️ Полный backend suite не зелёный (timeout на 41%)

**Severity:** P1 (CI gate ненадёжен)
**Effort:** M (3-5 дней — рефактор на per-file groups)

**Доказательство:** `AI-TUTOR-AUDIT-CURRENT-2026-08-23.md` §2.

- Полный `tests/test_sprint*.py` бандл в audit-сессии **завершается по timeout** примерно на 41% (exit 124).
- В status-сессии (current HEAD) — 637 passed за 177s. Это значит, что коммиты S1-S8 частично пофиксили timeout.
- Нужен стабильный baseline: каждый test file должен завершаться < 5 мин или явно группироваться.

**Что делать:**
1. Запустить `pytest --collect-only` и посмотреть список файлов.
2. Разбить на groups: `tests/test_group1_*.py ... tests/test_groupN_*.py`.
3. Каждую группу запускать с разным db (или tmp) чтобы избежать state leak.
4. На CI — параллельно (`pytest -n 4`).

---

### P1-2 ⚠️ CSRF не закрыт (Sprint 11 F2.2 — LIKELY UNFIXED)

**Severity:** P1 (security, реальный риск)
**Effort:** M (1-2 дня)

**Доказательство:** Sprint 11 audit F2.2 — `auth/security.py` и `auth/router.py` не содержат CSRF-middleware.

**Что нужно:**
- SameSite=Strict для auth cookies (сейчас Lax — уязвимо для GET-based CSRF).
- ИЛИ double-submit cookie pattern.
- ИЛИ проверка `Origin`/`Referer` для state-changing endpoints.

**Где подтвердить:**
- `apps/backend/app/auth/security.py` — параметры cookies.
- `apps/backend/app/main.py` — middleware list.
- `apps/backend/app/auth/router.py` — endpoints POST/PUT/DELETE.

**Почему опасно для Кирилла:**
LAN-сеть школы содержит много устройств. CSRF позволяет получить доступ к parent-dashboard без логина (если parent залогинен в той же сети).

---

### P1-3 ⚠️ PII leak (child.email)

**Severity:** P1 (privacy)
**Effort:** S (1-2 ч)

**Где:**
- `GET /api/v1/parents/children` — возвращает `email` ребёнка.
- `GET /api/v1/parents/students/{id}/dashboard` — может содержать `child_overview.email`.
- `child_dashboard.student.email`.

**Что делать:**
- В schemas явно удалить `email` поле из parent-scoped responses.
- Тест `test_parent_api_no_email_leak` — assert что response не содержит `@`.

---

### P1-4 ⚠️ Manual smoke никогда не был выполнен реально

**Severity:** P1 (marketing claim не подтверждён)
**Effort:** M (1 день на реальный smoke + документ)

**Доказательство:**
- `data/textbooks/7-class/evidence.json` имеет `manual_smoke_ready=true` для ВСЕХ 16 предметов.
- При том что `AI-TUTOR-CURRENT-STATUS.md` §3 явно говорит: «`manual_smoke_ready=true` НЕ подменяется автоматически — остаётся `false` чесно».
- → Никакого реального smoke не было.

**Что делать:**
- Кирилл + родитель делают **реальную сессию** (Sprint P5 в `06-sprints.md`).
- Результат — список реальных багов с приоритетами.
- Manual_smoke пересматривается по факту, не по отчёту.

---

### P1-5 ⚠️ License review не выполнен

**Severity:** P1 (legal risk)
**Effort:** L (юрист + manual, 2-3 недели)

**Доказательство:**
- `textbook-manifest.csv` имеет 20 строк с `license_decision=needs_review`.
- Это значит: тексты могут быть непригодны для распространения.

**Что делать:**
- Юридический review каждого учебника (PDF) с определением источника.
- Часть книг могут быть в публичном доступе (ФГОС-УМК с открытыми лицензиями).
- Часть — нет. Для них — отключить pilot_visible=true, оставить teacher-readable.

---

### P1-6 ⚠️ Image-only PDF без OCR (5 предметов)

**Severity:** P1 (контент не индексируется)
**Effort:** L (OCR pipeline + manual QA)

**Какие:**
- `04-istoriya-rossii-07-2015.pdf`
- `05-vseobshchaya-istoriya-07-2012.pdf`
- `11-informatika-07-bosova-2023.pdf`
- `12-obshchestvoznanie-07-bogolyubov-2023.pdf`
- `13-himiya-07-gabrielyan-2017.pdf`

**Что нужно:**
- Production Dockerfile с tesseract-ocr + tesseract-ocr-rus + tesseract-ocr-eng (отсутствует на проде по audit 2026-08-22).
- Визуальная проверка OCR (reproductions, chemical formulas, maps).
- Confidence threshold per page.

---

### P1-7 ⚠️ RAG retrieval quality низкая для all-subjects pilot

**Severity:** P1
**Effort:** L (отдельный sprint)

**Доказательство (audit 2026-08-22):**
- Probes `9/14`, recall@5 ~ `0.43`, MRR@5 ~ `0.32`.
- Это ниже production-ready threshold (~0.6+ recall@5).

**Что нужно:**
- Увеличить chunk quality (убрать хедеры, page numbers, repeat noise).
- Добавить bm25 reranking.
- Subject-specific embedding tuning.
- A/B test с разными threshold'ами.

---

### P1-8 ⚠️ Mobile viewport Playwright не запущен

**Severity:** P1 (UX на телефоне не проверен)
**Effort:** M (нужен CI runner с docker)

**Доказательство:** `AI-TUTOR-NEXT-PLAN-2026-08-23.md` T3.2 — deferred до CI.

**Что нужно:**
- Disposable CI runner (GitHub Actions или локальный LXC).
- Playwright mobile config (`page.setViewportSize({width: 375, height: 812})` для iPhone X).
- Screenshots: `/subjects`, `/subjects/[id]`, `/topics/[id]` — все три.

---

### P1-9 ⚠️ Permissions literacy: "Только для чтения" правило — нет UI indicator

**Severity:** P1
**Effort:** S (1-2 дня)

**Что нужно:**
- В `lesson`, в `topics/[id]` — если страница view-only (read-only source), показать явный badge «📖 режим чтения».
- Родителю в `/parent/dashboard/[id]` — заметный «view-only mode» badge.
- Кириллу — НЕ показывать admin/parent ссылки в nav (для principal of least privilege в UI).

---

## P2 — желательно до передачи

### P2-1 ⚠️ 91 CVE в transitive deps (starlette, cryptography, pillow, pypdf, multipart, transformers)

**Severity:** P2
**Effort:** L (major version upgrade pipeline, 1-2 недели)

**Что нужно:**
- `AI-TUTOR-STARLETTE-1X-MIGRATION-PLAN.md` (уже есть, 8-12ч оценка).
- Cryptography → новый release.
- Pillow → обновить до 11.x с проверкой OCR output.
- Pypdf → 5.x.
- Multipart — есть fixed версия.

**Почему не блокирует:** Проект используется только в домашней LAN, не в публичном интернете. CVE риск mitigated network isolation. Но если выставлять наружу — обязательно.

---

### P2-2 ⚠️ Duplicate lockfile warning при `npm run build`

**Severity:** P2 (warning, не блокер)
**Effort:** S (1 ч)

**Доказательство:** `AI-TUTOR-AUDIT-CURRENT-2026-08-23.md` §2 — Next.js warning о двух `package-lock.json`:
- `/root/package-lock.json`
- `/root/workspace/ai-tutor/apps/frontend/package-lock.json`

**Что нужно:** Удалить `/root/package-lock.json` или перенести в `apps/frontend/`.

---

### P2-3 ⚠️ Passlib `crypt` deprecation

**Severity:** P2
**Effort:** S (1-2 ч)

**Что нужно:** Заменить `passlib.context.CryptContext(schemes=['bcrypt'], deprecated='auto')` на прямой `bcrypt.hashpw()`. Или `filterwarnings('ignore', category=DeprecationWarning, module='passlib')` в pytest.ini.

---

### P2-4 ⚠️ Compose project name ≠ `aitutor`

**Severity:** P2 (не блокер, но тех. долг)
**Effort:** M (1 день)

**Доказательство:** Контейнеры называются `deploy-backend-1`, `deploy-frontend-1`, ..., а не `aitutor-backend-1`. Это из audit 2026-07-13: compose project name зафиксирован на `deploy` (а не `aitutor`).

**Что сделать:**
- `docker-compose.yml`: добавить `name: aitutor` в начало.
- Пересоздать контейнеры (один раз, риск downtime 5 мин).
- Обновить все ссылки в `deploy/*.sh` и `.github/workflows/`.

---

### P2-5 ⚠️ Deprecation warnings: passlib, jose.utcnow, Pydantic V1, sqlite3 adapter

**Severity:** P2
**Effort:** L (Pydantic V2 migration — отдельный sprint)

**Что нужно:**
- Pydantic V2 migration: `ConfigDict`, новые validators, model_validator.
- Passlib → bcrypt direct.
- python-jose уже обновлён до 3.5; остался только `utcnow` warning.

---

### P2-6 ⚠️ Branch dirty tree (10 файлов modified)

**Severity:** P2 (cosmetic + merge-conflict risk)
**Effort:** S (1 ч)

**Что нужно:**
- `git stash` или commit каждого изменения с описанием.
- Не оставлять 28 untracked файлов (textbook data, audit docs) — вынести в `docs/audit/`.

---

### P2-7 ⚠️ Offsite backup не настоящий (нет SMB)

**Severity:** P2 (data loss risk если LXC упадёт)
**Effort:** M (настройка SMB + ssh key + rsync cron)

**Доказательство:**
- `ai-tutor-backup-offsite.sh` пишет в `/var/backups/ai-tutor` на той же машине.
- Pilot Core добавил fail-closed check на разные mountpoint — если файлы на одном диске, cron exit non-zero.
- Реальный offsite (SMB 192.168.1.91) НЕ настроен.

---

### P2-8 ⚠️ CI/CD pipeline не активирован (GitHub remote отсутствует)

**Severity:** P2 (manual deploy каждый раз)
**Effort:** M (1-2 дня)

**Что нужно:**
- Создать remote на GitHub (Игорь откладывает).
- Перенести `~/.ssh/id_ed25519_cicd` в GitHub deploy keys.
- Workflow `deploy.yml` уже улучшен в Sprint 6.1.

---

## P3 — тех. долг / polish

### P3-1 — `tmp/` каталог занимает место и содержит мусор

**Severity:** P3
**Effort:** S (1 ч)

**Доказательство:**
- `/root/workspace/ai-tutor/tmp/` — десятки .py и .js скриптов без README.

**Что сделать:**
- Перенести валидные скрипты в `scripts/` или `deploy/`.
- `.gitignore` для tmp после очистки.

---

### P3-2 — Doc drift: ~50 docs/*.md от разных сессий

**Severity:** P3 (cognitive load для нового контрибьютора)
**Effort:** L (2-3 дня на merge / consolidation)

**Что сделать:**
- Свести все 3 audit (2026-08-22, 2026-08-23, текущий) в один `MASTER-AUDIT.md`.
- Актуализировать README + CURRENT-STATUS.
- Перенести WIP drafts в `docs/wip/`.

---

### P3-3 — Hardcoded passwords в git history

**Severity:** P3 (уже было, не воспроизводится)
**Effort:** L (blow up repo, переписать историю)

**Что сделать:** Не нужно, если сменили credentials на проде. Иначе — `git filter-repo` с rotate.

---

### P3-4 — `app/cgm/` модуль — Nightscout integration (read-only)

**Severity:** P3
**Effort:** S (документация)

**Что сделать:**
- Это experimental модуль, который трогать не надо.
- Но задокументировать в README, что это — отдельный pilot, не часть учебного product.

---

## Сводка по effort

| Sprint | Проблем | Effort | Кто делает |
|---|---|---|---|
| H1 (3 дня) | P0-1, P0-4, P0-5 (async warning milestones) | ~5 dev-days | backend |
| H2 (3 дня) | P0-2, P0-3, P1-3 | ~6 dev-days | full-stack |
| U1 (1 нед) | P1-9, P2-6 | ~5 dev-days | frontend |
| U2 (1 нед) | P2-3, P2-4, P2-5 (Pydantic V2 отдельный sprint) | ~10 dev-days | backend |
| C1 (1 нед) | P1-5, P1-6, P1-7 | ~7 dev-days | backend + юрист |
| Pilot (1 нед) | P1-4, P1-8 | ~5 dev-days (manual) | Игорь + Кирилл |
| Hard (2 нед) | P1-1, P1-2, P2-1, P2-7, P2-8 | ~14 dev-days | backend + infra |

**Итого до передачи Кириллу + родителю: ~6 недель (1 разработчик), либо 3 недели (2 разработчика параллельно).**
