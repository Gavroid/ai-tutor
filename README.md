# AI-репетитор 7 класса

[![CI](https://github.com/Gavroid/ai-tutor/actions/workflows/ci.yml/badge.svg)](https://github.com/Gavroid/ai-tutor/actions/workflows/ci.yml)

Персональный AI-репетитор для школьной программы 7 класса.
**Production-ready MVP** (12 этапов MVP + расширения + production hardening).

> **Статус:** ✅ 247/247 backend тестов проходят (+111 в Sprint 1-5). 12/12 Playwright E2E. 8/8 production smoke. 5/5 контейнеров healthy. Развёрнут на 192.168.1.86 (Proxmox LXC) с HTTPS + WebSocket + monitoring + auto-backup + Redis + OAuth2 + RAG + Voice + Prometheus metrics + audit retention.

> **📖 Для AI-агентов:**
> - [`AI-DEEP-AUDIT-PROMPT.md`](./AI-DEEP-AUDIT-PROMPT.md) — глубокий промт для AI-агента (990 строк, рекомендуется для сторонних AI).
> - [`docs/MASTER-HANDOVER-PROMPT.md`](./docs/MASTER-HANDOVER-PROMPT.md) — полный handover (Pilot Core Stage 1, ~742 строки): архитектура, схема БД, развёртывание, pitfalls, запросы к AI-аудитору.
> - [`AI-DEEP-AUDIT-PROMPT.md`](./AI-DEEP-AUDIT-PROMPT.md) — **глубокий аудит** (990 строк): тех. долг, фичи, UX, roadmap. **Рекомендуется для сторонних AI.**
> - Краткая версия: [`QUICK-START.md`](./QUICK-START.md).

---

## Доступ

- **URL:** https://192.168.1.86 (self-signed cert — прими предупреждение браузера)
- **Ученик:** `kirill@example.com` / `strongpass1`
- **Админ (audit log):** `admin@example.com` / `strongpass1`
- **AI модель:** MiniMax-M3 (через OpenAI-compatible API)

---

## Что реализовано

### MVP (12 этапов)
| # | Этап | Что работает |
|---|---|---|
| 1 | Каркас | Docker Compose, FastAPI, Next.js 16, PostgreSQL 16, Nginx |
| 2 | Авторизация | JWT, 4 роли, профиль ученика, защита от admin self-register |
| 3 | Учебная структура | 12 предметов × 186 тем × 42 подтемы |
| 4 | UI ученика | 8 страниц + PWA |
| 5 | AI Gateway | Hermes/MiniMax-M3, retry/timeout, sanitize |
| 6 | AI-репетитор | 6 режимов (explain/hint/check/generate/diagnose/chat) + WS streaming |
| 7 | Диагностика | Генерация вопросов, эвристика, рекомендации, parent notification |
| 8 | Прогресс | Mastery, ошибки, рекомендации повторения |
| 9 | Родительский кабинет | Invite-коды, отчёты, privacy |
| 10 | Загрузка материалов | TXT/MD/PDF/DOCX + OCR для PNG/JPG |
| 11 | Security | Rate limit (Redis-ready), Audit log, Notifications (in-app + email) |
| 12 | Deploy | Docker Compose + Nginx + HTTPS + WebSocket + backups |
| **1+** | **Роль Учителя (Sprint 1)** | RBAC-middleware, AI-генерация материалов по единому шаблону, workflow статусов (draft → ai_generated → teacher_approved → published), UI `/teacher/*`. См. [CHANGELOG.md](CHANGELOG.md). |

### Расширения
- **HTTPS** с самоподписанным сертификатом (HTTP→HTTPS redirect)
- **WebSocket streaming** для чата/explain/generate (3 WS endpoints)
- **Audit log UI** на `/admin` странице (только для admin)
- **OCR** для изображений через pytesseract (eng/rus)
- **Admin endpoints**: stats, users list, deactivate, audit log query
- **In-app notifications** + email через SMTP (aiosmtplib)
- **Rate limit** через Redis (опционально, fallback на in-memory)

**API:** 70 REST endpoints + 3 WebSocket. **Frontend:** 15 страниц + PWA. **Тестов:** 247 backend + 12 E2E.

---

## Стек

- **Backend:** Python 3.12, FastAPI 0.115, SQLAlchemy 2, Alembic, Pydantic v2
- **Frontend:** Next.js 16, React 19, TypeScript strict, Tailwind, PWA
- **Database:** PostgreSQL 16
- **Reverse proxy:** Nginx 1.27 (HTTPS + WebSocket)
- **Контейнеры:** Docker Compose
- **AI:** MiniMax-M3 через OpenAI-compatible API
- **Email:** aiosmtplib (SMTP) с dry_run fallback
- **OCR:** pytesseract + tesseract-ocr

---

## Структура

```
ai-tutor/
├── apps/
│   ├── backend/                     # FastAPI backend
│   │   ├── app/
│   │   │   ├── ai/                  # AI Gateway (Hermes + Mock + WS + sanitize)
│   │   │   ├── auth/                # JWT авторизация
│   │   │   ├── admin/               # Audit log + admin endpoints
│   │   │   ├── diagnostics/         # Диагностика (Этап 7)
│   │   │   ├── materials/            # Загрузка материалов (Этап 10)
│   │   │   ├── notifications/       # In-app + email
│   │   │   ├── parents/             # Родительский кабинет (Этап 9)
│   │   │   ├── progress/            # Mastery, ошибки
│   │   │   ├── subjects/            # Учебная структура + seed
│   │   │   ├── users/               # User + StudentProfile
│   │   │   ├── db/                  # SQLAlchemy engine
│   │   │   ├── scripts/             # seed.py
│   │   │   └── main.py              # FastAPI app + middleware (rate limit, IP)
│   │   ├── alembic/versions/        # 6 миграций
│   │   ├── tests/                   # 71 тестов
│   │   └── requirements.txt          # aiosmtplib, pytesseract, Pillow, redis
│   └── frontend/                    # Next.js 16
│       ├── app/
│       │   ├── admin/               # Audit log UI
│       │   ├── diagnostic/           # Диагностический тест
│       │   ├── link-parent/          # Привязка к родителю
│       │   ├── parents/              # Родительский кабинет
│       │   ├── subjects/             # Главная + список тем
│       │   ├── topics/[id]/          # Чат + задания (WebSocket)
│       │   ├── login/                # register
│       │   └── page.tsx              # Redirect
│       ├── lib/
│       │   ├── api.ts                # REST клиент
│       │   └── ws-chat.ts            # WebSocket клиент
│       ├── types/                    # TypeScript типы
│       └── public/                   # PWA manifest + icon
├── data/                            # seed, curriculum, uploads
├── deploy/
│   ├── docker-compose.yml           # 4 контейнера
│   ├── nginx/nginx.conf             # HTTPS + WS upgrade
│   ├── ssl/                         # self-signed certs generator
│   ├── backup/backup.sh             # PG + uploads backup
│   ├── postgres-init/               # Init scripts
│   └── proxmox/                     # Proxmox LXC guides
├── docs/                            # architecture, security, deployment
├── .env.example
├── Makefile
└── README.md
```

---

## Production (192.168.1.86)

```bash
ssh -i ~/.ssh/id_ed25519_kirill_ai root@192.168.1.86
cd /opt/ai-tutor/deploy

# Управление
docker compose ps                    # статус (4/4 healthy)
docker compose logs -f               # логи
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed --reset
bash /opt/ai-tutor/deploy/backup/backup.sh   # бэкап
```

### E2E smoke test
```bash
scp /tmp/test_FINAL_V2.sh root@192.168.1.86:/tmp/
ssh root@192.168.1.86 'bash /tmp/test_FINAL_V2.sh'
# 35/35 проверок
```

### Тестовые креды
```
Ученик: kirill@example.com / strongpass1
Админ:  admin@example.com  / strongpass1
```

### WebSocket endpoints (стриминг AI)
- `wss://192.168.1.86/ws/ai/chat` — чат
- `wss://192.168.1.86/ws/ai/explain` — объяснение темы
- `wss://192.168.1.86/ws/ai/generate` — генерация задания

### HTTP endpoints (REST)
42 эндпоинта в OpenAPI: `/docs` (через `https://192.168.1.86/docs`)

### Frontend страницы (8)
`/`, `/login`, `/register`, `/subjects`, `/subjects/[id]`, `/topics/[id]`, `/diagnostic`, `/parents`, `/link-parent`, `/admin`

---

## Безопасность

- bcrypt пароли (rounds=12)
- JWT access (24h) + refresh (30d)
- CORS whitelisting через `CORS_ORIGINS`
- Postgres в internal Docker network
- Rate limit AI (30/мин/user, in-memory + Redis-ready)
- Sanitize входа/выхода LLM, prompt injection detection
- **AI ключ никогда не в логах/ответах**
- Files: ограничение размера, MIME-проверка, защита от path traversal
- HTTPS с самоподписанным сертификатом
- Audit log всех админских действий и важных событий
- Admin endpoints защищены role-проверкой

---

## Уведомления

В `app/notifications/service.py`:
- `notify_parents_of_milestone()` — автоматически при завершении диагностики
- Если `SMTP_URL` задан — отправляется через SMTP
- Иначе — сохраняется в БД со status=`dry_run`
- Все уведомления дублируются в `notifications` для показа в UI

---

## Резервное копирование

```bash
bash /opt/ai-tutor/deploy/backup/backup.sh
# Создаёт db-YYYYMMDDTHHMMSSZ.sql.gz + uploads-YYYYMMDDTHHMMSSZ.tar.gz
# Автоматическая ротация 14 дней

# Restore из бэкапа:
bash /opt/ai-tutor/deploy/backup/backup.sh --restore /var/backups/ai-tutor/db-YYYYMMDDTHHMMSSZ.sql.gz

# Тест restore на отдельной БД (без побочных эффектов):
bash /opt/ai-tutor/deploy/backup/test-restore.sh
```

**Автоматизация через cron** (уже настроено):
```
0 3 * * * /opt/ai-tutor/deploy/backup/backup.sh && /usr/local/bin/ai-tutor-backup-offsite.sh
```

Offsite копия в `/var/backups/ai-tutor/` — синхронизируется через `rsync`.

---

## Мониторинг

Три cron-задачи запускают проверки каждые 5 минут:

| Скрипт | Что проверяет | Алерт |
|---|---|---|
| `healthcheck.sh` | `/health` 200, disk > 80%, memory > 80%, **backup старше 26ч** | Telegram |
| `error-rate.sh` | ERROR/Traceback в логах backend > 5 за 5 мин | Telegram |
| `error-rate.sh` | HTTP 5xx ответы в access log > 5 за 5 мин | Telegram |

**Активация Telegram алертов** (опционально):
```bash
echo 'TELEGRAM_BOT_TOKEN="<your-token>"' >> /etc/environment
echo 'TELEGRAM_CHAT_ID="<your-chat-id>"' >> /etc/environment
# или в cron: добавить env в начало строки
```

**Логи:**
- `/var/log/ai-tutor-monitor.log` — все healthcheck + alerts
- `/var/log/ai-tutor-backup.log` — backup events
- `/var/lib/docker/containers/*/*-json.log` — контейнеры (ротация logrotate 10M×3)

**JSON structured access log** (backend):
```json
{"ts": 1783866698.63, "level": "INFO", "method": "GET", "path": "/api/v1/subjects", "status": 200, "duration_ms": 70, "ip": "172.19.0.4", "user_agent": "curl/8.5.0", "request_id": "5120e9c28b484c38"}
```

---

## Admin UI инструменты

В `/admin` есть таб **"Инструменты"** с:

1. **Тест уведомления** — отправляет test email, проверяет SMTP конфигурацию
2. **Завершить старые сессии** — force expire диагностик
3. **Фильтры audit log** — action / since / until

См. также `POST /api/v1/admin/notifications/test?email=X` (REST endpoint).

---

## Что осталось (на потом)

- **Let's Encrypt** — заменить self-signed (пользователь делает сам)
- **RAG / vector store** — для умного поиска по материалам
- **Email на каждый урок** — сейчас только при завершении диагностики
- **CI/CD pipeline** — workflow готов, нужен git remote
- **WS для hint/check** — chat/explain/generate уже есть
- **Multi-worker** rate limit с Redis (код готов, нужен Redis)
- **OAuth2** (Google/Яндекс) — вход через соцсети
- **Voice input** — speech-to-text для детей

См. `docs/architecture.md`, `docs/security.md`, `docs/deployment.md`.

---

## Что внутри (12 этапов MVP + расширения)

| # | Этап | Что работает |
|---|---|---|
| 1 | Каркас | Docker Compose, FastAPI, Next.js 16, PostgreSQL, healthcheck |
| 2 | Авторизация | JWT, 4 роли, профиль ученика, защита от admin self-register |
| 3 | Учебная структура | 12 предметов × 186 тем × 42 подтемы |
| 4 | UI ученика | 7 страниц + PWA (manifest, icon, service worker) |
| 5 | AI Gateway | Hermes/MiniMax провайдер, retry/timeout, sanitize |
| 6 | AI-репетитор | 6 режимов AI + WebSocket streaming |
| 7 | Диагностика | Генерация вопросов, эвристика, рекомендации |
| 8 | Прогресс | Mastery, ошибки, рекомендации повторения |
| 9 | Родительский кабинет | Invite-коды, отчёты, privacy |
| 10 | Загрузка материалов | TXT/MD/PDF/DOCX, поиск по подстроке |
| 11 | Rate limit + Audit log + Notifications | in-memory rate limit, audit log всех действий, in-app notifications + SMTP email |
| 12 | Deploy + HTTPS + WS | Docker Compose + Nginx с самоподписанным SSL, WebSocket через прокси |

**API:** 42 REST endpoint + 1 WebSocket. **Frontend:** 7 страниц + PWA. **Тестов:** 64/64.

---

## Стек

- **Backend:** Python 3.12, FastAPI 0.115, SQLAlchemy 2, Alembic, Pydantic v2
- **Frontend:** Next.js 16, React 19, TypeScript strict, Tailwind, PWA manifest
- **Database:** PostgreSQL 16 (12 subjects, 186 topics, 42 subtopics)
- **Reverse proxy:** Nginx 1.27 (HTTPS + WebSocket)
- **Контейнеры:** Docker Compose
- **AI:** MiniMax-M3 через OpenAI-compatible API

---

## Структура

```
ai-tutor/
├── apps/
│   ├── backend/      # FastAPI + Alembic + AI Gateway + WebSocket
│   └── frontend/     # Next.js + PWA
├── data/             # seed, curriculum, uploads
├── deploy/
│   ├── docker-compose.yml
│   ├── nginx/nginx.conf  # HTTP→HTTPS redirect, WebSocket upgrade
│   ├── ssl/             # self-signed certs
│   ├── backup/
│   └── proxmox/
├── docs/             # architecture, security, deployment
├── .env.example
├── Makefile
└── README.md
```

---

## Локальный запуск

```bash
cp .env.example .env  # подставь реальные секреты
make up
```

После старта:
- Frontend: http://localhost:3000
- Backend Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

## Production (192.168.1.86)

```bash
ssh -i ~/.ssh/id_ed25519_kirill_ai root@192.168.1.86
cd /opt/ai-tutor/deploy
docker compose ps                    # статус
docker compose logs -f               # логи
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed --reset
bash /opt/ai-tutor/deploy/backup/backup.sh
```

HTTPS работает из коробки (self-signed, принять в браузере). Для production с реальным доменом:

```bash
bash /opt/ai-tutor/deploy/ssl/generate-self-signed.sh my-domain.com  # placeholder
# Потом настроить certbot:
apt install certbot python3-certbot-nginx
certbot --nginx -d my-domain.com
```

---

## Безопасность

- bcrypt пароли (rounds=12)
- JWT access (24h) + refresh (30d)
- CORS whitelisting через `CORS_ORIGINS`
- Postgres в internal Docker network
- Rate limit AI (30/мин/user, in-memory)
- Sanitize входа/выхода LLM, prompt injection detection
- **AI ключ никогда не в логах/ответах**
- Files: ограничение размера, MIME-проверка, защита от path traversal
- HTTPS с самоподписанным сертификатом (для prod — заменить на Let's Encrypt)
- Audit log всех админских действий и важных событий

---

## Уведомления (Email + In-App)

В `app/notifications/service.py`:
- `notify_parents_of_milestone()` — автоматически вызывается при завершении диагностики
- Если `SMTP_URL` задан в env — отправляется через SMTP (aiosmtplib)
- Если нет — email сохраняется в БД со status=`dry_run`
- Все уведомления дублируются в `notifications` для показа в UI

Для production настрой `SMTP_URL=smtp://user:pass@smtp.gmail.com:587` в `.env`.

---

## Что осталось (на потом)

- **OCR** для изображений в материалах (Этап 10)
- **RAG** для учебных материалов (vector store)
- **Real cert (Let's Encrypt)** — после получения домена
- **Email-to-parent на каждый урок** — не только диагностика
- **Audit log UI** — сейчас только через API
- **WebSocket для других AI endpoints** (chat сейчас, explain/generate TODO)

---

## Финальный E2E smoke test

`/tmp/test_final3.sh` на контейнере проверяет:
1. HTTPS /health
2. HTTP → HTTPS redirect
3. Login
4. AI ping (MiniMax-M3 ok)
5. 42 REST endpoints
6. WebSocket handshake (403 без токена, 200 с токеном)
7. PWA assets
8. 7 frontend страниц
9. 4 контейнера healthy
10. PostgreSQL: 12 subjects, 186 topics

Запускать:
```bash
scp /tmp/test_final3.sh root@192.168.1.86:/tmp/
ssh root@192.168.1.86 'bash /tmp/test_final3.sh'
```

См. `docs/architecture.md`, `docs/security.md`, `docs/deployment.md` для подробностей.

---

## Стек

- **Backend:** Python 3.12, FastAPI 0.115, SQLAlchemy 2, Alembic, Pydantic v2
- **Frontend:** Next.js 16, React 19, TypeScript strict, Tailwind CSS, PWA
- **Database:** PostgreSQL 16 (12 subjects, 186 topics, 42 subtopics)
- **Reverse proxy:** Nginx 1.27
- **Контейнеры:** Docker Compose
- **AI:** MiniMax-M3 через OpenAI-compatible API

---

## Структура репозитория

```
ai-tutor/
├── apps/
│   ├── backend/      # FastAPI + Alembic + AI Gateway
│   └── frontend/     # Next.js + PWA
├── data/             # seed, curriculum, uploads
├── deploy/
│   ├── docker-compose.yml
│   ├── nginx/nginx.conf
│   ├── backup/
│   └── proxmox/
├── docs/             # architecture, security, deployment
├── .env.example
├── Makefile
└── README.md
```

---

## Локальный запуск (для разработки)

```bash
cp .env.example .env  # подставь реальные секреты
make up
```

После старта:
- Frontend: <http://localhost:3000> (или через Nginx на 80)
- Backend Swagger UI: <http://localhost:8000/docs>
- Backend health: <http://localhost:8000/health>

---

## Production (192.168.1.86)

```bash
ssh -i ~/.ssh/id_ed25519_kirill_ai root@192.168.1.86
cd /opt/ai-tutor/deploy
docker compose ps            # статус
docker compose logs -f       # логи
docker compose exec backend alembic upgrade head   # миграции
docker compose exec backend python -m app.scripts.seed --reset  # seed
bash /opt/ai-tutor/deploy/backup/backup.sh          # бэкап
```

---

## Безопасность

- bcrypt пароли (rounds=12)
- JWT access (24h) + refresh (30d)
- CORS whitelisting через `CORS_ORIGINS`
- Postgres изолирован в internal Docker network
- Rate limit AI (30/мин/user, in-memory; для multi-worker → Redis)
- Sanitize входа/выхода LLM, prompt injection detection
- **AI ключ никогда не попадает в логи или ответы**
- Файлы: ограничение размера, MIME-проверка, защита от path traversal
- HTTPS: настроить certbot (TODO Этап 12 polish)

---

## Что осталось (на потом)

- **HTTPS** — certbot в LXC или reverse proxy на host
- **OCR** для изображений (Этап 10)
- **Email-уведомления** родителям (Этап 11)
- **RAG** для учебных материалов (vector store)
- **Audit log** для админ-действий
- **WebSocket** для стриминга ответов AI

См. `docs/architecture.md`, `docs/security.md`, `docs/deployment.md` для подробностей.