# API

> Полная спецификация всегда доступна в Swagger UI: `http://localhost:8000/docs`
> и в OpenAPI JSON: `http://localhost:8000/openapi.json`.
>
> **Состояние:** обновлено 2026-07-13 после Pilot Core Stage 1. Полный реестр endpoints
> в роутерах (`apps/backend/app/*/router.py`) — 70+ REST + 3 WebSocket.

## Соглашения

- Префикс всех API: `/api/v1/...` (новая версия `/api/v2/...` — для breaking changes).
- Авторизация: `Authorization: Bearer <token>` (JWT, HS256).
- Тело запроса/ответа — JSON.
- Ошибки — стандартный формат:
  ```json
  { "error": "validation_error", "detail": "...", "request_id": "..." }
  ```
- Пагинация: `?limit=20&offset=0`.
- Сортировка: `?sort=-created_at`.
- Версионирование: breaking changes → `/api/v2/...`. Старая версия живёт ≥ 6 месяцев.

## Мета

| Метод | Путь | Описание | Доступ |
|-------|------|----------|--------|
| GET   | `/health`              | Healthcheck (с version + uptime) | Public |
| GET   | `/ready`               | Readiness (200 если БД доступна; **НЕ exposed** в nginx по умолчанию) | Internal |
| GET   | `/metrics`             | Prometheus метрики (http_requests_total, http_request_duration_seconds, ai_tokens_total, ai_requests_total, active_sessions_total) | Internal |
| GET   | `/api/v2/health`       | v2 healthcheck | Public |
| GET   | `/api/v2/info`         | v2 info (версия, фичи) | Public |

---

## Auth (`/api/v1/auth`)

Стандартный OAuth2 password flow. JWT (HS256), access + refresh. bcrypt rounds=12.

| Метод | Путь | Описание | Доступ |
|-------|------|----------|--------|
| POST  | `/auth/register`               | Регистрация (роли: **student, parent** — public; teacher/admin — только через seed CLI). Rate-limit 5/час на IP. | Public |
| POST  | `/auth/login`                  | Логин (rate-limit: 10/15мин на IP) | Public |
| POST  | `/auth/refresh`                | Обновить access token по refresh (rotation) | Public |
| GET   | `/auth/me`                     | Текущий пользователь | Auth |
| POST  | `/auth/password-reset/request` | Запросить reset-токен | Public |
| POST  | `/auth/password-reset/confirm` | Подтвердить reset | Public |
| GET   | `/auth/oauth/{provider}/login` | OAuth2 (Google/Apple/Yandex) — инициация | Public |
| GET   | `/auth/oauth/{provider}/callback` | OAuth2 callback | Public |

**Pilot role policy** (Sprint Pilot Core Stage 1): teacher и admin **не могут** создаваться публично. Только через `python -m app.scripts.seed_users --teacher/--admin` (требует `PILOT_SEED_TOKEN`).

---

## Subjects & Topics (`/api/v1/subjects`, `/api/v1/topics`)

| Метод | Путь | Описание | Доступ |
|-------|------|----------|--------|
| GET   | `/subjects`                       | Список активных предметов (12 предметов) | Auth |
| GET   | `/subjects/{id}/topics`           | Темы предмета (186 тем всего) | Auth |
| GET   | `/topics/{id}`                    | Детали темы | Auth |

---

## AI (`/api/v1/ai`) — auth

| Метод | Путь | Описание |
|-------|------|----------|
| POST  | `/ai/explain`            | Объяснение темы (mode: explain) |
| POST  | `/ai/hint`               | Подсказка к задаче (3 уровня, mode: hint) |
| POST  | `/ai/check-answer`       | Проверка ответа (mode: check, structured JSON) |
| POST  | `/ai/generate-exercise`  | Генерация одной задачи (mode: generate) |
| **POST**  | **`/ai/quiz`**       | **Квиз из N вопросов (1-20) по теме (mode: quiz, Sprint 1+2026-07-13)** |
| POST  | `/ai/chat`               | Чат с AI (mode: chat) |
| GET   | `/ai/ping`               | Проверка доступности AI |
| GET   | `/ai/budget/usage`       | Текущее потребление AI-бюджета пользователя |
| GET   | `/ai/admin/budget/top`   | Топ потребителей (admin) |

**WebSocket:** `ws://.../ws/ai/{topic_id}?token=...` (SSE-стрим объяснения/чата/generate). 3 WS endpoints: `/ws/ai/chat`, `/ws/ai/explain`, `/ws/ai/generate`.

**Бюджет:** дневной лимит (5xx-запросы/день). При превышении → 429. Учёт в `ai_budget` таблице.

**Режимы AI:** `explain`, `hint`, `check`, `generate`, `diagnose`, `chat`, **`quiz`** (7 режимов всего).

---

## Materials (`/api/v1/materials`)

| Метод | Путь | Описание | Доступ |
|-------|------|----------|--------|
| POST  | `/materials/upload`               | Загрузить файл-материал (TXT/MD/PDF/DOCX, OCR для PNG/JPG) | teacher, admin |
| GET   | `/materials/search?q=...`         | Полнотекстовый поиск | Auth |
| GET   | `/materials/topic/{topic_id}`     | Материалы темы (только `published` для student) | Auth |

---

## Teacher (`/api/v1/teacher`) — Sprint 1

Все endpoints требуют роль **teacher или admin**. Teacher видит только свои материалы; admin — все.

| Метод | Путь | Описание |
|-------|------|----------|
| POST  | `/teacher/materials/generate`         | AI-генерация черновика по источнику (text / file / topic) |
| POST  | `/teacher/materials/upload-source`    | Загрузить файл-источник (PDF/DOCX/TXT, макс 20 МБ) для генерации |
| GET   | `/teacher/materials`                  | Список (фильтры: status, topic_id) |
| GET   | `/teacher/materials/{id}`             | Детальный просмотр |
| PATCH | `/teacher/materials/{id}`             | Редактировать (откатывает в `ai_generated` если был `teacher_approved`/`published`) |
| DELETE| `/teacher/materials/{id}`             | Soft delete (только для `draft`/`ai_generated`; для `teacher_approved`/`published` → 409) |
| POST  | `/teacher/materials/{id}/approve`     | → `teacher_approved` |
| POST  | `/teacher/materials/{id}/publish`     | → `published` (доступно ученику) |
| POST  | `/teacher/materials/{id}/unpublish`   | ← `teacher_approved` |

### Workflow статусов

```
draft ─┐
       ├─→ ai_generated ─→ teacher_approved ─→ published
       │      ↑                 │                  │
       └──────┘ (rollback)     └──────────────────┘ (rollback)
```

Любое редактирование (PATCH) approved/published → откатывает в `ai_generated` (требуется повторный approve).

### Единый шаблон AI-генерации

Каждый сгенерированный материал содержит 9 блоков:
- `title`, `purpose`, `connection_to_prior`
- `key_ideas[]` (3-7 главных мыслей с терминами)
- `rule_or_formula`, `simple_example`, `schema_or_table`
- `misconception`, `common_mistake`
- `self_check_questions[]` (3 вопроса)
- **`practice_tasks[]`** (≥5, метки `easy`/`medium`/`hard`, эталонные решения + hints)
- `mini_test[]` (5 вопросов с 4 вариантами)
- `flashcards[]` (6-10 карточек для spaced repetition)
- `ai_uncertainty_notes[]` (что требует проверки Учителем)

### POST `/teacher/materials/generate`

**Request:**
```json
{
  "topic_id": 42,
  "source_type": "text | file | topic",
  "text": "...",                    // только для source_type=text
  "file_path": "/path/to/file",     // только для source_type=file
  "topic_hint": "..."               // опционально
}
```

**Response 200:** полный черновик со статусом `ai_generated`.

**Ошибки:**
- `400` — пустой источник / невалидный topic / обнаружен prompt injection (`app.ai.sanitize.detect_injection`)
- `403` — недостаточно прав
- `404` — тема не найдена

### POST `/teacher/materials/upload-source`

**Request:** `multipart/form-data` с файлом (PDF/DOCX/TXT, ≤ 20 МБ).

**Response 200:** `{"file_id": "...", "filename": "...", "size": ...}` — использовать `file_id` в `/teacher/materials/generate` с `source_type=file`.

---

## Student (`/api/v1/student`) — Sprint 2, 7

| Метод | Путь | Описание | Доступ |
|-------|------|----------|--------|
| GET    | `/student/materials`                       | Список `published` материалов для ученика (read-only) | student |
| GET    | `/student/materials/{material_id}`         | Детальный просмотр материала | student |
| PUT    | `/student/topics/{topic_id}/draft`         | Сохранить черновик ответа (autosave, **T1D-friendly** — не теряется при гипо) | student |
| GET    | `/student/topics/{topic_id}/draft`         | Загрузить черновик | student |
| DELETE | `/student/topics/{topic_id}/draft`         | Удалить черновик | student |
| GET    | `/student/badges`                          | Список моих баджей (полученные + locked) | student |
| POST   | `/student/badges/evaluate`                 | Триггернуть пересчёт баджей | student |

**Черновик** (Sprint 7) — localStorage + backend для восстановления после reload. **Критично для T1D** (прерывание при гипо/гипер → прогресс не теряется).

**Баджи** (Sprint 7.5) — **БЕЗ сгорающих streak'ов и штрафов за паузу**. T1D-friendly.

---

## Progress (`/api/v1/progress`) — auth (Sprint 2)

| Метод | Путь | Описание |
|-------|------|----------|
| GET   | `/progress/`                       | Мой прогресс (список) |
| GET   | `/progress/subjects/{subject_id}`  | Прогресс по предмету (мастери по темам) |
| GET   | `/progress/recommend-review`       | Темы для повторения (recommend) |
| GET   | `/progress/mistakes`               | Мои типичные ошибки |
| POST  | `/progress/attempts`               | Записать попытку (legacy, exact-match) |
| GET   | `/progress/due-for-review`         | Карточки к повторению сегодня (SM-2) |
| POST  | `/progress/review-result`          | Зафиксировать результат повторения (обновляет SM-2 интервалы) |

**Spaced Repetition** (SM-2): интервалы 1д / 1нед / 1мес / 3мес. Лимит ≤20 карточек/день. **T1D-friendly** — пауза не штрафуется, streak'и не используются.

**Note:** с Pilot Core Phase 2 `/progress/attempts` — только exact match. Для secure flow используется `/api/v2/exercises/{id}/answer`.

---

## Diagnostics (`/api/v1/diagnostics`)

| Метод | Путь | Описание |
|-------|------|----------|
| POST  | `/diagnostics/start`                   | Начать диагностическую сессию (CAT-адаптивная) |
| GET   | `/diagnostics/{session_id}/next`       | Следующий вопрос (адаптивный по ответам) |
| POST  | `/diagnostics/{session_id}/answer`     | Ответить на вопрос |
| POST  | `/diagnostics/{session_id}/finish`     | Завершить сессию, получить рекомендации |

---

## Parents (`/api/v1/parents`) — только parent

| Метод | Путь | Описание |
|-------|------|----------|
| POST  | `/parents/invite`                              | Создать invite-код для привязки ребёнка |
| GET   | `/parents/children`                            | Список привязанных детей |
| GET   | `/parents/children/{student_id}`               | Обзор ребёнка (агрегаты) |
| GET   | `/parents/students/{student_id}/dashboard`     | **Расширенный дашборд (Sprint 3)**: subject_mastery, streak, time_stats, top_mistakes, daily_activity_30d, due_for_review_count |
| GET   | `/parents/students/{student_id}/dashboard.pdf` | **HTML-шаблон для печати в PDF через браузер (Sprint 3.3)** |

**Privacy (Sprint 3):** родитель **видит** агрегаты и метрики, **НЕ видит**:
- Содержимое чатов с AI-репетитором.
- Персональные данные (ФИО, медданные о T1D).
- Историю конкретных попыток с текстом ответов.

При попытке посмотреть чужого ребёнка → 404 (не 403, чтобы не палить существование).

---

## Students (`/api/v1/students`) — только student

| Метод | Путь | Описание |
|-------|------|----------|
| POST  | `/students/link-parent`           | Привязаться к родителю по invite-коду |

---

## Admin (`/api/v1/admin`) — только admin

| Метод | Путь | Описание |
|-------|------|----------|
| GET   | `/admin/stats`                          | Сводная статистика |
| GET   | `/admin/users`                          | Список пользователей |
| POST  | `/admin/users/{user_id}/deactivate`     | Деактивация пользователя |
| GET   | `/admin/audit-log`                      | Audit log (фильтры: user_id, action, since, until) |
| POST  | `/admin/audit-log/purge?ttl_days=90`    | **Sprint 4.2**: ручная очистка audit log старше TTL (default 90 дней) |
| POST  | `/admin/diagnostics/expire-stale`       | Завершить зависшие diagnostic сессии |
| POST  | `/admin/notifications/test`             | Тест SMTP (dry-run если `SMTP_URL` не настроен) |
| GET   | `/admin/realtime`                       | Real-time метрики (UI скрыт в Pilot Core, endpoint работает) |

---

## Notifications (`/api/v1/notifications`) — auth

| Метод | Путь | Описание |
|-------|------|----------|
| GET    | `/notifications/`                | Список уведомлений (in-app) |
| POST   | `/notifications/{id}/read`       | Пометить прочитанным |
| POST   | `/notifications/read-all`        | Пометить все прочитанными |
| GET    | `/notifications/settings`        | Настройки доставки (email/telegram) |
| PUT    | `/notifications/settings`        | Обновить настройки |

**Email:** если `SMTP_URL` не задан, уведомления сохраняются в БД со `status="dry_run"` (без отправки). См. `deploy/smtp/SETUP.md`.

**Telegram:** ещё не подключён (отложено по запросу владельца).

---

## Voice (`/api/v1/voice`) — auth (Sprint 2)

| Метод | Путь | Описание |
|-------|------|----------|
| POST  | `/voice/transcribe`            | Whisper ASR (multipart/form-data с аудио) |

**Note:** UI кнопка микрофона ещё не подключена (Sprint 7.3).

---

## RAG (`/api/v1/rag`) — auth

| Метод | Путь | Описание |
|-------|------|----------|
| POST   | `/rag/index`              | Индексировать документ (chunk → embed → in-memory vector store) |
| POST   | `/rag/search`             | Top-k cosine similarity по запросу |
| DELETE | `/rag/material/{id}`     | Удалить индекс материала |
| GET    | `/rag/stats`              | Статистика индекса (количество чанков, размер) |

**Implementation:** in-memory hash-based (RAG Sprint 8 → pgvector). Embeddings: hash fallback (без sentence-transformers).

---

## V2 (`/api/v2/...`) — Pilot Core Phase 2 (secure flow)

**Цель:** закрыть уязвимость «client подделывает is_correct/score в `/progress/attempts`». V2 — server-trusted scoring.

| Метод | Путь | Описание |
|-------|------|----------|
| GET   | `/api/v2/health`                          | v2 healthcheck (Public) |
| GET   | `/api/v2/info`                            | v2 info (Public) |
| POST  | `/api/v2/exercises/generate`              | Сгенерировать `GeneratedExerciseInstance` (safe projection, **без `correct_answer` в response**) |
| POST  | `/api/v2/exercises/{exercise_id}/answer`  | Ответить. Server-trusted score. Idempotency через `submitted_at IS NULL`. 404/410/410 на expired/already-submitted |

**`POST /api/v2/exercises/{exercise_id}/answer` lifecycle:**
- `404` — exercise не найден.
- `410` — истёк (`expires_at < now`).
- `410` — уже отвечен (idempotency: повторный submit → тот же результат).
- `200` — успех, server-trusted `is_correct` и `score`.

**Миграция:** `0013_secure_exercises` (таблица `generated_exercise_instances`).

---

## Auth & Rate Limits (сводка)

| Endpoint | Лимит | Источник |
|----------|-------|----------|
| `/auth/register` | 5/час на IP | in-memory + Redis fallback (Sprint 4.1) |
| `/auth/login` | 10/15мин на IP | in-memory + Redis fallback |
| `/ai/*` (все режимы) | Дневной AI-бюджет (5xx/день) | `app/ai/budget.py` |
| WS `/ws/ai/*` | Concurrent connections per user | in-memory + Redis fallback |

**TRUSTED_PROXIES** (Sprint 4.3): CIDR-список доверенных прокси. По умолчанию `127.0.0.1/32,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16`. XFF читается только если immediate peer в trusted CIDR.

---

## OpenAPI / Swagger

- **Swagger UI:** `http://localhost:8000/docs` (или `https://192.168.1.86/docs` на проде).
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`.
- **ReDoc:** `http://localhost:8000/redoc`.

**Генерация client SDK:** `npx openapi-typescript-codegen --input openapi.json --output ./client/src/api --client axios`.

---

## WebSocket Endpoints

| Path | Описание | Auth |
|------|----------|------|
| `/ws/ai/{topic_id}?token=...`     | SSE-стрим объяснения темы | JWT в query |
| `/ws/ai/chat?token=...`           | Чат с AI (стрим) | JWT в query |
| `/ws/ai/generate?token=...`       | Генерация (стрим) | JWT в query |
| `/admin/ws/metrics`               | Real-time метрики для админа | admin |

**Reconnect:** клиент должен сам реализовать backoff (10 попыток, потом требуется перезагрузка страницы — см. `lib/ws-chat.ts`).
