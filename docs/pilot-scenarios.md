# Pilot Scenarios — ручной прогон четырёх ролей

Этот документ — **для ручной проверки** Pilot Core. Каждый сценарий
рассчитан на 5–10 минут; полный прогон всех четырёх — ≤ 60 минут.

Production: `https://192.168.1.86` (self-signed, в браузере принять риск).

## Учётные записи (production, baseline)

| Роль | Email | Пароль | Что смотреть глазами |
|---|---|---|---|
| Student (kid) | `kirill@example.com` | `strongpass1` | Темы, secure exercise flow, голос (скрыт) |
| Parent | `parent-e2e@example.com` | `strongpass1` | Список привязанных детей, дашборд |
| Teacher | `teacher@example.com` | `strongpass1` | Свои материалы, генерация, public preview |
| Admin | `admin@example.com` | `strongpass1` | Audit log, статистика, инструменты |

> **Пароли НЕ должны быть `strongpass1` в проде.** В Pilot Core они
> оставлены для базового пилота, но seed_users.py (`app/scripts/seed_users.py`)
> позволяет сменить пароль. Шаги: `PILOT_SEED_TOKEN=... python -m
> app.scripts.seed_users --admin admin@example.com "..." --password 'NEWPWD'`.

## Сценарий 1: Student (Кирилл)

**Цель:** убедиться, что student hot-path работает на secure v2-flow.

| Шаг | Действие | Ожидаемо |
|---:|---|---|
| 1 | `/login` → `kirill@example.com` / `strongpass1` | Редирект на `/subjects` |
| 2 | Видно «Математика» и другие 11 предметов | Да, 12 subject'ов |
| 3 | Клик на «Математика» → список тем | ≥ 1 тема |
| 4 | Клик на первую тему → `/topics/[id]` | URL меняется |
| 5 | Кнопка «Объясни тему» → AI-ответ в чате | Markdown рендерится, нет ошибок |
| 6 | Сообщение в чат «Спасибо!» → AI отвечает | Streaming WS-соединение |
| 7 | «Дай задание» → secure v2 flow | Вопрос виден, `correct_answer` НЕ виден (через DevTools Network) |
| 8 | Ответ на задание → «Проверить» | Server-trusted `is_correct`/`explanation` появляются |
| 9 | Microphone-кнопка | **Скрыта** (Phase 5, `NEXT_PUBLIC_VOICE_ENABLED=0`) |
| 10 | `/student/badges` | Только баджи за усилие (НЕ за streak) |

**Проверка глазами:**
- После шага 7 — DevTools → Network → POST `/api/v2/exercises/generate` → Response НЕ содержит `"correct_answer"`.
- После шага 8 — server-trusted `is_correct` и `explanation` отображаются.
- В audit_log (`/admin` → Audit) появились записи `user.seed`-style (если были попытки).

## Сценарий 2: Parent

**Цель:** privacy и multi-child.

| Шаг | Действие | Ожидаемо |
|---:|---|---|
| 1 | `/login` → `parent-e2e@example.com` / `strongpass1` | Редирект на `/parents` |
| 2 | Список привязанных детей | ≥ 1 ребёнок (если был привязан) |
| 3 | «Создать код» → отображается invite-code | Виден (не хранится в UI после refresh) |
| 4 | Клик на «📊» у ребёнка → `/parent/dashboard/[id]` | KPI карточки, mastery по предметам |
| 5 | DevTools → Network → `/api/v1/parents/students/[id]/dashboard` | Email ребёнка НЕ в response (privacy minimization, Sprint 3.5) |
| 6 | Слабые темы (mastery<60%) | Видны (если есть) |
| 7 | PDF-кнопка (если была) | **Скрыта** (Phase 5) |

**Проверка глаз:** в DevTools → Network → Response payload НЕ должен
содержать `child.email` или `student.email` (только `id` и `display_name`).

## Сценарий 3: Teacher

**Цель:** teacher workflow.

| Шаг | Действие | Ожидаемо |
|---:|---|---|
| 1 | `/login` → `teacher@example.com` / `strongpass1` | Редирект на `/teacher` |
| 2 | Список материалов teacher'а | Только свои (`generated_by == current.id`) |
| 3 | «Сгенерировать» → `/teacher/generate` | 3 source type (text/file/topic) |
| 4 | Workflow: `draft → ai_generated → teacher_approved → published` | Кнопки работают |
| 5 | Попытка открыть чужой материал (URL `?id=...`) | 403 Forbidden |

## Сценарий 4: Admin

**Цель:** admin audit и скрытые инструменты.

| Шаг | Действие | Ожидаемо |
|---:|---|---|
| 1 | `/login` → `admin@example.com` / `strongpass1` | Редирект на `/subjects` или `/admin` |
| 2 | `/admin` → табы Audit/Users/Stats/Tools | Все 4 видны |
| 3 | «📡 Real-time» ссылка | **Скрыта** (Phase 5, frontend commit `7f0e1f9`) |
| 4 | Таб «Инструменты» → «📧 Тест уведомления» | **Скрыто** (Phase 5) |
| 5 | Фильтр audit по `action=error.5xx` | Если есть записи за 7 дней — видны |
| 6 | `GET /metrics` (через nginx) | 200, текст Prometheus формата |

**Проверка глаз:** в DevTools → Console → нет ошибок
`/admin/realtime` (Phase 5 скрыт из UI, хотя nginx location добавлен).

## Сводный smoke (run после каждого deploy)

```bash
bash deploy/release/smoke.sh
```

Проверяет:
1. `/health`, `/ready`, `/api/v2/health` → 200
2. `/api/v1/auth/register` role=student → 201, role=admin → 4xx
3. `/api/v2/exercises/generate` → 200, **no `correct_answer` in payload**
4. `/api/v2/exercises/{id}/answer` → 200, server-trusted
5. `/admin/realtime` → 200 (WS ожидаемо для plain GET — OK)
6. Backup age < 26ч

Если smoke **падает** — `bash deploy/release/rollback.sh` восстанавливает
БД из последнего backup и перезапускает backend.
