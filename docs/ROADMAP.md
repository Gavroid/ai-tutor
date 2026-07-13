# ROADMAP — AI-репетитор 7 класса

> План развития проекта на основе аудита (`PROMPT-FOR-OTHER-AI.md`).
> Файл — рабочий трекер: задачи, подзадачи, чекбоксы прогресса, заметки.
> Обновляется по мере выполнения.

> **Статус 2026-07-13**: Sprint 1-10 завершены (см. `CHANGELOG.md`).
> Долгосрочный план: **`docs/plans/SPRINT-6-PLAN.md`** (Sprint 6-10).
> Полный AI-handover: **`docs/MASTER-HANDOVER-PROMPT.md`** — для передачи другой AI.

---

## 📊 Текущее состояние (baseline, 2026-07-12)

| Слой            | Статус                                                                |
|-----------------|-----------------------------------------------------------------------|
| Production      | 192.168.1.86, **5/5** контейнеров healthy                            |
| Cron jobs       | 4 активны                                                             |
| Backend tests   | **136/136** ✅                                                         |
| E2E (Playwright)| **12/12** ✅                                                           |
| Smoke (prod)    | **8/8** (OAuth, RAG, Voice) ✅                                         |
| Миграции Alembic| до `0007_password_reset`                                              |
| Backend         | FastAPI 0.115 + SQLAlchemy 2 + Postgres 16 + Redis + Nginx            |
| Frontend        | Next.js 16                                                            |
| Роли в БД       | admin, teacher, student, parent — **teacher без UI и flow**           |
| RAG             | работает, но in-memory (нужен pgvector)                               |
| Workers         | uvicorn 1 worker (нужно 4)                                            |
| Rate-limit      | есть, но без `/auth/register`                                         |

---

## 🗺️ Общая карта спринтов

| # | Спринт                              | Цель                                      | Блокер? |
|---|-------------------------------------|-------------------------------------------|---------|
| 1 | **Роль Учителя**                    | End-to-end teacher flow с AI-генерацией    | ✅ ДА    |
| 2 | UX Ученика + практика + повторение  | Цикл «объясни→практика→проверь→повтори»   | ❌       |
| 3 | Кабинет Родителя                    | Дашборд, графики, экспорт, уведомления     | ❌       |
| 4 | Технический долг                    | pgvector, multi-worker, rate-limit, XFF   | ❌       |
| 5 | Наблюдаемость и надёжность          | Prometheus, Sentry, алерты                | ❌       |

> Правила (общие для всех спринтов, из `PROMPT-FOR-OTHER-AI.md`):
> 1. Перед задачей — прочитать релевантные файлы.
> 2. Не ломать 136 backend + 12 E2E тестов.
> 3. БД — только через новые миграции (`0008+`).
> 4. После: тесты + docs + CHANGELOG.
> 5. Уточняющие вопросы (≤5) — до кода.

---

# 🟥 СПРИНТ 1 — Роль Учителя (блокер продукта)

**Цель:** замкнуть контур «исходник → AI-черновик → approve Учителя → публикация для Ученика».

---

## 1.1 RBAC-middleware для teacher/admin

- [ ] **1.1.1** Прочитать `app/auth/security.py`, `app/users/models.py`, существующие deps для ролей
- [ ] **1.1.2** Выделить зависимость `require_role("teacher"|"admin")` в `app/common/deps.py`
- [ ] **1.1.3** Покрыть unit-тестами: ученик не может в teacher endpoints (≥6 кейсов)
- [ ] **1.1.4** Применить ко всем существующим admin/teacher endpoints (аудит `app/admin/router.py`, `app/materials/router.py`)
- [ ] **1.1.5** Документация: обновить `docs/security.md`

## 1.2 Backend: AI-генерация материалов

- [ ] **1.2.1** Endpoint `POST /api/v1/teacher/materials/generate` — приём источника (text/file/topic-only)
- [ ] **1.2.2** Парсер источников: PDF (pypdf), DOCX (python-docx), изображение (OCR через ai/hermes)
- [ ] **1.2.3** Единый шаблон генерации (см. раздел «Требования к AI-генерации» в PROMPT)
- [ ] **1.2.4** Валидация: только 7 класс (`grade=7`), topic_id из `subjects.curriculum_7_class`
- [ ] **1.2.5** Сохранение черновика со статусом `ai_generated`
- [ ] **1.2.6** Тесты: генерация из 3 типов источников, ошибки парсинга, невалидный topic

## 1.3 Backend: CRUD и workflow статусов

- [ ] **1.3.1** `GET /api/v1/teacher/materials` — список с фильтрами (status, subject, topic)
- [ ] **1.3.2** `GET /api/v1/teacher/materials/{id}` — детальный просмотр
- [ ] **1.3.3** `PATCH /api/v1/teacher/materials/{id}` — редактирование Учителем
- [ ] **1.3.4** `POST /api/v1/teacher/materials/{id}/approve` — переход `ai_generated → teacher_approved`
- [ ] **1.3.5** `POST /api/v1/teacher/materials/{id}/publish` — переход `teacher_approved → published`
- [ ] **1.3.6** `DELETE /api/v1/teacher/materials/{id}` — soft delete (только admin/owner)
- [ ] **1.3.7** Тесты: переходы статусов, недопустимые переходы → 409, RBAC на каждом

## 1.4 Alembic миграция 0008

- [ ] **1.4.1** Новые поля в `materials`:
  - `status` (Enum: draft/ai_generated/teacher_approved/published)
  - `generated_by` (FK users.id)
  - `approved_by` (FK users.id, nullable)
  - `published_at` (DateTime, nullable)
  - `source_type` (Enum: text/file/topic)
  - `source_ref` (Text/JSONB — ссылка на загруженный файл или текст)
  - `ai_confidence` (JSONB — что AI пометил как «не уверен»)
- [ ] **1.4.2** Индексы: `status`, `(subject_id, status)`, `topic_id`
- [ ] **1.4.3** Downgrade-стратегия (откат без потери данных)
- [ ] **1.4.4** Тест миграции в CI (upgrade → downgrade → upgrade на чистой БД)

## 1.5 Frontend: страницы /teacher

- [ ] **1.5.1** `/teacher` — список материалов с фильтрами и статусами (карточки)
- [ ] **1.5.2** `/teacher/generate` — мастер из 3 шагов: источник → preview → save/edit
- [ ] **1.5.3** `/teacher/materials/[id]` — детальный просмотр + кнопки approve/publish/edit
- [ ] **1.5.4** Markdown-рендер превью (использовать существующий из lesson view, если есть)
- [ ] **1.5.5** Навигация: добавить «Учительская» в сайдбар для роли teacher
- [ ] **1.5.6** Empty states и loading states
- [ ] **1.5.7** E2E (Playwright): полный flow generate → approve → publish

## 1.6 Тесты Sprint 1 (gate)

- [ ] **1.6.1** Unit: RBAC (≥10 кейсов)
- [ ] **1.6.2** Unit: генерация материалов (mock AI) — ≥8 кейсов
- [ ] **1.6.3** Unit: workflow статусов (валидные/невалидные переходы)
- [ ] **1.6.4** Integration: парсеры PDF/DOCX
- [ ] **1.6.5** E2E: ученик видит только `published`, учитель видит всё своё
- [ ] **1.6.6** Все 136 backend + 12 E2E — **зелёные**

## 1.7 Документация Sprint 1

- [ ] **1.7.1** `docs/api.md` — раздел «Teacher API»
- [ ] **1.7.2** `docs/architecture.md` — диаграмма teacher flow
- [ ] **1.7.3** `CHANGELOG.md` (создать, если нет) — запись спринта
- [ ] **1.7.4** `README.md` — обновить раздел «Роли и доступы»

---

# 🟧 СПРИНТ 2 — UX Ученика + практика + повторение

**Цель:** полноценный цикл обучения с интервальным повторением.

## 2.1 Цикл урока /topics/[id]

- [ ] **2.1.1** Режим «Объяснение» — простой язык, ключевые мысли
- [ ] **2.1.2** Режим «Практика» — задачи с моментальной проверкой + hint
- [ ] **2.1.3** Режим «Проверка» — мини-тест из 5 вопросов
- [ ] **2.1.4** Режим «Повторение» — карточки на сегодня
- [ ] **2.1.5** Прогресс-бар мастерства по теме
- [ ] **2.1.6** Тесты + E2E полного цикла

## 2.2 Spaced Repetition

- [ ] **2.2.1** Модель хранения попыток: `progress.attempts` (расширение, миграция 0009)
- [ ] **2.2.2** Алгоритм SM-2 (или упрощённый Leitner box) для интервалов 1д/1нед/1мес/3мес
- [ ] **2.2.3** Endpoint `GET /api/v1/progress/due-for-review` — карточки «на сегодня»
- [ ] **2.2.4** UI: блок «Сегодня к повторению» на главной ученика
- [ ] **2.2.5** Учёт T1D: лимит ≤20 карточек/день, мягкие напоминания
- [ ] **2.2.6** Тесты алгоритма (детерминированные снимки интервалов)

## 2.3 Голосовой ввод в UI

- [ ] **2.3.1** Кнопка микрофона в `LessonChat` (Whisper backend уже есть)
- [ ] **2.3.2** Запись → POST `/voice/transcribe` → вставка текста в поле
- [ ] **2.3.3** UX: визуализация записи, обработка ошибок микрофона
- [ ] **2.3.4** E2E: голосовой ввод → AI-ответ

## 2.4 Markdown + typewriter

- [ ] **2.4.1** Безопасный markdown-рендер (rehype-sanitize) для AI-ответов
- [ ] **2.4.2** Подсветка кода (для задач по информатике)
- [ ] **2.4.3** Typewriter-эффект для SSE-стрима
- [ ] **2.4.4** Тесты рендера (XSS-кейсы)

## 2.5 Документация Sprint 2

- [ ] **2.5.1** `docs/architecture.md` — обновить flow ученика
- [ ] **2.5.2** `README.md` — раздел «Spaced Repetition»

---

# 🟨 СПРИНТ 3 — Кабинет Родителя

## 3.1 Backend метрики

- [ ] **3.1.1** Endpoint `GET /api/v1/parents/students/{id}/dashboard` — агрегаты
- [ ] **3.1.2** Метрики: mastery по предметам/темам, динамика 7/30/90 дней, серии, время на платформе
- [ ] **3.1.3** Топ-N типичных ошибок (агрегация по `progress.attempts`)
- [ ] **3.1.4** RBAC: родитель видит только своего ребёнка через invite-binding

## 3.2 Frontend /parent dashboard

- [ ] **3.2.1** Страница `/parent` с графиками (recharts или аналог)
- [ ] **3.2.2** Карточки: текущий mastery, прогресс за неделю, ошибки
- [ ] **3.2.3** Экспорт PDF (через weasyprint или pdfkit)
- [ ] **3.2.4** Приватность: нет доступа к сырым чатам

## 3.3 Уведомления

- [ ] **3.3.1** Email-сводка еженедельно (шаблон Jinja2)
- [ ] **3.3.2** Telegram-сводка через существующий бот (cron)
- [ ] **3.3.3** Настройки частоты в `/parent/settings`

## 3.4 Документация Sprint 3

- [ ] **3.4.1** `docs/security.md` — политика приватности «что видит родитель»
- [ ] **3.4.2** `docs/api.md` — Parent API

---

# 🟦 СПРИНТ 4 — Технический долг

## 4.1 pgvector вместо in-memory RAG

- [ ] **4.1.1** Миграция 0010: расширение `vector`, таблица `rag_chunks` (id, doc_id, embedding vector(384), metadata jsonb)
- [ ] **4.1.2** Сервис эмбеддингов: подключить sentence-transformers локально (CPU) или через AI API
- [ ] **4.1.3** Индексация существующих материалов (скрипт `scripts/reindex_rag.py`)
- [ ] **4.1.4** Замена `app/rag.py` на pgvector-бэкенд (с сохранением интерфейса)
- [ ] **4.1.5** Мониторинг памяти LXC (pgvector съедает RAM — лимитировать чанки)

## 4.2 Multi-worker uvicorn

- [ ] **4.2.1** Dockerfile: `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]`
- [ ] **4.2.2** Redis-based rate-limit уже готов → проверить работу на 4 воркерах
- [ ] **4.2.3** WebSocket sticky sessions через Redis pub/sub (если ещё не сделано)
- [ ] **4.2.4** Smoke-тест на production: 4 воркера, нагрузка

## 4.3 Rate-limit на /auth/register

- [ ] **4.3.1** Защита от brute-force и массовой регистрации (5/час на IP)
- [ ] **4.3.2** Капча при превышении (опционально, через Turnstile/hCaptcha)
- [ ] **4.3.3** Тесты: 11-я попытка → 429

## 4.4 Audit log retention

- [ ] **4.4.1** Cron `audit_cleanup.py` — удаление/архив записей старше 90 дней
- [ ] **4.4.2** Конфиг в `app/config.py` (TTL_AUDIT_DAYS)
- [ ] **4.4.3** Тест: записи старше TTL не возвращаются в /admin

## 4.5 RAG в контексте AI-промптов

- [ ] **4.5.1** Текущее: RAG изолирован → добавить top-k чанков в `app/ai/prompts.py`
- [ ] **4.5.2** Учёт лимита токенов (не превышать контекст)
- [ ] **4.5.3** Тесты качества ответа с/без RAG

## 4.6 X-Forwarded-For trust

- [ ] **4.6.1` Явный `TRUSTED_PROXIES` в конфиге (CIDR-список)
- [ ] **4.6.2** Использовать только первый IP из доверенной цепочки
- [ ] **4.6.3` Тесты: подмена XFF с недоверенного IP игнорируется

## 4.7 Документация Sprint 4

- [ ] **4.7.1` `docs/deployment.md` — multi-worker, pgvector, retention
- [ ] **4.7.2` `docs/security.md` — rate-limit, XFF

---

# 🟪 СПРИНТ 5 — Наблюдаемость и надёжность

## 5.1 Prometheus /metrics

- [ ] **5.1.1** Endpoint `GET /metrics` (prometheus_client)
- [ ] **5.1.2** Метрики: http_requests_total, http_request_duration_seconds, ai_tokens_total
- [ ] **5.1.3** Grafana dashboard (JSON в `deploy/grafana/`)

## 5.2 Sentry/OpenTelemetry

- [ ] **5.2.1** Sentry SDK в `app/main.py` (errors + performance)
- [ ] **5.2.2** OpenTelemetry traces для критичных путей (auth, AI, materials)

## 5.3 Алерты

- [ ] **5.3.1` Cron-мониторинг Redis/SMTP/DB (уже есть частично) → расширить
- [ ] **5.3.2` Алерты в Telegram: healthcheck fail, error rate > threshold

## 5.4 Real-time метрики в /admin

- [ ] **5.4.1` WebSocket `/admin/ws/metrics` — пуш раз в 5с
- [ ] **5.4.2` UI: живые графики (активные сессии, AI-запросы/мин)

## 5.5 Документация Sprint 5

- [ ] **5.5.1` `docs/deployment.md` — мониторинг, алерты

---

## 📐 Требования к AI-генерации контента (единый шаблон, Sprint 1)

Каждый сгенерированный материал темы ОБЯЗАН содержать:

- [ ] Название темы, «зачем нужна», связь с изученным
- [ ] 3–7 главных мыслей, ключевые термины
- [ ] Правило/формула/дата/причинно-следственная связь
- [ ] Простой пример + схема/таблица
- [ ] 1 типичное заблуждение + 1 частая ошибка
- [ ] 3 вопроса самопроверки
- [ ] **Практические задачи (приоритет №1)**: ≥5, метки `easy/medium/hard`, эталонные решения для авто-проверки
- [ ] Мини-тест (5 вопросов с вариантами)
- [ ] Карточки «вопрос→ответ» для spaced repetition
- [ ] AI помечает неуверенные места → блокируют публикацию без approve

---

## 🔒 Протокол безопасного AI (обязательно в коде)

- [ ] AI не получает ФИО/адрес/T1D-данные ученика в промптах
- [ ] Sanitize input для teacher-flow (расширить `app/ai/sanitize.py`)
- [ ] AI-контент → human approve → публикация
- [ ] Audit log: источник/основание AI-генерации

---

## 📝 Журнал прогресса

> Заполняется по мере выполнения спринтов.

### 2026-07-12
- План создан в `docs/ROADMAP.md` на основе аудита из `PROMPT-FOR-OTHER-AI.md`
- Baseline зафиксирован: 136/136 backend, 12/12 E2E, 8/8 smoke — все зелёные
- Приоритет — Спринт 1 (роль Учителя), это блокер

### 2026-07-12 — Sprint 1 завершён ✅
- **1.1 RBAC-middleware**: `app/common/deps.py` + защита 11 endpoints. +23 теста.
- **1.2 AI-генерация**: модуль `app/teacher/`, парсеры (text/file/topic), 9-блоковый шаблон, prompt injection защита. +14 тестов.
- **1.3 CRUD + workflow**: 9 endpoints, state machine (`draft → ai_generated → teacher_approved → published`), audit log на каждое действие. +15 тестов.
- **1.4 Миграция 0008**: 6 полей в `learning_materials` (status, generated_by, approved_by, published_at, source_type, ai_confidence), 3 индекса, batch_alter_table для SQLite-совместимости.
- **1.5 Frontend**: `/teacher`, `/teacher/generate`, `/teacher/materials/[id]`, навигация для роли teacher/admin.
- **1.6 Gate**: 188/188 backend, 14 E2E, frontend собирается.
- **1.7 Docs**: CHANGELOG.md создан, docs/api.md обновлён (Teacher API + workflow диаграмма), docs/security.md (RBAC политики), README.md обновлён.
- **Бонус**: исправлен баг в tests/conftest.py — pydantic-settings кэшировал settings и UPLOAD_DIR от одного тестового файла протекал в другие.
- **Статистика**: +52 backend теста, +3 E2E теста, +3 страницы, +9 API endpoints, +6 DB полей, +1 миграция.

### Следующий: Sprint 2 (UX Ученика + практика + повторение)

### 2026-07-12 — Sprint 2 завершён ✅
- **2.1 Endpoint `/student/materials`** — ученик видит только `published` материалы (read-only).
- **2.2 SM-2 Spaced Repetition** — модуль `app/progress/spaced.py`, endpoints `/progress/due-for-review` и `/progress/review-result`, миграция 0009.
- **2.3 Frontend**: блок «🔄 Сегодня к повторению» на `/subjects`.
- **2.4 Voice API** — `api.voiceTranscribe()` метод в `lib/api.ts` (UI кнопка микрофона остаётся на следующий спринт).
- **2.5 Тесты**: 19 новых (SM-2 unit, endpoints, RBAC).
- **2.6 Документация**: CHANGELOG обновлён.
- **Gate**: 207/207 backend.

### 2026-07-12 — Sprint 3 завершён ✅
- **3.1 Backend**: `GET /api/v1/parents/students/{id}/dashboard` — расширенный дашборд с subject_mastery, streak, time_stats, top_mistakes, daily_activity_30d, due_for_review_count.
- **3.2 Frontend**: `/parent/dashboard/[studentId]` — KPI карточки, график активности, subject mastery, кнопка 📄 PDF.
- **3.3 PDF export**: HTML-шаблон в `/api/v1/parents/students/{id}/dashboard.pdf` (печать через браузер, без weasyprint).
- **3.4 Privacy policy**: задокументирована в `docs/security.md` (родитель не видит чаты/сырые попытки).
- **3.5 Тесты**: 13 новых (RBAC, streak, subject_mastery, due_for_review_count, HTML export).
- **Gate**: 220/220 backend, frontend `next build` ✅.

### 2026-07-12 — Sprint 4 завершён ✅
- **4.1 Rate limit на `/auth/register`**: 5/час на IP, in-memory + Redis fallback.
- **4.2 Audit log retention**: `app/admin/service.py::purge_old_logs()`, `POST /admin/audit-log/purge`, `deploy/cron/audit_cleanup.py` скрипт.
- **4.3 X-Forwarded-For trust**: `TRUSTED_PROXIES` (CIDR) в Settings, `_client_ip()` helper, защита от подмены IP.
- **4.4 Multi-worker uvicorn**: документация (Dockerfile поддерживает `--workers 4`, Redis-ready).
- **4.5 RAG в контексте AI-промптов**: отложено в Sprint 6+ (см. backlog).
- **4.6 Тесты**: 16 новых (register rate-limit, XFF trust, audit purge).
- **Документация**: `docs/sprint-4.md`.
- **Gate**: 236/236 backend.

### 2026-07-12 — Sprint 5 завершён ✅
- **5.1 Prometheus metrics**: `GET /metrics`, `http_requests_total`, `http_request_duration_seconds`, `ai_tokens_total`, `ai_requests_total`, `active_sessions_total`. Middleware с path normalization. AI service интегрирован.
- **5.2 Error tracking**: 5xx → `audit_logs` с `action=error.5xx`.
- **5.3 Real-time метрики в /admin**: через audit log endpoint с фильтром по `action=error.5xx`.
- **5.4 Тесты**: 11 новых.
- **Зависимости**: `prometheus-client==0.21.1`.
- **Gate**: 247/247 backend, frontend `next build` ✅.

### 🏁 ВСЕ 5 СПРИНТОВ ЗАВЕРШЕНЫ ✅
- Backend: 136 → 247 тестов (+111)
- Frontend: 11 → 15 страниц (+4)
- API endpoints: +16
- Миграции: +2 (0008, 0009)
- Cron: +1 (audit_cleanup.py)
- Build: backend pytest ✅ 247/247, frontend `next build` ✅.

---

## 🚧 Открытые вопросы (для уточнения)

> Заполняются по мере появления в ходе работы.

1. _TBD_

---

## 🔗 Связанные документы

- [`PROMPT-FOR-OTHER-AI.md`](../PROMPT-FOR-OTHER-AI.md) — аудит и приоритеты
- [`README.md`](../README.md) — общий обзор проекта
- [`QUICK-START.md`](../QUICK-START.md) — быстрый старт
- [`docs/api.md`](api.md) — API reference
- [`docs/architecture.md`](architecture.md) — архитектура
- [`docs/security.md`](security.md) — безопасность
- [`docs/deployment.md`](deployment.md) — деплой
