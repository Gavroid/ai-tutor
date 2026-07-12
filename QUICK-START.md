# 🎯 AI-репетитор 7 класса — краткий обзор

> **Если у тебя мало времени — прочитай только этот файл.** Полная версия: `PROMPT-FOR-OTHER-AI.md`.

## Что это

Production-ready AI-репетитор для школьников 7 класса (РФ). Ребёнок регистрируется, выбирает тему, получает от AI объяснения/задачи/проверки. Родители видят прогресс.

**URL**: https://192.168.1.86 (self-signed HTTPS, Proxmox LXC)

## Стек

- **Backend**: FastAPI 0.115 + SQLAlchemy 2 + Postgres 16 (Python 3.12)
- **Frontend**: Next.js 16 + React 19 + TypeScript + Tailwind
- **AI**: MiniMax-M3 через OpenAI-compatible API
- **Infra**: Docker Compose (5 контейнеров), Nginx, Redis, Proxmox LXC
- **Tests**: 247 backend + 12 Playwright (все зелёные; +111 в Sprint 1-5)

## Структура

```
apps/backend/app/
├── admin/        audit log + admin endpoints
├── ai/           AI gateway (Hermes + Mock + WS + sanitize)
├── auth/         JWT + password_reset + OAuth2
├── diagnostics/  диагностика + expire
├── materials/    upload + OCR
├── notifications/ in-app + email
├── parents/      invite + link
├── progress/     mastery + attempts
├── subjects/     12 предметов × 186 тем
├── users/        User + StudentProfile
├── rag.py        vector store
├── rag_router.py
├── voice/        Whisper ASR
└── main.py       middleware + routes
```

## Ключевые endpoint'ы (50+)

- **Auth**: register, login, refresh, /me, password-reset, OAuth (Google/Yandex/GitHub)
- **AI**: explain, hint, check-answer, generate-exercise, chat + WS /ws/ai/{chat,explain,generate}
- **Subjects**: GET /subjects (ПУБЛИЧНЫЙ), /subjects/{id}/topics
- **Progress**: /progress/me, /mistakes, /recommend-review
- **Diagnostics**: /diagnostic/start/next/answer/finish
- **Parents**: /parents/invite, /students/link-parent
- **Materials**: /materials/upload (multipart), /search
- **Admin**: /admin/{stats,users,audit-log,notifications/test,diagnostics/expire-stale}
- **Voice**: POST /voice/transcribe
- **RAG**: POST /rag/{index,search}, DELETE /rag/material/{id}
- **Meta**: /health (с version + uptime)

## Production state

- **5 контейнеров healthy**: db, backend, frontend, proxy, redis
- **4 cron jobs**: backup (3AM), healthcheck, error-rate, smtp-worker (каждые 5 мин)
- **Backup**: pg_dump + uploads → /var/backups/ai-tutor/ → md5 verify
- **Monitoring**: 3 cron скриптов пишут в /var/log/ai-tutor-*.log
- **Audit log**: все админ-операции + register/deactivate/expire-stale/material upload
- **Test creds**: kirill@example.com / strongpass1 (student), admin@example.com / strongpass1 (admin)

## Что НЕ сделано (что я бы улучшил)

### Безопасность
- OAuth2 state CSRF protection — есть, но валидация?
- Rate limit X-Forwarded-For trust — может быть bypass
- JWT secret rotation — нет автоматической
- 2FA для админов

### Архитектура
- In-memory RAG store (теряется при рестарте) — мигрировать на pgvector
- Single-worker backend — нужен uvicorn --workers 4 + Redis (готов)
- Self-signed HTTPS — пользователь сделает Let's Encrypt
- WS reconnect — после 10 неудач требует перезагрузки страницы

### DevOps
- CI/CD workflow готов, но не активирован (нет git remote)
- Webhook-based deploy не сделан
- Prometheus/Grafana мониторинг не сделан

### UX
- PWA offline mode = stub (нет реального кэширования)
- Voice input в UI не подключен (есть только endpoint)
- OAuth UI кнопки не сделаны
- Markdown рендеринг в AI ответах не сделан

### Бизнес-логика
- AI temperature/tokens захардкожены где?
- Вопросы диагностики: что если AI генерирует ерунду? (нет валидации)
- Materials OCR: что с PDF с картинками внутри?

## Команды

```bash
# SSH
ssh -i /root/.ssh/id_ed25519_kirill_ai root@192.168.1.86

# Все тесты backend
cd /opt/ai-tutor/apps/backend && . .venv/bin/activate && \
  APP_SECRET_KEY=test-s...7890 \
  APP_ENV=development \
  DATABASE_URL=sqlite+pysqlite:///:memory: \
  AI_API_KEY=mock pytest -q

# Playwright
cd /opt/ai-tutor/apps/frontend && npx playwright test

# Smoke test
curl -sk https://192.168.1.86/health | python3 -m json.tool

# WS test
python3 /opt/ai-tutor/deploy/smoke/ws-test.py

# Backup test
bash /opt/ai-tutor/deploy/backup/test-restore.sh

# Redis rate limit
docker exec deploy-redis-1 redis-cli KEYS "*"
```

## Главные вопросы для аудита

1. **OAuth2 state** — правильно ли валидируется CSRF?
2. **Rate limit bypass** через X-Forwarded-For?
3. **In-memory RAG** — как масштабируется?
4. **N+1 queries** в progress/parents?
5. **Multi-worker** — почему не включено?
6. **AI streaming** — что если chunk corrupt?
7. **Self-signed HTTPS** — почему не Let's Encrypt?

## Файлы документации

- `README.md` — общее описание
- `PROMPT-FOR-OTHER-AI.md` — базовый промт для AI-агента (559 строк)
- `AI-DEEP-AUDIT-PROMPT.md` — **глубокий промт для аудита** (990 строк, рекомендуется для сторонних AI)
- `QUICK-START.md` — этот файл (краткая версия)
- `CHANGELOG.md` — история Sprint 1-5
- `docs/ROADMAP.md` — долгосрочный roadmap
- `docs/api.md` — API reference
- `docs/architecture.md` — архитектура
- `docs/security.md` — политика безопасности
- `docs/deployment.md` — деплой
- `docs/sprint-4.md` — детали Sprint 4
- `deploy/ssl/LETS-ENCRYPT.md` — инструкция по SSL
- `deploy/CICD.md` — CI/CD настройка
- `deploy/smtp/SETUP.md` — SMTP настройка
- `~/.hermes/skills/devops/ai-tutor-deploy/SKILL.md` — операционный runbook
- `apps/backend/tests/` — 25 файлов тестов (247 тестов) с примерами использования API

## Контекст пользователя

Делается для **Игоря** (Kirill — 13 лет, T1D, 7 класс). Production — домашний сервер. Важно:
- Ребёнок пользуется сам → UX > features
- Локальный сервер → нет облака
- Audit log для родителей
- Email уведомления для родителей

---

**Промты для AI-агентов:**
- Базовый (разработка): `PROMPT-FOR-OTHER-AI.md` (559 строк)
- Глубокий (аудит): `AI-DEEP-AUDIT-PROMPT.md` (990 строк) — тех. долг, фичи, UX, roadmap
