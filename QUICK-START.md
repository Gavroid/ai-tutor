# 🎯 AI-репетитор 7 класса — краткий обзор

> **Если у тебя мало времени — прочитай только этот файл.** Полная версия: `PROMPT-FOR-OTHER-AI.md`.

## Что это

Production-ready AI-репетитор для школьников 7 класса (РФ). Ребёнок регистрируется, выбирает тему, получает от AI объяснения/задачи/проверки. Родители видят прогресс.

**URL**: https://192.168.1.86 (self-signed HTTPS, Proxmox LXC)

## Стек

- **Backend**: FastAPI 0.115 + SQLAlchemy 2 + Postgres 16 (Python 3.12)
- **Frontend**: Next.js 16 + React 19 + TypeScript + Tailwind
- **AI**: MiniMax-M3 через OpenAI-compatible API
- **Infra**: Docker Compose (7 контейнеров), Nginx, Redis, Proxmox LXC
- **Tests**: **428/428** backend pytest + 15/15 Playwright E2E (все зелёные; +111 в Sprint 1-5, +23 в Pilot Core)

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
## Production state
- **7 контейнеров запущено, 5/7 healthy**: db, backend, frontend, proxy, redis (healthy); grafana + prometheus — healthy; proxy — без healthcheck.
- **5 cron jobs**: backup 03:00, 3 monitoring каждые 5 мин, audit cleanup 03:00.
- **Backup**: pg_dump + uploads → `/opt/ai-tutor/deploy/backup/_out/` (локальный) → offsite через SMB на `\\192.168.1.91\Kirill-AI\ai-tutor\` (smbclient, без mount.cifs — LXC unprivileged не поддерживает) → md5 verify.
- **Monitoring**: 3 cron скрипта пишут в `/var/log/ai-tutor-*.log`. Telegram-алерты — **отложены** (нужен `TELEGRAM_BOT_TOKEN` от владельца).
- **Audit log**: все админ-операции + register/deactivate/expire-stale/material upload. TTL 90 дней.
- **Pilot role policy**: `student`/`parent` — public registration; `teacher`/`admin` — только через `seed_users` CLI (PILOT_SEED_TOKEN).
- **Test creds**: `kirill@example.com` / `strongpass1` (student), `admin@example.com` / `strongpass1` (admin). **Это baseline, не production — сменить через `seed_users.py`!**

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
- CI/CD workflow готов и активирован (Gavroid/ai-tutor, 13.07.2026). `tests.yml` + `frontend-build.yml` объединены в `ci.yml` (2 jobs: backend pytest + frontend tsc/lint/build). Deploy через `tar | ssh` (без CI trigger — нужны `PRODUCTION_SSH_KEY` + `PRODUCTION_HOST` GitHub Secrets).
- Webhook-based deploy не сделан
- Prometheus/Grafana мониторинг поднят, но без активных Grafana dashboards (есть заглушка `ai-tutor-overview.json`).
- `BACKUP_OFFSITE_DEST` в `/etc/ai-tutor/.env` указывает на тот же LXC FS (fail-closed по дизайну Pilot Core, реальный offsite — SMB шара).

### UX
- PWA offline mode = stub (нет реального кэширования)
- Voice input в UI не подключен (есть только endpoint)
- OAuth UI кнопки не сделаны
- Markdown рендеринг в AI ответах не сделан

### Бизнес-логика
- AI temperature/tokens захардкожены где?
- Вопросы диагностики: что если AI генерирует ерунду? (нет валидации)
- Materials OCR: что с PDF с картинками внутри?
- Семантический match для free-text ответов отключён (Pilot Core Phase 2) — только exact match. AI-judge отложен.
- `app/main.py::ready()` отдаёт `repr(exc)` при DB-fail — privacy-hygiene фикс (5 строк).

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
- Базовый (разработка): `PROMPT-FOR-OTHER-AI.md` (~643 строки, синхронизирован с Sprint 6-10)
- Глубокий (аудит): `AI-DEEP-AUDIT-PROMPT.md` (990 строк) — тех. долг, фичи, UX, roadmap
- **Полный AI-handover (handover-style, июль 2026)**: `docs/MASTER-HANDOVER-PROMPT.md` — самый подробный документ, включает архитектуру, схему БД, развёртывание, известные pitfalls, вопросы к AI-аудитору
