# API

> Полная спецификация всегда доступна в Swagger UI: `http://localhost:8000/docs`
> и в OpenAPI JSON: `http://localhost:8000/openapi.json`.

## Соглашения

- Префикс всех API: `/api/v1/...`
- Авторизация: `Authorization: Bearer <access_token>`
- Тело запроса/ответа — JSON
- Ошибки — стандартный формат:
  ```json
  { "error": "validation_error", "detail": "...", "request_id": "..." }
  ```
- Пагинация: `?limit=20&offset=0`
- Сортировка: `?sort=-created_at`

## Версионирование

Изменения, ломающие контракт, — в новой версии (`/api/v2/...`).
Старая версия живёт минимум 6 месяцев после релиза новой.

---

## Auth (`/api/v1/auth`)

Стандартный OAuth2 password flow.

| Метод | Путь                          | Описание                              | Доступ      |
|-------|-------------------------------|---------------------------------------|-------------|
| POST  | `/auth/register`              | Регистрация (роли: student/parent/teacher) | Public      |
| POST  | `/auth/login`                 | Логин (rate-limited: 10/15мин на IP)  | Public      |
| POST  | `/auth/refresh`               | Обновить access token по refresh      | Public      |
| GET   | `/auth/me`                    | Текущий пользователь                  | Auth        |
| POST  | `/auth/password-reset/request`| Запросить reset-токен                 | Public      |
| POST  | `/auth/password-reset/confirm`| Подтвердить reset                     | Public      |
| GET   | `/auth/oauth/{provider}/login`| OAuth2 (Google/Apple/etc)             | Public      |

---

## Subjects & Topics (`/api/v1/subjects`, `/api/v1/topics`)

| Метод | Путь                              | Описание                  | Доступ |
|-------|-----------------------------------|---------------------------|--------|
| GET   | `/subjects`                       | Список активных предметов | Auth   |
| GET   | `/subjects/{id}/topics`           | Темы предмета             | Auth   |
| GET   | `/topics/{id}`                    | Детали темы               | Auth   |

---

## Materials (`/api/v1/materials`) — read-only для всех авторизованных

| Метод | Путь                              | Описание                       | Доступ                  |
|-------|-----------------------------------|--------------------------------|-------------------------|
| POST  | `/materials/upload`               | Загрузить файл-материал        | teacher, admin          |
| GET   | `/materials/search?q=...`         | Поиск по материалам            | Auth                    |
| GET   | `/materials/topic/{topic_id}`     | Материалы темы                 | Auth                    |

---

## Teacher (`/api/v1/teacher`) — Sprint 1

Все endpoints требуют роль **teacher или admin**. Teacher видит только свои
материалы; admin — все.

| Метод | Путь                                          | Описание                          |
|-------|-----------------------------------------------|-----------------------------------|
| POST  | `/teacher/materials/generate`                 | AI-генерация черновика            |
| POST  | `/teacher/materials/upload-source`            | Загрузить файл-источник           |
| GET   | `/teacher/materials`                          | Список (фильтры: status, topic)  |
| GET   | `/teacher/materials/{id}`                     | Детальный просмотр                |
| PATCH | `/teacher/materials/{id}`                     | Редактировать (откатывает approve)|
| DELETE| `/teacher/materials/{id}`                     | Удалить (только draft/ai_generated)|
| POST  | `/teacher/materials/{id}/approve`             | → `teacher_approved`              |
| POST  | `/teacher/materials/{id}/publish`             | → `published` (доступно ученику)  |
| POST  | `/teacher/materials/{id}/unpublish`           | ← `teacher_approved`              |

### Workflow статусов

```
draft ─┐
       ├─→ ai_generated ─→ teacher_approved ─→ published
       │      ↑                 │                  │
       └──────┘ (rollback)     └──────────────────┘ (rollback)
```

Любое редактирование (PATCH) approved/published → откатывает в `ai_generated`
(требуется повторный approve).

### Единый шаблон AI-генерации

Каждый сгенерированный материал содержит:
- `title`, `purpose`, `connection_to_prior`
- `key_ideas[]` — 3-7 главных мыслей с терминами
- `rule_or_formula`, `simple_example`, `schema_or_table`
- `misconception`, `common_mistake`
- `self_check_questions[]` — 3 вопроса
- **`practice_tasks[]`** — минимум 5, приоритет №1, с метками сложности
  (`easy`/`medium`/`hard`), эталонными решениями и hints
- `mini_test[]` — 5 вопросов с 4 вариантами
- `flashcards[]` — 6-10 карточек для spaced repetition
- `ai_uncertainty_notes[]` — что требует проверки Учителем

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
- `400` — пустой источник / невалидный topic / обнаружен prompt injection
- `403` — недостаточно прав
- `404` — тема не найдена

---

## Admin (`/api/v1/admin`) — только admin

| Метод | Путь                                  | Описание                          |
|-------|---------------------------------------|-----------------------------------|
| GET   | `/admin/stats`                        | Сводная статистика                |
| GET   | `/admin/users`                        | Список пользователей              |
| POST  | `/admin/users/{id}/deactivate`        | Деактивация пользователя          |
| GET   | `/admin/audit-log`                    | Audit log (фильтры: user, action, since, until) |
| POST  | `/admin/diagnostics/expire-stale`     | Завершить старые diagnostic сессии|
| POST  | `/admin/notifications/test`           | Тест SMTP (dry-run если не настроен) |

---

## Parents (`/api/v1/parents`) — только parent

| Метод | Путь                              | Описание                       |
|-------|-----------------------------------|--------------------------------|
| POST  | `/parents/invite`                 | Создать invite-код             |
| GET   | `/parents/children`               | Список привязанных детей       |
| GET   | `/parents/children/{student_id}`  | Обзор ребёнка                  |

---

## Students (`/api/v1/students`) — только student

| Метод | Путь                              | Описание                       |
|-------|-----------------------------------|--------------------------------|
| POST  | `/students/link-parent`           | Привязаться к родителю по коду |

---

## AI (`/api/v1/ai`) — auth

| Метод | Путь                              | Описание                       |
|-------|-----------------------------------|--------------------------------|
| POST  | `/ai/explain`                     | Объяснение темы                |
| POST  | `/ai/hint`                        | Подсказка к задаче             |
| POST  | `/ai/check-answer`                | Проверка ответа                |
| POST  | `/ai/generate-exercise`           | Генерация одной задачи         |
| POST  | `/ai/chat`                        | Чат с AI                       |
| GET   | `/ai/ping`                        | Проверка доступности AI         |

Также WebSocket: `ws://.../ws/ai/{topic_id}?token=...` (стрим объяснения).

---

## Notifications (`/api/v1/notifications`) — auth

| Метод | Путь                              | Описание                       |
|-------|-----------------------------------|--------------------------------|
| GET   | `/notifications/`                 | Список уведомлений             |
| POST  | `/notifications/{id}/read`        | Пометить прочитанным           |
| GET   | `/notifications/settings`         | Настройки (email/telegram)     |
| PUT   | `/notifications/settings`         | Обновить настройки             |
