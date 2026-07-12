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