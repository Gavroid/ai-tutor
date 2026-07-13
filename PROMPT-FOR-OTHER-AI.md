# 🤖 Промт для изучения проекта AI-репетитор 7 класса

> **Назначение**: Этот документ позволяет другой AI-платформе полностью погрузиться в проект, провести независимый аудит, предложить доработки и/или продолжить разработку. Прочтите этот документ целиком перед началом работы.

---

## 📌 Контекст проекта

**AI-репетитор 7 класса** — это production-ready MVP для репетиторства школьников 7 класса (РФ) по всем 12 предметам программы. Ребёнок регистрируется, выбирает тему и получает от AI объяснения, генерацию задач, проверку ответов и подсказки. AI может работать в 6 режимах (explain, hint, check, generate, diagnose, chat). Родители видят прогресс ребёнка через привязку по invite-коду.

- **Production URL**: https://192.168.1.86 (self-signed HTTPS, Proxmox LXC)
- **Codebase**: `/root/workspace/ai-tutor/`
- **Stack**: FastAPI 0.115 + SQLAlchemy 2 + Next.js 16 + Postgres 16 + Nginx + Redis + Docker Compose
- **AI**: MiniMax-M3 через OpenAI-compatible API
- **Tests**: 136 backend + 12 Playwright E2E (все зелёные)
- **Status**: развёрнут в production, мониторинг работает, backup+offsite+md5 verify работают

---

## 1️⃣ Архитектура проекта

### Технологический стек

**Backend (apps/backend):**
- Python 3.12 + FastAPI 0.115 + SQLAlchemy 2 + Pydantic v2 + Alembic
- 50 файлов Python (~5000 LOC), 17 тестовых файлов (136 тестов)
- Dependencies: bcrypt, jose (JWT), httpx, aiosmtplib, pypdf, python-docx, pytesseract, Pillow, redis, slowapi

**Frontend (apps/frontend):**
- Next.js 16 + React 19 + TypeScript strict + Tailwind CSS
- 12 страниц + PWA (manifest.json + icon.svg + service worker)
- 3 клиентских модуля: api.ts (REST), ws-chat.ts (WebSocket), types/index.ts

**Database (PostgreSQL 16):**
- 7 миграций (0001-0007), 12 таблиц
- Схема: users, student_profiles, parent_student_links, subjects, sections, topics, subtopics, learning_materials, questions, common_mistakes, attempts, mistakes, progress, diagnostic_sessions, diagnostic_answers, audit_logs, notifications, email_notifications, password_reset_tokens

**Infrastructure:**
- Docker Compose: 5 контейнеров (db, backend, frontend, proxy, redis)
- Nginx 1.27: HTTPS reverse proxy с WebSocket upgrade, rate limits (5r/s auth, 30r/s api)
- Redis 7-alpine: rate limiting для multi-worker (login_rl:*, ai_rl:*, ws_rl:*)
- Proxmox LXC: 4 CPU, 4 GB RAM, swap=0

**CI/CD:**
- GitHub Actions: `.github/workflows/tests.yml` + `deploy.yml`
- Backup скрипт с md5 manifest + test-restore.sh
- Мониторинг: cron `*/5 * * * *` для healthcheck + error-rate + smtp-worker

---

## 2️⃣ Структура директорий

```
ai-tutor/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── admin/        # Audit log + admin endpoints (4 файла)
│   │   │   ├── ai/           # AI Gateway: Hermes + Mock + WS + sanitize (8 файлов)
│   │   │   ├── auth/         # JWT + password_reset + oauth (4 файла)
│   │   │   ├── diagnostics/  # Диагностика + expire (4 файла)
│   │   │   ├── materials/    # Upload + OCR (3 файла)
│   │   │   ├── notifications/ # In-app + email retry (4 файла)
│   │   │   ├── parents/      # Invite + link (3 файла)
│   │   │   ├── progress/     # Mastery + attempts (4 файла)
│   │   │   ├── rag.py        # Chunking + embeddings + vector store
│   │   │   ├── rag_router.py # RAG endpoints
│   │   │   ├── subjects/     # 12 subject × 186 topic (5 файлов)
│   │   │   ├── users/        # User + StudentProfile (3 файла)
│   │   │   ├── voice/        # Whisper ASR endpoint
│   │   │   ├── db/           # SQLAlchemy engine
│   │   │   ├── scripts/      # seed.py
│   │   │   ├── main.py       # FastAPI app + middleware
│   │   │   └── config.py
│   │   ├── alembic/versions/ # 7 миграций (0001-0007)
│   │   ├── tests/             # 17 файлов тестов
│   │   └── requirements.txt
│   └── frontend/
│       ├── app/                # 12 страниц
│       ├── lib/                # api.ts, ws-chat.ts
│       ├── types/index.ts
│       ├── public/             # manifest.json, icon.svg, sw.js
│       └── e2e/                # Playwright tests
├── deploy/
│   ├── docker-compose.yml      # 5 services
│   ├── nginx/nginx.conf        # HTTPS + WS + rate limits
│   ├── backup/                 # backup.sh, test-restore.sh, offsite
│   ├── monitoring/             # healthcheck.sh, error-rate.sh
│   ├── smtp/                   # test-smtp.sh, smtp-worker.sh, SETUP.md
│   ├── ssl/                    # generate-self-signed.sh, LETS-ENCRYPT.md
│   ├── docker-daemon.json      # log rotation
│   ├── postgres-init/          # init scripts
│   └── proxmox/                # LXC guides
├── docs/                       # api.md, architecture.md, deployment.md, security.md
├── .github/workflows/          # tests.yml, deploy.yml
├── PROMPT-FOR-OTHER-AI.md      # ← этот файл
└── README.md
```

---

## 3️⃣ Все реализованные фичи

### MVP (12 этапов)

1. **#1 Каркас**: Docker Compose с 5 контейнерами, FastAPI, Next.js, PostgreSQL, Nginx
2. **#2 Авторизация**: JWT (HS256, 24h access + 30d refresh), 4 роли (student/parent/teacher/admin), bcrypt(rounds=12), Refresh token endpoint
3. **#3 Учебная структура**: 12 предметов × 186 тем × 42 подтемы (программа 7 класса РФ)
4. **#4 UI ученика**: 12 страниц + PWA manifest + service worker
5. **#5 AI Gateway**: HermesProvider (OpenAI-compatible), MockProvider, sanitize (regex + injection detection), retry/timeout
6. **#6 AI-репетитор**: 6 режимов (explain, hint, check, generate, diagnose, chat) + WebSocket streaming
7. **#7 Диагностика**: generation questions, heuristic_check (числа + keywords), mastery расчёт, recommendations
8. **#8 Прогресс**: mastery (скользящее среднее), mistakes aggregation, recommend_review
9. **#9 Родительский кабинет**: invite-коды (одноразовые), привязка ребёнка (`/students/link-parent`), отчёты
10. **#10 Загрузка материалов**: TXT/MD/PDF/DOCX парсинг + OCR PNG/JPG через pytesseract
11. **#11 Audit log + Admin + Notifications**: admin endpoints (users, stats, audit, deactivate), in-app + email (aiosmtplib)
12. **#12 Deploy**: Docker Compose + Nginx + HTTPS + WS + backup + monitoring

### Расширения (post-MVP)

- **HTTPS** с self-signed + редирект HTTP→HTTPS
- **WebSocket стриминг** (3 endpoints: chat/explain/generate)
- **Audit log UI** на `/admin` с фильтрами (action, since, until)
- **Nginx rate limits** (auth 5r/s burst=10, api 30r/s burst=20)
- **Login rate limit** (10 попыток / 15 мин на IP) через Redis
- **WS rate limit** (5 concurrent/uid)
- **Password reset flow** с anti-enumeration (всегда 200), SHA256, 1h TTL, 5/час rate limit
- **Email retry** с exponential backoff (3 попытки: 1с, 2с, 4с)
- **Diagnostic expire** (24ч TTL) + admin endpoint `/admin/diagnostics/expire-stale`
- **Multi-worker Redis** rate limiting (login/AI/WS)

### Production hardening (этап после MVP)

- **Backup cron** `0 3 * * *` → pg_dump + uploads → offsite в `/var/backups/ai-tutor/`
- **Backup MD5 manifest** → test-restore.sh проверяет целостность через `md5sum -c`
- **Logrotate** Docker контейнеров (10M × 3 файла max)
- **Healthcheck cron** `*/5 * * * *` (uptime + backup freshness + disk/RAM)
- **Error-rate cron** `*/5 * * * *` (5xx errors / 5min → алерт)
- **SMTP worker cron** `*/5 * * * *` (отправляет queued email-уведомления)
- **Telegram alerts** (готовы, нужны TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)
- **Structured JSON access log** (middleware `access_log`)
- **Audit log IP capture** (ContextVar + middleware)
- **Health endpoint** с version, uptime, started_at
- **WS reconnect** с exponential backoff (500ms→30s, 10 попыток) + heartbeat ping
- **Admin UI tools tab** (test SMTP, force expire)
- **Backend Admin tools**: POST `/admin/notifications/test`, POST `/admin/diagnostics/expire-stale`

### Масштабирование (текущая сессия)

- **OAuth2** (Google/Yandex/GitHub) — Authorization Code flow с CSRF защитой через `state`
- **Voice input** (Whisper ASR) — multipart upload + 3 бэкенда (API/local/stub)
- **RAG** (vector store) — chunking + embeddings + cosine similarity + in-memory store
- **Email per lesson** — milestone notifications (5/10/20/50/100/200/500 attempts)
- **CI/CD** GitHub Actions workflows (tests + deploy)
- **Let's Encrypt** документация (пользователь сделает сам)

---

## 4️⃣ API Reference (50+ endpoints + 3 WebSocket)

### Auth
- `POST /api/v1/auth/register` — регистрация (с защитой от admin self-register)
- `POST /api/v1/auth/login` — JWT pair (access + refresh)
- `POST /api/v1/auth/refresh` — обновить токен (проверяет type claim)
- `GET /api/v1/auth/me` — текущий пользователь
- `POST /api/v1/auth/password-reset/request` — anti-enumeration (всегда 200), max 5/час
- `POST /api/v1/auth/password-reset/confirm` — проверка SHA256 токена, TTL 1ч
- `GET /api/v1/auth/oauth/{provider}/login` — OAuth redirect (Google/Yandex/GitHub)
- `GET /api/v1/auth/oauth/{provider}/callback?code=...` — обмен на JWT
- `GET /api/v1/auth/oauth/providers` — список провайдеров

### AI
- `POST /api/v1/ai/explain` — объяснение темы
- `POST /api/v1/ai/hint` — подсказка к задаче
- `POST /api/v1/ai/check-answer` — проверка с injection detection
- `POST /api/v1/ai/generate-exercise` — генерация задания
- `POST /api/v1/ai/chat` — свободный диалог
- `POST /api/v1/ai/ping` — healthcheck AI
- `WS /ws/ai/chat` — стриминг ответа AI (chunks + done)
- `WS /ws/ai/explain` — стриминг объяснения
- `WS /ws/ai/generate` — стриминг генерации задания

### Subjects / Topics
- `GET /api/v1/subjects` — список 12 предметов (ПУБЛИЧНЫЙ, без auth)
- `GET /api/v1/subjects/{id}/topics` — список тем предмета
- `GET /api/v1/topics/{id}` — детали темы

### Progress
- `POST /api/v1/progress/attempt` — записать попытку (триггер email milestone)
- `GET /api/v1/progress/me` — все темы пользователя с mastery
- `GET /api/v1/progress/mistakes` — агрегированные ошибки
- `GET /api/v1/progress/recommend-review` — темы для повторения

### Diagnostics
- `POST /api/v1/diagnostic/start` — начать сессию
- `POST /api/v1/diagnostic/next` — следующий вопрос
- `POST /api/v1/diagnostic/answer` — ответить
- `POST /api/v1/diagnostic/finish` — завершить (email родителю)

### Parents
- `POST /api/v1/parents/invite` — создать invite код
- `GET /api/v1/parents/me` — профиль родителя
- `GET /api/v1/parents/students` — список детей
- `POST /api/v1/students/link-parent` — привязать ребёнка по коду

### Materials
- `POST /api/v1/materials/upload` — multipart (file + topic_id)
- `GET /api/v1/materials/list` — список
- `GET /api/v1/materials/by-topic/{id}` — материалы темы
- `GET /api/v1/materials/search?q=...` — substring search

### Admin
- `GET /api/v1/admin/stats` — статистика
- `GET /api/v1/admin/users` — список пользователей
- `POST /api/v1/admin/users/{id}/deactivate` — деактивация
- `GET /api/v1/admin/audit-log` — с фильтрами `action`, `user_id`, `since`, `until`
- `POST /api/v1/admin/diagnostics/expire-stale?ttl_hours=24` — force expire
- `POST /api/v1/admin/notifications/test?email=X` — тестовая отправка email

### Notifications
- `GET /api/v1/notifications/me?unread_only=true` — список
- `GET /api/v1/notifications/unread-count` — количество
- `POST /api/v1/notifications/{id}/read` — пометить прочитанным
- `POST /api/v1/notifications/read-all` — пометить все

### Voice / RAG / Meta
- `POST /api/v1/voice/transcribe` — Whisper ASR (file + language)
- `POST /api/v1/rag/index` — индексировать текст
- `POST /api/v1/rag/search` — semantic search (top_k)
- `GET /api/v1/rag/stats`
- `DELETE /api/v1/rag/material/{id}`
- `GET /health` — `{status, service, env, version, uptime_seconds, started_at}`
- `GET /ready` — readiness probe
- `GET /openapi.json`
- `GET /manifest.json`, `/icon.svg`, `/sw.js` — PWA assets

---

## 5️⃣ Конфигурация (env переменные)

### Backend
```
APP_SECRET_KEY=<min 32 chars>
APP_ENV=production|development
DATABASE_URL=postgresql+psycopg2://tutor:pass@db:5432/tutor
CORS_ORIGINS=https://192.168.1.86
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE_MB=20

# AI
AI_BASE_URL=https://api.openrouter.ai/api/v1
AI_API_KEY=<provider key>
AI_MODEL=anthropic/claude-3.5-haiku (or current)
AI_TIMEOUT_SECONDS=30
AI_MAX_RETRIES=2
AI_MAX_INPUT_CHARS=8000

# JWT
JWT_ALGORITHM=HS256
JWT_ACCESS_TTL_MINUTES=1440
JWT_REFRESH_TTL_DAYS=30

# Rate limits
RATE_LIMIT_AI_PER_MINUTE=30
REDIS_URL=redis://redis:6379/0

# Email (optional - dry_run if not set)
SMTP_URL=smtp://user:pass@smtp.example.com:587

# OAuth2 (optional)
OAUTH_GOOGLE_CLIENT_ID=<id>
OAUTH_GOOGLE_CLIENT_SECRET=<secret>
OAUTH_YANDEX_CLIENT_ID=<id>
OAUTH_YANDEX_CLIENT_SECRET=<secret>
OAUTH_GITHUB_CLIENT_ID=<id>
OAUTH_GITHUB_CLIENT_SECRET=<secret>
OAUTH_REDIRECT_BASE=https://192.168.1.86

# Voice (optional)
WHISPER_API_URL=https://api.openai.com
WHISPER_API_KEY=<key>
WHISPER_MODEL=whisper-1

# RAG (optional)
EMBEDDING_MODEL=text-embedding-3-small
```

---

## 6️⃣ Что ещё можно улучшить (TODO планы)

### 🔴 Критический приоритет
1. **Let's Encrypt** — реальный SSL (пользователь сделает сам по `deploy/ssl/LETS-ENCRYPT.md`)
2. **Реальный SMTP** — добавить `SMTP_URL` в `.env` (smtp-worker cron уже готов)
3. **OAuth2 credentials** — зарегистрировать OAuth app у провайдеров
4. **CI/CD с реальным git remote** — push triggers deploy

### 🟡 Высокий приоритет
5. **pgvector вместо in-memory RAG** — заменить in-memory vector store на Postgres + pgvector для persistence
6. **Whisper API credentials** — для реального speech-to-text
7. **Voice input в UI** — добавить кнопку микрофона в `/topics/[id]`
8. **OAuth UI** — кнопки "Login with Google/Yandex" на `/login`

### 🟢 Средний приоритет
9. **RAG в AI чат** — добавить retrieved chunks в context для AI промптов
10. **Email templates** — HTML вместо plaintext
11. **Telegram бот для родителей** — отправлять прогресс не только email, но и в Telegram
12. **Multi-worker uvicorn** — сейчас 1 worker, для нагрузки нужно Redis (уже есть)
13. **WebSocket для explain/generate** в UI — сейчас только chat через WS
14. **OAuth refresh tokens** — сейчас только initial JWT, нет rotation

### 🔵 Низкий приоритет (фичи)
15. **OAuth2 (Facebook, Apple)** — добавить провайдеров
16. **Voice-to-voice** — ребёнок говорит → ASR → AI → TTS (text-to-speech)
17. **Push notifications** (web push)
18. **i18n** — английский язык для интерфейса
19. **Dark mode**
20. **Mobile PWA** (offline mode)
21. **Teacher role UI** — сейчас роль есть в БД, но нет UI
22. **Геймификация** (streak, badges, лидеры)
23. **Расписание / напоминания** (cron-driven push)
24. **RAG embeddings upgrade** — pgvector + sentence-transformers (локально)
25. **Mocking AI для тестов** — лучше mock provider, текущий mock упрощён
26. **Audit log retention policy** — удалять старше 90 дней

### 🟡 Архитектурные улучшения
27. **Celery + Redis** для background tasks (вместо прямых cron)
28. **Pydantic Settings** с явной типизацией env
29. **OpenAPI client SDK** generation
30. **GraphQL** alternative API (вместо REST)
31. **gRPC** для internal service communication
32. **WebSocket compression** для больших payloads

### 🔵 UX
33. **PWA offline mode** — кэш страниц и AI ответов
34. **Markdown в AI ответах** — рендеринг форматирования
35. **AI streaming render** — typewriter effect
36. **Dark mode toggle** в UI
37. **Accessibility** (a11y) — WCAG AA

### 📊 Мониторинг / Observability
38. **Prometheus metrics** для backend
39. **Grafana dashboard** для визуализации
40. **Loki/ELK** для логов
41. **Sentry / OpenTelemetry** для error tracking
42. **Real-time metrics** в `/admin` (active users, AI requests/min, etc.)

### 🧪 Тесты
43. **Frontend unit tests** (vitest)
44. **E2E больше сценариев** (Playwright)
45. **Load tests** (locust)
46. **Security audit** (OWASP ZAP)

### 📦 DevOps
47. **Helm chart** для K8s
48. **Ansible playbook** для прод
49. **Terraform** для инфры
50. **Multi-region deployment**

---

## 7️⃣ Известные проблемы / Caveats

### Архитектурные
1. **In-memory RAG store** — теряется при рестарте backend. Нужна БД (pgvector) или Qdrant.
2. **Single-worker backend** — нужен Redis (есть) и `uvicorn --workers 4` для production load.
3. **HTTP/2 отключён в nginx** — для WebSocket совместимости (Workaround: HTTP/1.1 для /api/, HTTP/2 для статики).
4. **Self-signed HTTPS** — пользователь сделает Let's Encrypt сам.

### Код
5. **Audit log IP** — захватывается через middleware, но есть edge cases (proxies, X-Forwarded-For trust).
6. **Email retry exponential backoff** — 1с/2с/4с. Для долгих SMTP таймаутов может быть недостаточно.
7. **RAG hash fallback** — не настоящий embedding, используется только если нет API key.
8. **WS reconnect** — max 10 попыток, после этого нужно перезагрузить страницу.
9. **Materials upload** — требует multipart form, нельзя через curl без `--form`.

### Безопасность
10. **JWT secret rotation** — нет автоматической ротации.
11. **SQL injection** — используется SQLAlchemy ORM, всё ОК.
12. **XSS** — React эскейпит по умолчанию, ОК.
13. **CSRF** — для OAuth есть `state` параметр, для обычных форм нет CSRF tokens (но есть JWT в Authorization header).

### Конфигурация
14. **Нет .env.example** — есть, но некоторые переменные могут отсутствовать.
15. **Нет rate limit на /auth/register** — может быть abuse.
16. **Docker Hub rate limits** — могут быть проблемы при pull на shared IP.

---

## 8️⃣ Связанные skill (Hermes Agent)

`~/.hermes/skills/devops/ai-tutor-deploy/SKILL.md` содержит:
- Подробный runbook (как deploy, как дебажить)
- Каталог из 23+ pitfalls (Proxmox LXC, scp issues, test pollution, logrotate, etc.)
- Cron jobs описание
- Backup/restore инструкции
- WS reconnect, OAuth2, RAG, Voice, Email per lesson архитектура

---

## 9️⃣ Команды для работы с проектом

```bash
# SSH to prod
ssh -i /root/.ssh/id_ed25519_kirill_ai root@192.168.1.86

# Project dir
cd /opt/ai-tutor/

# Backend tests
cd apps/backend && . .venv/bin/activate && \
  APP_SECRET_KEY=test-secret-key-for-pytest-only-1234567890 \
  APP_ENV=development \
  DATABASE_URL=sqlite+pysqlite:///:memory: \
  CORS_ORIGINS=http://localhost:3000 AI_API_KEY=mock-key-for-tests \
  UPLOAD_DIR=/tmp/ai-tutor-test-uploads \
  pytest --tb=line -q

# Frontend tests
cd apps/frontend && npx playwright test --reporter=list --workers=1

# Health check
curl -sk https://192.168.1.86/health | python3 -m json.tool

# Logs (monitoring)
tail -f /var/log/ai-tutor-monitor.log

# Backup + test restore
bash /opt/ai-tutor/deploy/backup/test-restore.sh

# Redis check
docker exec deploy-redis-1 redis-cli KEYS "*"

# Container stats
docker stats --no-stream
```

---

## 🔟 Тестовые креды (production)

- **Student**: `kirill@example.com` / `strongpass1`
- **Admin**: `admin@example.com` / `strongpass1`
- **URL**: https://192.168.1.86 (self-signed cert)

---

## 1️⃣1️⃣ Главные задачи для AI-аудитора

Если ты — AI-аудитор, вот конкретные вопросы для анализа:

### Безопасность
1. **OAuth2 state parameter** — правильно ли валидируется CSRF защита?
2. **JWT secret rotation** — есть ли механизм?
3. **Rate limits** — могут ли быть bypass при смене IP через X-Forwarded-For?
4. **Materials upload** — есть ли virus scan, MIME validation?
5. **SQL injection** — все ли запросы используют ORM?
6. **Audit log retention** — что происходит через год?

### Производительность
7. **In-memory RAG store** — как масштабируется? O(N) на каждый search?
8. **Embeddings** — кешируются ли?
9. **N+1 queries** — есть ли в progress/parents?
10. **AI timeout 30s** — что если пользователь ждёт?

### Архитектура
11. **Single-worker uvicorn** — почему не multi-worker? Redis готов.
12. **Self-signed HTTPS** — почему не Let's Encrypt (пользователь делает)?
13. **In-memory store для RAG** — почему не pgvector?
14. **Backup MD5** — что если backup corrupt во время записи?

### UX
15. **Login form** — нет 2FA
16. **WS reconnect** — что показывается после 10 неудач?
17. **AI streaming** — что если chunk corrupt JSON?
18. **Materials OCR** — что для PDF с картинками внутри?

### DevOps
19. **CI/CD без git remote** — почему webhook не сделан?
20. **Backup retention 14 дней** — достаточно?
21. **Logrotate 10M×3** — может терять важные логи
22. **Нет alerting на offline Redis** — что если Redis упадёт?

### Бизнес-логика
23. **AI temperature/tokens** — захардкожены где?
24. **Diagnostics questions generation** — что если AI генерирует ерунду?
25. **Mastery formula** — правильно ли считает?
26. **Password reset email** — содержит ли токен в URL или в теле?

---

## 1️⃣2️⃣ Рекомендуемые доработки (мой wishlist)

### Если бы я делал проект с нуля
1. Использовать **pgvector** с самого начала для RAG (вместо in-memory).
2. **Multi-worker из коробки** — uvicorn с 4 workers + Redis-ready.
3. **OpenTelemetry** для трейсинга (вместо JSON логов).
4. **React Query / SWR** для frontend (вместо ручных fetch).
5. **Pydantic v2 strict mode** — везде.
6. **TypeScript strict everywhere** — включая Next.js config.
7. **Git remote с первого дня** — даже если приватный.
8. **Terraform** для инфры — повторяемость.

### Что бы добавил прямо сейчас
- **WebSocket admin monitoring** — реальное время, сколько соединений
- **Dashboard для родителей** — графики прогресса, экспорт в PDF
- **A/B тесты промптов** — какая формулировка даёт лучшие ответы
- **Embedded whiteboards** — для объяснения геометрии/физики
- **Голосовые ответы** (TTS) — для маленьких детей

---

## 1️⃣3️⃣ Связь с пользователем

Проект делается для **Игоря** (Kirill — 13 лет, T1D, 7 класс) — это его репетитор для школьной программы. Production сервер — домашний LXC на Proxmox (192.168.1.86). Telegram: подключен.

Что важно:
- Ребёнок пользуется сам → UX > features
- Локальный сервер → нет облачных зависимостей
- Audit log важен для родителей (что делает ребёнок)
- Email уведомления — чтобы родители знали прогресс
- Производительность критична — AI ответы должны быть быстрыми

---

## 1️⃣4️⃣ Финальный чеклист для AI-агента

Если ты анализируешь этот проект, проверь:

- [ ] Прочитал ли ты README.md?
- [ ] Проверил ли ты `apps/backend/app/main.py` для понимания структуры?
- [ ] Понял ли ты как работает AI flow (sanitize → prompt → Hermes provider → response → sanitize)?
- [ ] Понял ли ты как работает WebSocket (handshake → JWT verify → payload → stream chunks)?
- [ ] Проверил ли ты тесты — все ли зелёные?
- [ ] Прочитал ли ты `deploy/ssl/LETS-ENCRYPT.md`?
- [ ] Прочитал ли ты `deploy/CICD.md`?
- [ ] Проверил ли ты cron jobs?
- [ ] Проверил ли ты backup + restore?
- [ ] Проверил ли ты monitoring (healthcheck, error-rate)?

Если да — ты готов к анализу и предложениям!

---

## 1️⃣5️⃣ Контактные данные (production)

- **URL**: https://192.168.1.86
- **SSH**: `ssh -i /root/.ssh/id_ed25519_kirill_ai root@192.168.1.86`
- **Project path**: `/opt/ai-tutor/`
- **Workspace**: `/root/workspace/ai-tutor/`
- **Production cron**:
  - `0 3 * * *` backup + backup-verify (пн 04:00)
  - `*/5 * * * *` healthcheck
  - `*/5 * * * *` error-rate
  - `*/5 * * * *` smtp-worker
  - `/etc/cron.d/ai-tutor-audit-cleanup` ежедневно 03:00 (Sprint 4.2)
  - `/etc/cron.d/ai-tutor-weekly-summary` вс 18:00 MSK (Sprint 9.1)
  - `/etc/cron.d/ai-tutor-backup-verify` пн 04:00 (Sprint 10.4)

- **Секреты**: `/etc/ai-tutor/.env` (chmod 600, root:root) — для cron-задач

---

## 1️⃣6️⃣ Обновлено: июль 2026 — Sprint 6-10 завершены

После первого промта (Sprint 1-5) проект прошёл через 5 дополнительных спринтов автоматизированной работы. Ниже — сводка для AI, проводящей аудит (см. также `docs/plans/SPRINT-6-PLAN.md`).

### Что нового (Sprint 6-10)

- **Sprint 6 (P0 — Надёжность прод)**:
  - 6.4 Cron-секреты вынесены в `/etc/ai-tutor/.env` (600), inline-пароли убраны
  - 6.5 SSL зафиксирован: self-signed (LAN-only, threat model в `deploy/ssl/LETS-ENCRYPT.md`)
  - 6.1 CI/CD: workflows есть, отдельный SSH-ключ `id_ed25519_cicd` (ТРЕБУЕТ GitHub-репо)
  - 6.6 Backup verify: smoke test-restore прошёл (3 users, 12 subjects, 186 topics, 17 audit logs)

- **Sprint 7 (UX ученика — для T1D)**:
  - 7.1 Markdown-рендер AI-ответов (server `markdown-it-py` + client минимальный парсер) с защитой от XSS
  - 7.2 Кнопка микрофона (MediaRecorder API) → POST `/voice/transcribe` с rate-limit 20/мин/user
  - 7.3 Автосохранение урока: миграция `0010_topic_drafts`, localStorage каждые 5с + сервер каждые 15с
  - 7.4 Hint с 3 уровнями (наводящий / подсказка / разбор)
  - 7.5 Баджи за УСИЛИЕ (10 баджей, миграция `0011_badges`, UI `/student/badges`, **НИКАКИХ streak'ов**)
  - 7.6 E2E полный цикл в `e2e/student.spec.ts`

- **Sprint 8 (AI-качество)**:
  - 8.1 Structured output + retry (3 попытки для teacher-генерации)
  - 8.2 Чекеры `app/practice/checkers.py`: numeric + keyword + exact
  - 8.3 RAG embedding cache: миграция `0012_rag_chunks`, hash-fallback для MiniMax
  - 8.4 `record_ai_request()` во всех 5 режимах + `ai_parse_status_total`
  - 8.5 CAT адаптивная диагностика: `app/diagnostics/cat.py`, θ-обновление после каждого ответа

- **Sprint 9 (Родитель+Админ)**:
  - 9.1 Weekly summary email: cron вс 18:00 MSK, HTML f-string шаблон
  - 9.2 Multi-child UI: сохранение выбора в localStorage
  - 9.3 Real-time /admin: WS `/api/v1/admin/ws` + UI `/admin/realtime` с KPI dashboard
  - 9.4 AI-бюджет: `app/ai/budget.py` (Redis + in-memory fallback, 200 req / 200K токенов/день)
  - 9.5 **Добавлены контейнеры Prometheus + Grafana** (теперь 7/7 healthy)

- **Sprint 10 (Техдолг)**:
  - 10.1 JWT в httpOnly cookie: `ai_tutor_access` + `ai_tutor_refresh` (Secure+SameSite=Lax)
  - 10.3 `/api/v2` каркас (готов для breaking changes)
  - 10.4 Backup verify автоматизирован (cron)
  - 10.5 E2E parent dashboard

### Метрики на 2026-07-13

- Backend tests: **405 passed** (было 247 — +158 за Sprint 6-10)
- Миграции: 0010-0012 (3 новых поверх 0009)
- HTTP endpoints: ~85 REST + 5 WS (admin + ai-chat-WS + realtime + 2 open)
- UI pages: 14 (admin/, parent/, parents/, student/badges, subjects/, topics/, teacher/, login, register, diagnostic, link-parent, forgot-password, root)
- Cron jobs: 8 (4 базовых + audit_cleanup + weekly_summary + backup-verify + timezone-setup)
- Контейнеры: **7/7 healthy** на `192.168.1.86`
- Memory: ~398MB / 4GB (10%)
- Git: `main` ветка, 12+ коммитов

### Что осталось (внешние блокеры)

1. **Telegram-алерты (6.2)** — нужен `TELEGRAM_BOT_TOKEN/CHAT_ID` от владельца
2. **Реальный offsite backup (6.6)** — нужен `BACKUP_OFFSITE_DEST` (сейчас копирует в ту же папку)
3. **GitHub-репо (6.1)** — нужен приватный remote + secrets `PRODUCTION_HOST/PRODUCTION_SSH_KEY`
4. **pgvector (8.3)** — текущая реализация: embeddings cache в SQLite (hash-fallback для MiniMax). Если у MiniMax появится `/embeddings`, можно подключить. Альтернатива — pgvector с локальной моделью, но риск OOM на 4GB.

### Backlog идеи (НЕ из плана, но интересные)

- AI-judge для semantic чекеров (`checker_type=semantic`) — сейчас placeholder
- IRT 2PL для адаптивной диагностики (заменит heuristic CAT)
- Zustand для frontend state management (см. `PLAN` 10.2)
- TTS (text-to-speech) — озвучка ответов AI для T1D-ученика (отложено: см. PROMPT)
- Оффлайн-PWA (для ненадёжного интернета на даче)
- Multi-tenant: расширение на других семей / школьный SaaS (требует security review)

---

**Конец промта.** Этот документ создан для того, чтобы другая AI-платформа могла полностью погрузиться в проект, провести аудит и предложить улучшения. Если что-то непонятно — спроси, и я уточню.
