# Changelog

Все значимые изменения в проекте `ai-tutor`.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).

---

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

