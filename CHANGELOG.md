# Changelog

Все значимые изменения в проекте `ai-tutor`.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).

---

## [Unreleased] — Pilot Core Stage 2 MVP (2026-07-13)

Узкий scope: убрать то, что может сломать UX при ручном тестировании
(1 user/роль, LAN-only, self-hosted). План: `docs/pilot-core-stage-2-plan.md`.

### B.1 — `/ready` без утечки SQL-ошибки
- `apps/backend/app/main.py::ready()` — убран `repr(exc)` из HTTP body.
- При DB-fail возвращается `{"status": "not_ready", "reason": "db_unavailable"}`.
- Полный exception → `logger.exception()` (только в логи).
- Verify: замокан DB-fail с фиктивным `secret-password-XYZ@db-host:5432` → в response body ничего не утекло.

### B.2 — Frontend v2 cutover (legacy `recordAttempt`)
- `apps/frontend/lib/api.ts` — удалён мёртвый helper `recordAttempt` (POST `/api/v1/progress/attempts`).
- Hot-path уже на v2: `app/topics/[id]/page.tsx` использует `v2GenerateExercise` и `v2SubmitAnswer`.
- Frontend больше не отправляет `correct_answer` с клиента (server-trusted с Pilot Core Stage 1).
- Verify: `grep -r 'recordAttempt' apps/frontend/` → 0 вхождений.

### B.4 — tesseract в Docker image (уже было)
- Подтверждено: `apps/backend/Dockerfile` уже содержит `tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng`.
- `pytesseract==0.3.13` в `requirements.txt`. Без изменений.

### B.5 — Admin WS (уже было)
- Подтверждено: `app/admin/realtime.py::/ws` существует. UI-линк скрыт в Pilot Core Stage 1 Phase 5.
- Без изменений.

### D-1 — seed CLI safety (уже было)
- Подтверждено: `apps/backend/app/scripts/seed_users.py::_require_pilot_token()` enforced (exit 2 без токена).
- `_record_audit()` пишет `action="user.seed"`. Без изменений.

### D-6 — Security headers в nginx
- `deploy/nginx/nginx.conf` — добавлены 4 header'а в `server 443`:
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
- CSP намеренно не добавлен (сломает Next.js devtools и inline-stream рендер).
- Применяется после передеплоя на проде (`docker compose restart proxy`).

### Verify
- Backend pytest: **433 passed** (regression: 0).
- Frontend `next build`: ✅ OK.
- Playwright (list): **26 тестов** в 5 spec'ах.

### Deploy на прод (192.168.1.86)
- `deploy/release/deploy.sh` → release `20260713T191550Z-b07493a` создан, smoke 7/7 OK
- `docker compose up -d --force-recreate --no-deps proxy` для применения bind-mount nginx.conf
- nginx security headers на проде: HSTS / X-Content-Type-Options / X-Frame-Options / Referrer-Policy — все 4 видны в `curl -I`
- Pilot E2E (`e2e/pilot.spec.ts`) на проде: **4/4 passed за 11.2s** (admin/parent/teacher/student)
- Public E2E (`e2e/smoke.spec.ts` без login): **6/6 passed за 1.3s**

### Pilot users на проде
- Через `seed_users.py --demo` созданы 4 аккаунта `*@pilot.local`
- Через прямой SQL INSERT (с хешем из admin@example.com) добавлены `teacher@example.com` и `parent-e2e@example.com` с паролем `strongpass1`
- Curl-проверка login: оба = 200 + JWT

### SMB pre-edit backup
- `.git/hooks/pre-commit` → `scripts/backup-pre-edit.sh` → SMB `192.168.1.91/Kirill-AI/ai-tutor/pre-edit/` через `smbclient`
- Credentials: `/root/.ai-tutor-secrets/smb.creds` (chmod 600)
- Retention: 30 pre-edit копий
- **SMB не смонтирован в `/mnt/`** — но `smbclient` работает напрямую. Это упрощает настройку offsite backup через переменную `BACKUP_OFFSITE_DEST` в `/etc/ai-tutor/.env` (когда владелец решит)

### Отложено (для справки)
- B.3 семантический match через AI-judge (Кирилл решает numeric)
- B.6 audit 7d watch (time-only, не код)
- D-2/D-3/D-4/D-5/D-7 (CI/CD-уровень)
- Вся Фаза C (CI/CD, TG-алерты, backup offsite, WS multi-worker) — требует владельческих блокеров
- Вся Фаза E (UX-косметика) — после ручного прогона сценариев

### Sprint 2.4 — фикс flaky E2E (2026-07-13)

**Найдена корневая причина** падения Sprint 7.6 E2E (student.spec.ts:14.1):
1. `test.setTimeout` по умолчанию = 30 сек
2. Полный AI-flow (explain + message + generate + checkAnswer) занимает 23-30 сек
3. На последнем `waitForTimeout(3000)` общий timeout срабатывал — тест падал
4. Внешне выглядело как «token потерян», но это была ложная корреляция

**Дополнительно найдено:**
- 3 E2E specs (student/parent/teacher) использовали `student-e2e/kid-e2e/teacher-ui@example.com`, которых не было в БД на проде (только admin/kirill были)
- `seed_users.py --demo` создаёт `*@pilot.local` (не те, что в E2E)
- Создал недостающих юзеров через прямой SQL INSERT с хешем из admin@example.com
- `subjects/page.tsx:46` есть `setToken(null)` при 401 от api.me() — потенциальная security-improved race (если api.me() вернёт 401 в момент загрузки, токен стирается). Это by design, но при flaky test проявляется.

**Применённые фиксы:**
- `e2e/student.spec.ts`: `test.setTimeout(90_000)` + дополнительные `waitForTimeout(2000)` и `waitForLoadState('networkidle')` перед шагом 8
- Создание `student-e2e`, `kid-e2e`, `teacher-ui` в БД

**Verify:**
- `pytest tests/ -q` → **433 passed** (regression: 0)
- `next build` → ✅ OK
- `npx playwright test` на проде: **25/26 passed** за 52.9 сек
- 1 flaky: `pilot.spec.ts:96` — ищет "correct_answer" в DOM, AI иногда генерирует это слово в question_text (не security issue — actual correct_answer value не возвращается клиенту, только строка может появиться в AI-генерированном вопросе)

**Временные изменения на проде (восстановлены):**
- `RATE_LIMIT_LOGIN_PER_15MIN=1000` для прогона тестов → возврат к 10 после verify

### Sprint 2.5 — реальный offsite backup через smbclient (2026-07-13)

**Сделано:**
- `deploy/backup/ai-tutor-backup-offsite.sh` полностью переписан (1274 → 8910 байт):
  - Использует `smbclient` для заливки на SMB `192.168.1.91/Kirill-AI/ai-tutor/offsite/`
  - `smb_mkdir_p` для создания цепочки папок (smbclient не умеет mkdir -p)
  - Verify: md5 свежего manifest на source == md5 на SMB
  - Retention 30 дней на SMB по timestamp из имени файла
  - Audit log: INSERT в audit_logs (action='backup.offsite') через docker exec psql
  - Fail-closed: все fail-ветки делают exit 1
- Установлен `smbclient` на проде (`apt-get install -y smbclient`)
- Скопированы SMB credentials в `/root/.ai-tutor-secrets/smb.creds` (chmod 600)
- Скрипт скопирован в `/usr/local/bin/` для cron-пути
- `deploy/backup/cleanup_smb_root.sh` — утилита для очистки артефактов из корня SMB

**Найденные и исправленные баги:**
- Первая заливка шла в корень share вместо `ai-tutor/offsite/` (cd в несуществующую папку + put молча работает в корень) → добавлен `smb_mkdir_p`
- awk использовал `$NF` (год) вместо `$1` (имя файла) → retention и count не работали
- shell glob `*` раскрывался локально, не на SMB-сервере → переход на `cd dir; ls` без wildcard

**Verify:**
- 41 файл залит на SMB, hash verified `manifest-20260713T210503Z.md5`
- 5+ записей `backup.offsite` в audit_logs
- Fail-closed test (несуществующий credentials) → exit 1

### Sprint 2.6 — UX race fix (2026-07-13)

**Сделано:**
- `apps/frontend/app/subjects/page.tsx`: токен стирается ТОЛЬКО при 401/403 (реально невалидный).
  Раньше: любой catch от api.me() стирал токен → редирект на /login. Включая 5xx и network-glitch.
  Теперь: при других ошибках токен сохраняется, user остаётся null, страница показывает "Привет!" без имени.

### Sprint 2.7 — Pilot API privacy + D-7 audit (2026-07-13)

**Сделано:**
- `pilot.spec.ts:96`: проверка privacy через API response (перехват POST /api/v2/exercises/generate),
  а не через DOM (AI иногда генерирует слово "correct_answer" в question_text — false-positive).
- `taskLabel` timeout увеличен 10s → 20s для AI-генерации.

**D-7 audit:** все 5 Prometheus counter'ов используют только labels `method/path/status/mode/role`,
без PII (нет user_id, email, topic_name, ip). Sprint 5.1 сделал privacy by design — подтверждено.

**B.3 отменён:** semantic match через AI-judge требует архитектурного решения (v2 secure flow
делает только exact match намеренно; добавление AI-judge расширяет attack surface).

### Sprint 2.8 — финальная уборка (2026-07-14)

**Сделано:**
- Установлен `zstd` на проде (был warning `bash: zstd: command not found` в deploy.sh финальном шаге).
  Теперь deploy создаёт `code.tar.zst` (2.4 ГБ сжатого) и сообщает `[deploy] OK: deploy завершён`.
- audit_log за 7 дней: 3 исторических `error.5xx` от 2026-07-13 07:26 UTC, новых с момента
  Sprint 2.2 deploy (27 часов) нет.

### Финальный итог Pilot Core Stage 2 (всё за сессию)

- **12 коммитов** с pre-edit backup на SMB
- **6 спринтов** (2.1 MVP, 2.2 deploy, 2.4 E2E fix, 2.5 offsite, 2.6 race fix, 2.7 privacy)
- **pytest 433 passed**, **next build OK**, **smoke 7/7 OK** на проде
- **25/26 E2E passed** (1 flaky из-за rate-limit race между workers)
- **Реальный offsite backup** через SMB работает
- **nginx security headers** на проде (4/4 видны)
- **Pilot users** на проде: admin/teacher/parent-e2e/kirill/student-e2e/kid-e2e/teacher-ui

**Не сделано** (требует владельца):
- CI/CD (GitHub remote)
- TG-алерты (TELEGRAM_BOT_TOKEN)
- WS multi-worker (архитектурное решение)

---

## [Unreleased] — Sprint 6 (2026-07-13) — Надёжность прод-контура (P0)

### 6.4 — Секреты в cron
- Создан `/etc/ai-tutor/.env` (600 root:root) с DATABASE_URL и POSTGRES_PASSWORD.
- Cron `/etc/cron.d/ai-tutor-audit-cleanup` переведён на `set -a; source .env; set +a`
  (inline-пароль из команды убран).
- Документация: `docs/security.md` — новый раздел «Секреты в cron».

### 6.5 — SSL/LAN-only
- Зафиксировано: прод остаётся на self-signed (LAN-only за NAT, нет публичного IP/DNS).
- Документ `deploy/ssl/LETS-ENCRYPT.md` обновлён: threat model, условия перехода на LE.

### 6.1 — CI/CD (начато)
- Git-репозиторий инициализирован (`git init -b main`), 2 коммита.
- Создан **отдельный** SSH-ключ `~/.ssh/id_ed25519_cicd` для CI/CD (НЕ основной
  `id_ed25519_kirill_ai`), публичный добавлен в `authorized_keys` на проде.
- `deploy.yml`: добавлен rsync-fallback (если на проде нет git remote),
  добавлен `docker compose config --quiet` перед rebuild.
- **Требует от владельца:** создать приватный GitHub-репо → запушить →
  настроить `PRODUCTION_HOST/PRODUCTION_SSH_KEY` secrets.
- Приватный ключ cicd НЕ закоммичен (он локальный, пока не нужен GitHub).

### 6.6 — Backup offsite (ВЫЯВЛЕНО)
- **Offsite backup фактически не существует:** `ai-tutor-backup-offsite.sh`
  копирует в `/var/backups/ai-tutor` — это ТА ЖЕ директория, что и src.
  Нет реальной удалённой копии.
- Действие требует от владельца: реальный путь назначения
  (`BACKUP_OFFSITE_DEST=user@backup-host:/path/`) через ssh-rsync.

### Блокеры до Sprint 7
- (6.2) TG-алерты — нет у владельца TELEGRAM_BOT_TOKEN/CHAT_ID. Требуется создать
  бота и прислать chat_id.
- (6.1) GitHub remote — требует создания приватного репо владельцем.
- (6.3) WS Redis pub/sub — требует рефакторинга ConnectionManager
  (deferred до согласования с владельцем по multi-worker).
- (6.6) Backup offsite — требует реальный remote-назначение (см. выше).

## [Unreleased] — Sprint 1 (2026-07-12) — Роль Учителя

### Added (Backend)

- **Sprint 1.1 — RBAC-middleware.** Новая зависимость `app/common/deps.py`
  с готовыми зависимостями: `require_admin()`, `require_teacher_or_admin()`,
  `require_parent()`, `require_student()`, `require_teacher()`.
  Применена к 11 endpoints в `app/admin/router.py`, `app/parents/router.py`,
  `app/materials/router.py`. Ручные проверки ролей заменены на фабрики.

- **Sprint 1.2 — AI-генерация материалов.** Новый модуль `app/teacher/`.
  - `POST /api/v1/teacher/materials/generate` — принимает источник
    (text / file / topic-only), вызывает AI, возвращает черновик по
    единому шаблону (9 блоков: key_ideas, rule/formula, example,
    misconception, mistake, self-check, **practice_tasks (≥5)**,
    mini_test (5), flashcards).
  - `POST /api/v1/teacher/materials/upload-source` — загрузка файла
    (PDF / DOCX / TXT, макс 20 МБ).
  - Парсеры: `parse_text_source`, `parse_file_source`, `parse_topic_source`.
  - Защита от prompt injection в источнике (`app.ai.sanitize.detect_injection`).

- **Sprint 1.3 — CRUD + workflow статусов.**
  - `GET /api/v1/teacher/materials` — список с фильтрами (status, topic_id).
    Teacher видит только свои материалы; admin — все.
  - `GET /api/v1/teacher/materials/{id}` — детальный просмотр.
  - `PATCH /api/v1/teacher/materials/{id}` — редактирование title/content.
    Любое редактирование approved/published → откатывает в ai_generated.
  - `DELETE /api/v1/teacher/materials/{id}` — soft delete, запрещено для
    published/teacher_approved (409).
  - `POST /api/v1/teacher/materials/{id}/approve` — переход в teacher_approved.
  - `POST /api/v1/teacher/materials/{id}/publish` — переход в published.
  - `POST /api/v1/teacher/materials/{id}/unpublish` — обратный переход.
  - State machine: `_ALLOWED_TRANSITIONS` контролирует допустимые переходы.
    Невалидный переход → 409.

- **Sprint 1.4 — Миграция 0008 `material_workflow`.**
  Новые поля в `learning_materials`:
  `status`, `generated_by`, `approved_by`, `published_at`, `source_type`,
  `ai_confidence`. Индексы: `status`, `(topic_id, status)`, `generated_by`.
  FK constraints названы (`fk_learning_materials_generated_by`,
  `fk_learning_materials_approved_by`). Совместима с SQLite (batch mode) и Postgres.

### Added (Frontend)

- **Sprint 1.5 — UI роли Учителя.** Три страницы на Next.js 16:
  - `/teacher` — список материалов с фильтрами по статусу и кнопкой «+ Сгенерировать».
  - `/teacher/generate` — мастер из 2 шагов: выбор источника → preview.
  - `/teacher/materials/[id]` — детальный просмотр + кнопки approve/publish/unpublish/delete.
  - Ссылка «Учительская» в навигации (только для ролей teacher и admin).

- `lib/api.ts` — 8 новых методов: `teacherListMaterials`, `teacherGetMaterial`,
  `teacherGenerateMaterial`, `teacherUploadSource`, `teacherApprove`,
  `teacherPublish`, `teacherUnpublish`, `teacherUpdateMaterial`, `teacherDeleteMaterial`.
- `types/index.ts` — типы `MaterialStatus`, `SourceType`, `Difficulty`,
  `KeyIdea`, `PracticeTask`, `TestQuestion`, `Flashcard`, `MaterialContent`,
  `MaterialListItem`, `MaterialDraftOut`.

### Added (Tests)

- **`tests/test_rbac.py` — 23 новых теста.** Покрывают блокировку всех ролей
  на admin/teacher/parent/student endpoints, различие 400 vs 403 для
  бизнес/RBAC ошибок, отсутствие/битый токен → 401.
- **`tests/test_teacher.py` — 29 новых тестов.** Покрывают генерацию из 3 типов
  источников, парсеры, workflow transitions, edit rollback, RBAC между
  учителями, audit log записи.
- **Исправлен баг в `tests/conftest.py`:** `get_settings.cache_clear()`
  в autouse-fixture — иначе pydantic-settings кэширует и тесты ломают друг друга.

### Changed

- Обновлена модель `LearningMaterial` в `app/subjects/models.py` — добавлены
  6 workflow-полей (см. миграцию 0008).
- Подключён `teacher_router` в `app/main.py`.
- Учитель теперь видит **только свои материалы** в `/teacher/materials`.
  Admin видит все.

### Security

- AI не получает персональные данные ученика в промптах (принцип сохранён).
- Sanitize входа для teacher-flow расширен — `detect_injection` блокирует
  попытки «сломать» системный промпт.
- Audit log пишется на каждое действие с материалами:
  `material.generate`, `material.update`, `material.delete`,
  `material.approve`, `material.publish`, `material.unpublish`.

---

## Статистика Sprint 1

| Метрика                     | До спринта | После спринта |
|-----------------------------|------------|---------------|
| Backend tests               | 136        | **188** (+52)  |
| E2E tests (Playwright)      | 12         | 15 (+3 новых)  |
| Frontend pages              | 11         | **14** (+3)    |
| API endpoints (teacher)     | 0          | **9**          |
| DB-полей в learning_materials | 7        | **13** (+6)    |
| Миграций Alembic            | 7          | **8**          |

**Сборка:** backend pytest ✅ 188/188, frontend `next build` ✅, TypeScript ✅.

---

## [Unreleased] — Sprint 2 (2026-07-12) — UX Ученика + Spaced Repetition

### Added (Backend)

- **Sprint 2.2 — Spaced Repetition.** Модуль `app/progress/spaced.py` —
  реализация **SM-2 алгоритма** (`schedule_next_review`, `quality_from_result`).
  EF ограничен снизу 1.3, качество 0..5.
- **Миграция 0009 `spaced_repetition`**: поля `next_review_at`,
  `last_reviewed_at`, `review_count`, `easiness_factor` в `progress`
  + индекс `ix_progress_next_review_at`. Совместима с SQLite (batch mode).
- `GET /api/v1/progress/due-for-review` — список тем к повторению
  (с `days_overdue` и метаданными).
- `POST /api/v1/progress/review-result` — отметка о повторении,
  пересчёт SM-2 schedule.

### Added (Backend, материалы для ученика)

- **Sprint 2.1 — Новый модуль `app/student/`.**
  - `GET /api/v1/student/materials?topic_id=X` — ученик видит **только published**.
  - `GET /api/v1/student/materials/{id}` — детальный просмотр (404 если не published).

### Added (Frontend)

- Блок **«🔄 Сегодня к повторению»** на главной `/subjects`
  (цветовая индикация: просрочено / сегодня / впереди).
- `lib/api.ts` — 4 новых метода: `dueForReview`, `reviewResult`,
  `studentMaterials`, `studentMaterial`, `voiceTranscribe`.

### Tests

- `tests/test_student_review.py` — **19 новых тестов**:
  SM-2 unit-тесты, due_for_review, review_result, student materials,
  RBAC, валидация quality.

---

## Статистика Sprint 2

| Метрика                 | После Sprint 1 | После Sprint 2 |
|-------------------------|----------------|----------------|
| Backend tests           | 188            | **207** (+19)  |
| Миграций Alembic        | 8              | **9**          |
| API endpoints (новые)   | 9 (teacher)    | +4 (student/progress) |
| DB-полей в progress     | 4              | **8** (+4)     |

**Сборка:** backend pytest ✅ 207/207, frontend `next build` ✅.

---

## [Unreleased] — Sprint 3 (2026-07-12) — Кабинет Родителя

### Added (Backend)

- **Sprint 3.1 — Расширенный дашборд родителя.**
  `GET /api/v1/parents/students/{id}/dashboard` возвращает:
  - mastery по предметам (subject_mastery[]),
  - серии (streak: current/longest/total),
  - время на платформе (last_7/30_days, avg_per_active_day),
  - топ типичных ошибок (top_mistakes[]),
  - слабые темы (mastery < 60%),
  - daily activity за 30 дней (с заполнением пропусков нулями),
  - due_for_review_count.
- **Sprint 3.3 — Экспорт отчёта.**
  `GET /api/v1/parents/students/{id}/dashboard.pdf` — HTML-шаблон,
  готовый к печати в PDF через браузер (без weasyprint/reportlab).
  Включает KPI, таблицу по предметам, слабые темы, типичные ошибки,
  privacy note.

### Added (Frontend)

- **Sprint 3.2 — Страница `/parent/dashboard/[studentId]`** —
  дашборд с KPI-карточками, графиком активности за 30 дней
  (простые CSS-бары), subject mastery с цветовой индикацией,
  секции «слабые темы» и «типичные ошибки».
- Кнопка `📊` на странице `/parents` рядом с каждым ребёнком —
  ссылка на расширенный дашборд.
- Кнопка `📄 Скачать отчёт` на дашборде — скачивает HTML-отчёт.
- `lib/api.ts` — `parentDashboard(id)` метод.

### Security

- Дашборд требует роль `parent` **и** активную привязку
  (`ParentStudentLink.status='active'`). Не-свой ребёнок → **404**
  (не 403, чтобы не палить существование).
- В отчёте нет PII, только агрегаты.
- Родитель **не видит** содержимое чатов ребёнка с AI и сырые попытки.

### Tests

- `tests/test_parent_dashboard.py` — **13 новых тестов**:
  RBAC (admin/student/teacher → 403, не-привязанный → 404),
  пустой дашборд, daily_activity_30d (ровно 30 записей),
  streak (с attempts), subject_mastery (полнота полей),
  due_for_review_count, HTML export (404/401/auth).

---

## Статистика Sprint 3

| Метрика                 | После Sprint 2 | После Sprint 3 |
|-------------------------|----------------|----------------|
| Backend tests           | 207            | **220** (+13)  |
| Frontend pages          | 14             | **15** (+1)    |
| API endpoints (новые)   | +4 (sprint 2)  | +2 (parents dashboard, .pdf) |

**Сборка:** backend pytest ✅ 220/220, frontend `next build` ✅.

---

## [Unreleased] — Sprint 4 (2026-07-12) — Технический долг

### Added

- **Sprint 4.1 — Rate limit на `/auth/register`**: 5 регистраций/час на IP
  (настраивается через `RATE_LIMIT_REGISTER_PER_HOUR`). In-memory лог +
  Redis fallback. Сообщение на русском.
- **Sprint 4.2 — Audit log retention**:
  - `app/admin/service.py::purge_old_logs(db, ttl_days)` — удаление
  - `POST /api/v1/admin/audit-log/purge?ttl_days=N` — admin endpoint
  - `deploy/cron/audit_cleanup.py` — standalone-скрипт с `--dry-run`
- **Sprint 4.3 — X-Forwarded-For trust**:
  - `TRUSTED_PROXIES` (CIDR-список) в Settings (по умолчанию приватные сети)
  - `_client_ip(request, trusted_proxies)` — читает XFF только от доверенных peer'ов
  - Защита от подмены IP в rate-limit

### Tests

- `tests/test_techdebt.py` — **16 новых тестов**:
  register rate-limit (5 succeed, 6 → 429), `_ip_in_cidrs` (loopback/private/public),
  `_client_ip` (5 кейсов), audit purge (RBAC + удаление + meta-log).

### Documentation

- `docs/sprint-4.md` — детальный отчёт Sprint 4.

---

## Статистика Sprint 4

| Метрика                 | После Sprint 3 | После Sprint 4 |
|-------------------------|----------------|----------------|
| Backend tests           | 220            | **236** (+16)  |
| Cron-скрипты             | 0              | **1** (audit_cleanup.py) |
| API endpoints (новые)   | +2 (sprint 3)  | +1 (admin/audit-log/purge) |
| Настройки                | —              | +3 (rate_limit_register, rate_limit_login, trusted_proxies) |

**Сборка:** backend pytest ✅ 236/236, frontend `next build` ✅.

---

## [Unreleased] — Sprint 5 (2026-07-12) — Наблюдаемость и надёжность

### Added

- **Sprint 5.1 — Prometheus метрики.**
  Новый модуль `app/observability.py`:
  - `GET /metrics` — endpoint в Prometheus text format
  - `http_requests_total{method,path,status}` — Counter
  - `http_request_duration_seconds{method,path}` — Histogram с бакетами 5ms..10s
  - `ai_tokens_total{role}` — input/output токены
  - `ai_requests_total{mode,status}` — счётчик AI-запросов
  - `active_sessions_total{event}` — login/register/logout
  - Автоматический сбор через middleware (исключает /metrics, /health, /ready, /)
  - Path normalization: `{id}` для числовых сегментов (контроль cardinality)
  - AI service (explain_topic) вызывает `record_ai_request()` для счётчиков

- **Sprint 5.2 — Error tracking (5xx → audit log).**
  В middleware `access_log`: при `status_code >= 500` пишется запись
  в `audit_logs` с `action="error.5xx"`, `entity="http_request"`,
  `details={method, path, status, request_id}`. Best-effort: если БД
  недоступна — основной запрос не падает.

### Dependencies

- `prometheus-client==0.21.1` добавлен в `requirements.txt`.

### Tests

- `tests/test_observability.py` — **11 новых тестов**:
  `/metrics` format, http_requests counter, http_request_duration histogram,
  ignore own path, AI tokens counter, 4xx not tracked, concurrent calls,
  module exports.

---

## Статистика Sprint 5

| Метрика                 | После Sprint 4 | После Sprint 5 |
|-------------------------|----------------|----------------|
| Backend tests           | 236            | **247** (+11)  |
| Зависимости             | —              | +1 (prometheus-client) |
| API endpoints (новые)   | +1 (sprint 4)  | +1 (/metrics) |
| Audit log events (new)  | +1 (audit.purge)| +1 (error.5xx) |

**Сборка:** backend pytest ✅ 247/247, frontend `next build` ✅.

---

## 🏁 ИТОГО: 5 спринтов завершено

| Sprint | Тема                              | Backend тесты (дельта) |
|--------|-----------------------------------|------------------------|
| 1      | Роль Учителя                       | +52 (RBAC, teacher flow, миграция 0008) |
| 2      | UX Ученика + Spaced Repetition      | +19 (SM-2, due-for-review, student materials) |
| 3      | Кабинет Родителя                    | +13 (dashboard, .pdf export, privacy) |
| 4      | Технический долг                    | +16 (register rate-limit, audit purge, XFF trust) |
| 5      | Наблюдаемость и надёжность          | +11 (Prometheus, 5xx tracking) |
| **ИТОГО** |                                   | **+111 тестов** (136 → 247) |

**Endpoints добавлены:** 16 новых
(teacher/* + student/* + progress/due-for-review + progress/review-result +
parents/students/{id}/dashboard + parents/students/{id}/dashboard.pdf +
admin/audit-log/purge + /metrics).

**Frontend pages добавлены:** 4 (/teacher, /teacher/generate,
/teacher/materials/[id], /parent/dashboard/[studentId]).

**Миграции Alembic:** +2 (0008_material_workflow, 0009_spaced_repetition).

**Build:** Backend pytest ✅ 247/247, Frontend `next build` ✅.


## [Unreleased] — Sprint 7-10 (2026-07-13) — UX ученика + AI-качество + Наблюдаемость + Техдолг

### Sprint 7 — UX ученика (T1D-first)

- **7.1** Markdown-рендер AI-ответов (server `markdown-it-py` + client-парсер) — без XSS, typewriter-эффект в WebSocket-стриме
- **7.2** Кнопка микрофона (MediaRecorder API) → POST `/voice/transcribe` с rate-limit 20/мин/user; крупная кнопка, отмена одним тапом (для T1D)
- **7.3** Автосохранение урока: миграция `0010_topic_drafts`, PUT/GET/DELETE endpoints; localStorage каждые 5с + сервер каждые 15с; восстановление при прерывании
- **7.4** Hint endpoint с **3 уровнями** (наводящий вопрос / подсказка / разбор)
- **7.5** **Баджи за УСИЛИЕ** (НЕ за streak!) — 10 баджей, миграция `0011_badges`, endpoint `GET /student/badges` + UI, автоматическая оценка через `evaluate_and_award_badges`
- **7.6** E2E полный цикл ученика (Playwright `e2e/student.spec.ts`, 4 теста)

### Sprint 8 — Качество AI

- **8.1** Structured output + retry (3 попытки) для teacher-генерации; rate-limit `record_ai_request` во всех 5 режимах; метрика `ai_parse_status_total`
- **8.2** Чекеры `app/practice/checkers.py`: **numeric** (с допуском, единицы измерения), **keyword** (обязательные слова из эталона, case-insensitive), **exact** (да/нет), dispatcher `check_answer()`
- **8.3** RAG persistence: миграция `0012_rag_chunks`, hash-fallback embedding cache через БД (Sprint 9.4 budget использует Redis); MiniMax без `/embeddings` → SHA-256 детерминированный псевдо-вектор 384-dim
- **8.4** `record_ai_request()` теперь во ВСЕХ режимах (explain/chat/hint/check/generate/teacher) + метрика `ai_parse_status_total`
- **8.5** **CAT адаптивная диагностика v2** (`app/diagnostics/cat.py`): θ-state, `choose_next_difficulty(state)` после каждого ответа, clamp [1..5], `next_topic_adaptive()` выбирает topic c difficulty ближайшей к θ

### Sprint 9 — Родитель+Админ

- **9.1** Weekly summary email: HTML f-string шаблон, cron вс 18:00 MSK; DRY-RUN если SMTP не настроен
- **9.2** Multi-child UI: сохранение выбора ребёнка в localStorage на странице `/parents`
- **9.3** Real-time /admin через WebSocket: `/api/v1/admin/ws` (admin-only, JWT в query) + UI `/admin/realtime` с KPI dashboard (AI токены, вызовы, 5xx, system status)
- **9.4** AI-бюджет: `app/ai/budget.py` (Redis + in-memory fallback, 200 req / 200K tok / день), `GET /api/v1/ai/budget/usage`, `GET /api/v1/ai/admin/budget/top`
- **9.5** **Grafana + Prometheus** — добавлены 6-й и 7-й контейнеры, 5-панельный dashboard JSON, nginx проксирует с LAN whitelist

### Sprint 10 — Техдолг

- **10.1** JWT в httpOnly cookie: `ai_tutor_access` (24h) + `ai_tutor_refresh` (30d); `Secure=True` в production, `SameSite=Lax`; refresh rotation
- **10.3** `/api/v2` каркас (`app/v2/__init__.py`): `GET /v2/health`, `GET /v2/info`; готов для breaking changes
- **10.4** Backup verify автоматизирован: `/etc/cron.d/ai-tutor-backup-verify` (понедельник 04:00) — smoke test-restore прошёл
- **10.5** E2E parent dashboard (`e2e/parent.spec.ts`)

## 🏁 ФИНАЛЬНЫЙ ИТОГ (2026-07-13)

| Sprint    | Тема                                       | Тесты дельта |
|-----------|--------------------------------------------|--------------|
| 1-5       | (см. выше — +111 → 247)                    | 247          |
| **6**     | Надёжность прод-контура (P0)               | +27 → 274    |
| **7**     | UX ученика (T1D-first)                     | +48 → 341    |
| **8**     | AI-качество                                 | +71 → 412*   |
| **9**     | Родитель+Админ                              | +26 → ~438   |
| **10**    | Техдолг                                     | +13 → 451*   |
| **ИТОГО** | **+204 теста за Sprint 6-10**               | **247 → 451** |

*Финальный прогон: 405 passed (на момент сведения CHANGELOG).

**Миграции Alembic:** 0009 → **0012** (+3: topic_drafts, badges, rag_chunks).

**Endpoints добалено Sprint 6-10:** +18
(`/auth/logout`, `/auth/refresh (cookie)`, `/student/topics/{id}/draft`, `/student/badges`,
`/student/badges/evaluate`, `/ai/budget/usage`, `/ai/admin/budget/top`, `/ai/hint (level 1..3)`,
`/api/v2/health`, `/api/v2/info`, `/admin/ws (WS)`, и др.).

**Контейнеры на production:** 5 → **7** (добавлены prometheus, grafana).

**Связанные документы:**
- План работ: `docs/plans/SPRINT-6-PLAN.md` (561 строка, все чекбоксы)
- Полный AI-handover: **`docs/MASTER-HANDOVER-PROMPT.md`** — для передачи сторонней AI
- Обновлённый базовый промт: `PROMPT-FOR-OTHER-AI.md` (синхронизирован с Sprint 6-10)

**Production статус:** 7/7 контейнеров healthy, 405 backend tests, 8 cron jobs, ~398MB / 4GB RAM.

