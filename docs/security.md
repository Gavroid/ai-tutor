# Безопасность

## Реализовано в каркасе (Этап 1)

- **Секреты только в `.env`.** `.env` в `.gitignore`. В репозитории лежит
  `.env.example` с плейсхолдерами.
- **APP_SECRET_KEY валидируется.** Минимум 16 символов (pydantic-settings).
- **CORS ограничен.** Whitelist через переменную `CORS_ORIGINS`.
- **PostgreSQL недоступен снаружи.** Том `internal` в docker-compose.
- **Debug отключён в production.** `APP_DEBUG=false` в `.env.example`.
- **Healthcheck / health НЕ ломает процесс** при недоступной БД — для
  корректной работы оркестратора.

## Будет добавлено в следующих этапах

| Этап | Что |
|---|---|
| 2 | bcrypt-хэширование паролей, JWT (access+refresh), CSRF для cookie-auth, роли |
| 5 | Защита от prompt injection в AI Gateway (sanitization, лимиты длины) |
| 6 | Очистка HTML в ответах AI перед сохранением |
| 10 | MIME-проверка, magic-bytes валидация, ограничение размера файлов |
| 11 | Rate limit (slowapi), audit log админ-действий, retention политики |
| 12 | HTTPS через reverse proxy, fail2ban, мониторинг |

## RBAC (Role-Based Access Control) — Sprint 1.1+

Все защищённые endpoints используют единую зависимость `require_role(...)`
из `app/common/deps.py`:

| Зависимость                  | Кому разрешает                       |
|------------------------------|--------------------------------------|
| `require_admin()`            | admin                                |
| `require_teacher_or_admin()` | teacher, admin                       |
| `require_teacher()`          | только teacher                       |
| `require_parent()`           | parent                               |
| `require_student()`          | student                              |
| `current_user`               | любой авторизованный                 |

Неавторизованный запрос → **401 Unauthorized**.
Неверная роль → **403 Forbidden**.

### Политики доступа к материалам (Sprint 1.3+)

- **teacher** видит ТОЛЬКО свои материалы (`generated_by == current.id`).
  Чужие материалы → 403.
- **admin** видит ВСЕ материалы.
- **student** не имеет доступа к `/api/v1/teacher/*` (403).
- **parent** не имеет доступа к `/api/v1/teacher/*` (403).
- При PATCH/DELETE чужого материала → 403.
- Удаление материала в статусе `teacher_approved` или `published` запрещено (409).

### Audit log (Sprint 1+)

Каждое действие с материалами пишется в `audit_logs`:
`material.generate`, `material.update`, `material.delete`,
`material.approve`, `material.publish`, `material.unpublish`.

Каждая запись содержит `user_id`, `action`, `entity`, `entity_id`,
`details` (JSON), `ip_address` (из `X-Forwarded-For`), `created_at`.

### AI и безопасность данных (Sprint 1.2+)

- AI **не получает** персональные данные ученика (ФИО, адрес, медданные о T1D)
  в промптах при генерации материалов.
- Источник материала проходит `sanitize.detect_injection()` — попытки
  prompt injection блокируются (400).
- AI-контент проходит человеческую верификацию (approve Учителем)
  перед публикацией для ученика.
- AI помечает неуверенные места в `ai_uncertainty_notes` — они не блокируют
  публикацию, но информируют Учителя.

### Sanitization входа (Sprint 5+, обновлено)

`app/ai/sanitize.py`:
- `sanitize_user_input(text, max_chars)` — обрезка + удаление управляющих символов
- `detect_injection(text)` — поиск паттернов ("ignore previous instructions",
  `[INST]`, `<|system|>`, "you are now", etc.)
- `sanitize_output(text)` — экранирование HTML в ответе LLM

### Политика приватности родителя (Sprint 3)

Родитель **видит**:
- Агрегированные метрики ребёнка (mastery, accuracy, серии, активность)
- Список слабых тем и типичных ошибок (агрегаты по `mistakes.count`)
- Динамику прогресса по дням/предметам
- Количество заданий к повторению (без содержимого)

Родитель **НЕ видит**:
- Содержимое чатов ребёнка с AI-репетитором (дословно)
- Персональные данные (ФИО, адрес, медданные о T1D) — не отображаются
- История конкретных попыток с текстом ответов

Проверки:
- Endpoint `GET /api/v1/parents/students/{id}/dashboard` требует роль `parent`
  **и** активную привязку (`ParentStudentLink.status='active'`). Иначе 404.
- Если родитель пытается посмотреть не-своего ребёнка → 404 (не 403, чтобы не
  палить существование).

Экспорт отчёта (`/dashboard.pdf`):
- HTML-шаблон, готовый к печати в PDF через браузер
- Не содержит PII, только агрегаты
- Кнопка «📄 Скачать отчёт» на `/parent/dashboard/[studentId]`



- Минимальный сбор PII: только имя/псевдоним, класс, email родителя.
- Чат-сообщения **не показываются родителю** без отдельного разрешения
  (Этап 9).
- Удаление аккаунта + выгрузка данных — в плане (Этап 11).
- AI-инструкция запрещает опасный контент, манипуляции, выдачу
  медицинских/юридических советов. Промпт — в `apps/backend/app/ai/prompts.py`
  (появится в Этапе 5).

## Роли в пилоте (Pilot Core Stage 1 — P1.1.5)

Пилот — закрытая семейная система для четырёх пользователей. Регистрация
через браузер ограничена; привилегированные роли создаются заранее одним
явным seed-процессом.

### Матрица ролей в пилоте

| Роль | Где создаётся | Кто создаёт | Как сменить пароль |
|---|---|---|---|
| `student` | `POST /api/v1/auth/register` **или** `seed_users CLI` | сам пользователь (форму) **или** оператор через CLI (`--student email "Имя"`) | `seed_users --student email "Имя" --password 'NEW'` **или** `/api/v1/auth/password-reset/*` |
| `parent` | `POST /api/v1/auth/register` **или** `seed_users CLI` | сам пользователь (форму) **или** оператор через CLI (`--parent email "Имя"`) | `seed_users --parent email "Имя" --password 'NEW'` **или** `/api/v1/auth/password-reset/*` |
| `teacher` | **только** `seed_users CLI` | только оператор (PILOT_SEED_TOKEN) | **только** `seed_users --teacher email "Имя" --password 'NEW'` |
| `admin` | **только** `seed_users CLI` | только оператор (PILOT_SEED_TOKEN) | **только** `seed_users --admin email "Имя" --password 'NEW'` |

### Политика публичной регистрации

Реализация allowlist — `app/users/schemas.py::PUBLIC_REGISTRATION_ALLOWED_ROLES`
(`frozenset({"student", "parent"})`), импортируется в
`app/users/service.py::register_user` и применяется там же при дефолтном
`allow_private_bypass=False`. Публичный путь — `app/auth/router.py::register`
(вызывает `service.register_user(db, payload)` без bypass-флага, т.е. с
`allow_private_bypass=False`).

Поведение:

- `student` / `parent` через `POST /api/v1/auth/register` → **201 Created**.
- `teacher` / `admin` через `POST /api/v1/auth/register` → **403 Forbidden**
  (role не в allowlist) **плюс** в БД новая запись не попадает
  (см. `service.register_user` raise до `db.add`).
- `teacher` / `admin` через seed-скрипт с `allow_private_bypass=True` →
  создаются, и каждое действие пишется в `audit_log` (`action=user.seed`).

Это закрывает риск «самозванного учителя» (см. handover-prompt §3, P0/P1 #1)
и синхронизировано с общим трекером.

### Seed-скрипт `app/scripts/seed_users.py`

CLI создаёт/обновляет пользователей ВСЕХ ролей в текущей configured БД,
требует `PILOT_SEED_TOKEN` и пишет каждое действие в `audit_log`
(`action="user.seed"`). Пароли, хэши и сам токен **никогда** не попадают
в `audit_log.details` и в stdout (опционально через `--print-passwords`).

#### Требования безопасности

- Переменная окружения `PILOT_SEED_TOKEN` обязательна, минимум 16 символов.
  Сгенерировать: `openssl rand -hex 16`.
- Опциональный флаг `--token` ДОЛЖЕН совпадать с env. Если не совпадает —
  процесс завершается с ошибкой **до** любых операций с БД.
- Пароль из `--password` (>=12 символов) или `--default-password` для CSV
  используется для bcrypt-хэширования и **не** пишется ни в audit, ни в логи.
- Идемпотентность: повторный запуск обновляет display_name/role/хэш пароля.

#### Примеры запуска

```bash
cd /app  # внутри backend-контейнера
export PILOT_SEED_TOKEN="$(openssl rand -hex 16)"

# Demo: 4 известных аккаунта для пилота (student/parent/teacher/admin@pilot.local)
python -m app.scripts.seed_users --demo

# Конкретные пользователи через явные флаги:
python -m app.scripts.seed_users \
    --admin  admin@example.com  "Админ Пилота"     --password 'STRONG-Admin-1!' \
    --teacher teacher@example.com "Учитель Пилота"  --password 'STRONG-Teach-1!'

# Массовый импорт из CSV (email,role,display_name):
python -m app.scripts.seed_users \
    --csv /tmp/users.csv --default-password 'change-me-NOW-12'
```

CSV-формат:
```
email,role,display_name
student2@example.com,student,A
parent2@example.com,parent,B
teacher2@example.com,teacher,C
```

#### Что пишется в audit_log

| Поле | Значение |
|---|---|
| `action` | `"user.seed"` |
| `entity` | `"user"` |
| `entity_id` | `<user_id>` |
| `user_id` | `null` (системное действие) |
| `ip_address` | из request middleware (обычно `null` при запуске из cron) |
| `details` | `{"email": "...", "role": "...", "source": "flag\|csv\|demo", "demo": bool}` |
| `details.нет` | `password / hash / secret / token` — фильтруются автоматически |

### Как обновить пароль пилота

Пилот использует **только seed-скрипт** для смены пароля. Self-service
`/api/v1/auth/password-reset/*` работает в коде, но в пилоте **не применяется**
(UI скрыт, email-уведомления ненадёжны).

```bash
# Внутри backend-контейнера (cd /app) или в .venv с DATABASE_URL.
export PILOT_SEED_TOKEN="$(openssl rand -hex 16)"

# Teacher / admin — тот же email + новый --password → user обновляется,
# bcrypt-хэш пересчитан, audit пишет строку action=user.seed.
python -m app.scripts.seed_users \
    --admin  admin@example.com  "Админ Пилота"    --password 'NEW-STRONG-Pwd-12'
python -m app.scripts.seed_users \
    --teacher teacher@example.com "Учитель Пилота" --password 'NEW-STRONG-Pwd-12'

# Student / parent — эквивалентно через --student/--parent.
python -m app.scripts.seed_users \
    --student student@example.com "Ученик" --password 'NEW-STRONG-Pwd-12'
python -m app.scripts.seed_users \
    --parent  parent@example.com  "Родитель" --password 'NEW-STRONG-Pwd-12'
```

Идемпотентность гарантируется: повторный запуск обновляет `display_name`,
`role` и `password_hash`, а не создаёт дубль.

### Что НЕ входит в Pilot Core (отложено)

- OAuth2 / Google login (см. handover-prompt §5: cookie-auth пока не полный).
- Email-уведомления пользователям (worker ненадёжен; в пилоте UI скрыт).
- Public self-service «сброс пароля через email» уже работает в Этапе 11,
  но **не используется в пилоте**: пароли меняются seed-скриптом.

### Тестовое покрытие

- `tests/test_auth.py::test_teacher_role_self_registration_blocked` (P1.1.1)
- `tests/test_auth.py::test_admin_role_does_not_create_user` (P1.1.2)
- `tests/test_auth.py::test_registration_allowlist_is_student_and_parent_only` (P1.1.3)
- `tests/test_auth.py::test_registration_unknown_role_rejected` (P1.1.3, defence-in-depth)
- `tests/test_pilot_seed_users.py` — 8 тестов для P1.1.4
  (token gate, идемпотентность, --demo, --csv, audit leak check)

Acceptance фазы 1 см. в `.hermes/plans/2026-07-13_134543-pilot-core-stage-1.md §Фаза 1`.

## Backup и DR

`deploy/backup/backup.sh`:
- ежедневный `pg_dump` в `deploy/backup/_out/`
- архив uploads
- ротация 14 дней
- восстановление: `./backup.sh --restore <file>`

## Секреты в cron (Sprint 6.4)

**Правило:** БД-пароль и любые секреты НИКОГДА не передаются
через CLI-аргументы cron-команд и НЕ хранятся в `/etc/cron.d/*` или
`/var/spool/cron/*` в открытом виде.

**Реализация (с 2026-07-13):**
- `/etc/ai-tutor/.env` — файл с секретами для cron-задач.
  Права `600`, owner `root:root`. Доступ только root.
- Cron-строки используют `set -a; source /etc/ai-tutor/.env; set +a`
  для подгрузки окружения.

**Пример (`/etc/cron.d/ai-tutor-audit-cleanup`):**
```cron
0 3 * * * root bash -c "set -a; source /etc/ai-tutor/.env; set +a; \
  docker exec -u root deploy-backend-1 python3 /app/audit_cleanup.py" \
  >> /var/log/ai-tutor-audit-cleanup.log 2>&1
```

**Проверка:**
```bash
# Должно вернуть пусто
grep -r "DATABASE_URL=.*postgresql" /etc/cron* /etc/crontab
# Должно вернуть 600 root:root
stat -c "%a %U:%G" /etc/ai-tutor/.env
```

**Аудит:** при добавлении новой cron-задачи — секреты
выносятся в `/etc/ai-tutor/.env` СРАЗУ. Inline-пароли в cron
запрещены категорически.