# AI-Tutor Admin Guide

**Дата:** 2026-07-26
**Production:** https://school.431a.ru (LAN: 192.168.1.86)
**Target users:** Admins, parents (advanced), teachers

Это руководство для админа/владельца AI-Tutor. Описывает как управлять пользователями, материалами, audit log, alerts.

---

## 🔑 Доступ к admin panel

1. Откройте https://school.431a.ru/admin
2. Login с admin credentials (email + password)
3. Доступ к:
   - Audit log
   - Пользователи
   - Статистика
   - Инструменты
   - Invites (Sprint 52)

---

## 👥 Управление пользователями

### Просмотр пользователей
- Admin → вкладка "Пользователи"
- Все users с ролями (admin/teacher/parent/student)
- Фильтры: по роли

### Создание нового пользователя

#### Через UI (login/register)
1. Пользователь регистрируется на /register
2. По умолчанию role=student
3. Admin/teacher НЕ могут зарегистрироваться через UI (security gate)

#### Через invite code (Sprint 44)
1. Admin → Invites → "Создать invite"
2. Выбрать role (student/parent/teacher)
3. Optional: note, max_uses, expires_in_days
4. Code копируется автоматически в clipboard
5. Share code с пользователем (email/SMS)
6. Пользователь регистрируется на /register?code=ABC123
7. Role override: если invite role=teacher, пользователь получит teacher role

#### Deactivate пользователя
- Admin → Users → кнопка "Deactivate"
- Пользователь больше НЕ может залогиниться
- **Нельзя deactivate себя** (защита)

---

## 📚 Управление материалами (teacher)

### Создание материала
1. Login как teacher
2. Teacher → "Сгенерировать материал"
3. Выбрать subject → topic
4. AI генерирует текст (5-30 сек)
5. Review → Approve / Reject
6. Approved материалы появляются у students

### Bulk approve
- Teacher → Materials → "Bulk approve"
- Выбрать до 50 материалов за раз
- Approve selected

### Search
- Teacher → Materials → Search
- Поиск по title (case-insensitive)
- Комбинируется с filters (status, subject)

---

## 📋 Audit log

### Просмотр audit log
- Admin → Audit log
- Все admin/teacher действия записываются
- Filters: action, user_id, date range

### Hash chain integrity (Sprint 45)
- GET /api/v1/admin/audit-log/verify
- Проверяет SHA-256 hash chain
- Returns: verified, tampered, total_checked

### Export
- GET /api/v1/admin/audit-log/export?fmt=json|csv
- JSON: structured export для SIEM
- CSV: human-readable для compliance

### Retention
- POST /api/v1/admin/audit-log/purge?ttl_days=90
- Default: 90 дней
- Cron job автоматически purge'ит каждый день в 03:00

---

## 🔔 Alerts (Telegram)

### Как работают
1. Backend 5xx → middleware enqueue в Redis list `ai:alerts`
2. Alert worker (Sprint 50) BLPOPs
3. Telegram bot отправляет в chat

### Subscribe
- Telegram bot: @Ai_School_431a_bot
- Chat ID: 432505767
- Add bot к вашему Telegram для alerts

### Dedupe
- 5 мин TTL на (status_code + method + path) combination
- Чтобы не spam'ить с одинаковыми alerts

### Persistent log
- `/var/log/ai-tutor/alerts.jsonl` (Sprint 50)
- Каждый alert logged: timestamp, action, response time, message_id

---

## 🤖 T1D Safety features

### Recovery mode (Sprint 42)
- Если student нажал "У меня гипо/гипер" → recovery_mode=True
- Следующие упражнения автоматически easy (difficulty=1)
- 30-минутный cooldown

### Session pause (Sprint 34)
- PauseButton в /topics/[id]
- 4 причины: break/hypo/hyper/other
- Логируется в БД для analytics

### CGM integration (Sprint 40)
- Opt-in через /cgm page
- URL валидация: HTTPS-only, no localhost
- SSRF protection

---

## 🔍 Troubleshooting

### Проблема: Health endpoint возвращает 500
**Решение:**
1. SSH на production: `ssh root@192.168.1.86`
2. `docker logs deploy-backend-1 --tail 50`
3. Проверить PostgreSQL: `docker exec deploy-db-1 pg_isready`
4. Проверить Redis: `docker exec deploy-redis-1 redis-cli ping`

### Проблема: WebSocket не подключается
**Решение:**
1. Проверить nginx proxy (ws:// школа.431a.ru)
2. Проверить cookie auth (Sprint 27)
3. `docker logs deploy-backend-1 | grep -i websocket`

### Проблема: Telegram bot не отвечает
**Решение:**
1. `docker exec deploy-backend-1 ps aux | grep bot` — check bot alive
2. Если dead: `docker compose restart backend`
3. Telegram token в `/opt/ai-tutor/.env` (TELEGRAM_BOT_TOKEN)

### Проблема: Grafana дашборды не показывают данные
**Решение:**
1. Проверить Prometheus: `curl http://localhost:9090/-/healthy`
2. Проверить metrics: `curl http://localhost:8000/metrics`
3. Grafana provisioning: `/etc/grafana/provisioning/dashboards/`

---

## 🔒 Security checklist

- [x] Cookie-based auth (httpOnly, Secure, SameSite=lax)
- [x] 2FA для parents (TOTP + backup codes)
- [x] Audit log с hash chain integrity
- [x] CSRF protection (SameSite=lax)
- [x] Rate limit (Redis-based, multi-worker safe)
- [x] 5xx → Telegram alerts
- [x] Self-hosted runner (non-root)
- [x] SSRF protection (CGM config)

## 📊 Performance

- **Workers**: 4 uvicorn workers
- **Memory**: ~230MiB / 4GiB (5.6%)
- **Coverage**: 78% backend
- **Tests**: 709 passed
- **Cron jobs**: 9 (8 + alert-worker)

---

## 📁 Files & locations

```
/opt/ai-tutor/                 # production git clone
├── .env                       # secrets (mode 600, group app-secrets)
├── deploy/                    # docker-compose, nginx, grafana
│   ├── release/smoke.sh       # basic smoke (8 checks)
│   ├── release/smoke-extra.sh # Sprint 55 (13 checks)
│   ├── grafana/dashboards/    # 3 dashboards
│   └── nginx/nginx.conf
├── apps/
│   ├── backend/               # FastAPI
│   └── frontend/              # Next.js

/etc/cron.d/ai-tutor-*         # 9 cron jobs
/var/log/ai-tutor-deploy.log   # deploy history
/var/log/ai-tutor/alerts.jsonl # alert log (Sprint 50)
/etc/systemd/system/actions.runner.*  # self-hosted runner
```

## 🔗 Backlog

- **Sprint 64+**: Performance optimization, custom OTel spans
- **RAG**: real embeddings (после RAM upgrade до 8GB)
- **Multi-region**: not needed для LAN deployment
- **Multi-tenant**: not planned

## 📞 Контакты

- **Admin/owner**: Igor Vasyaev
- **Telegram**: @Ai_School_431a_bot
- **GitHub**: github.com/Gavroid/ai-tutor
- **Production**: https://school.431a.ru