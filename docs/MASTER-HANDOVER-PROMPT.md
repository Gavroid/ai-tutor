# 🚀 AI-репетитор 7 класса — Master Handover Prompt

> **Назначение документа**: эта страница — единственная точка входа для сторонней
> AI-платформы, которая должна: (а) понять проект целиком, (б) провести независимый
> аудит, (в) предложить идеи по доработкам, новым фичам и улучшениям, (г) при желании —
> продолжить разработку самостоятельно.
>
> Прочти целиком. Спроси, если что-то непонятно. Не выдумывай — уточни.

---

## 📋 TL;DR для быстрого старта

Проект — **персональный AI-репетитор** для ученика 7 класса (12-13 лет) с диагнозом
T1D (диабет 1 типа). Семейное использование: 1 admin (родитель-разработчик), 1 parent,
1 student, 0–2 teachers. Production — self-hosted на Proxmox LXC домашней сети.

| Параметр | Значение |
|---|---|
| **Production URL** | `https://192.168.1.86` (self-signed cert, LAN-only) |
| **Backend** | FastAPI 0.115 + SQLAlchemy 2 + Postgres 16 + Redis 7 |
| **Frontend** | Next.js 16 (App Router) + React 19 + TS strict + Tailwind |
| **AI провайдер** | MiniMax-M3 через OpenAI-compatible HTTP API |
| **Test coverage** | 405 backend pytest pass; 15+ Playwright E2E |
| **Контейнеры** | 7/7 healthy (backend, frontend, db, redis, proxy, prometheus, grafana) |
| **RAM** | ~398MB / 4GB (10% — много headroom) |
| **Cron** | 8 jobs (backup, verify, audit_cleanup, weekly_summary, monitoring × 3) |
| **Спринтов завершено** | **10/10** (Sprint 1-10, июль 2026) |
| **Git** | `main` ветка, ~12 коммитов за спринты 6-10 |
| **CI/CD** | workflows есть, требует GitHub-репо (внешний блокер) |

---

## 🎯 1. КОНТЕКСТ И ФИЛОСОФИЯ ПРОДУКТА

### Кто пользователь

**Главный пользователь — Кирилл, 13 лет, T1D.** Проживает в Москве, учится в 7 классе.
Каждое занятие — после школы, 30-60 минут, чтобы **разобрать и зафиксировать** школьные
темы через практику (не через лекции). Приоритет №1 — практические задачи.

T1D накладывает ограничения:
- **Короткие сессии**, нельзя блокировать ученика таймером/дедлайном.
- **Никаких streak'ов** (T1D = ребёнок может пропустить занятия из-за болезни).
- **Нельзя давить** через «соревнование с одноклассниками», «ты отстаёшь», «ты упал
  в рейтинге».
- **Гипо/гипер** могут снижать концентрацию → интерфейс должен прощать ошибки ввода.
- **Автосохранение** критично: эпизод гипо/гипер → урок прерывается → прогресс не теряется.

### Зачем AI-репетитор (а не обычный, типа Skysmart)

- **Репетитор под рукой 24/7** — Кирилл может прийти и спросить в 11 вечера.
- **Персонализация** — AI подстраивается под уровень (через SM-2 + CAT-адаптивную диагностику).
- **Без стыда** — ребёнок может переспросить одно и то же 10 раз без потери лица.
- **Фокус на практике** — не просто объяснить, а дать задачу, проверить, разобрать ошибку.

### Что НЕ планируется (out of scope)

- Другие классы (8-11, ЕГЭ/ОГЭ) — **только 7 класс**.
- Многопользовательский SaaS — **только семья**.
- Мобильное приложение — **только браузер**.
- Аналитика поведения / ML персонализация — философия: минимум данных, максимум пользы.
- Открывать сервис другим семьям — **закрытая коробка для семьи**.

---

## 📐 2. АРХИТЕКТУРА

### 2.1 Архитектурная диаграмма

```
                ┌─────────────────────────────────────────┐
                │  Proxmox LXC 192.168.1.86 (4GB RAM)        │
                │  Docker Compose (7 контейнеров)              │
                │                                                │
   HTTPS (LAN)  │  ┌────┐ ┌────────┐ ┌───────┐                  │
   :443  ───────┼─▶│proxy│▶│backend │▶│ db   │─── Postgres 16  │
                │  │Nginx│ │FastAPI │ │ Redis │── Redis 7       │
                │  │/TLS │ │+uvicorn│ │7/7 up │                  │
                │  └────┘ └────────┘ └───────┘                  │
                │    │       │   │                               │
                │    │       │   ▼                               │
                │    │       │  ┌─────────────┐                  │
                │    │       │  │  MiniMax-M3 │ ── AI API       │
                │    │       │  │   (cloud)   │                  │
                │    │       │  └─────────────┘                  │
                │    │       ▼                                   │
                │    │   ┌──────────────────┐                  │
                │    │   │  frontend         │                  │
                │    └──▶│ Next.js 16 + R19  │                  │
                │        │ + Markdown parser │                  │
                │        └──────────────────┘                  │
                │         ┌───────────┐  ┌────────┐              │
                │         │Prometheus  │  │Grafana  │              │
                │         └───────────┘  └────────┘              │
                └─────────────────────────────────────────┘
                              │
                              ▼  HTTPS scrape /metrics
                         MiniMax API (AI провайдер)
```

### 2.2 Стек

**Backend (`apps/backend/`)**:
- Python 3.12, FastAPI 0.115, uvicorn 0.32
- SQLAlchemy 2, Alembic (12 миграций: 0001..0012)
- Pydantic v2 (Settings + schemas)
- prometheus-client 0.21 (метрики)
- pydantic-settings 2.7 (конфиг через env)
- passlib + bcrypt (auth, rounds=12)
- python-jose (JWT)
- httpx 0.28 (proxy к AI)
- markdown-it-py 3.0 (Sprint 7.1, server-render AI-ответов)
- redis 5.2 (Sprint 9.4 budget + multi-worker rate-limit)

**Frontend (`apps/frontend/`)**:
- Next.js 16.2 (App Router, Turbopack)
- React 19 + TypeScript strict
- Tailwind CSS 3.4
- Минимальный собственный markdown-парсер (`lib/markdown.ts`, ~200 строк)
- WebSocket клиент для /api/v1/admin/ws (`lib/admin-ws.ts`)
- React hooks — **нет** Zustand/Redux/Jotai (открытая задача 10.2)

**Infra**:
- Docker Compose 5→7 контейнеров
- Nginx 1.27 (proxy, self-signed cert, LAN whitelist для `/grafana/`)
- Postgres 16 alpine
- Redis 7 alpine (--maxmemory 64mb)
- Prometheus v2.55 (scrape backend `:8000/metrics`)
- Grafana 11.3 (provisioned datasource + 1 dashboard JSON)
- Proxmox LXC (4 CPU, 4GB RAM, swap=0 — см. pitfalls)

**AI провайдер**: MiniMax-M3 через OpenAI-compatible HTTP API. **Нет /embeddings** —
все «embeddings» через SHA256 hash-fallback (детерминированный псевдо-вектор).

### 2.3 Структура репозитория

```
/root/workspace/ai-tutor/
├── README.md                       503 строк — обзор
├── CHANGELOG.md                    368 строк — история Sprint 1-5
├── MASTER-HANDOVER-PROMPT.md     ~742 строки — полный handover (Pilot Core Stage 1, актуальный)
├── AI-DEEP-AUDIT-PROMPT.md         990 строк — глубокий AI-аудит
├── QUICK-START.md                  162 строки — краткая справка
├── Makefile                        — стандартные команды
├── .git/                           — main ветка, ~12 коммитов
│
├── apps/
│   ├── backend/
│   │   ├── app/                    — Python-код (структурирован по доменам)
│   │   │   ├── ai/                 — AI-провайдеры, service, бюджет, RAG, markdown
│   │   │   ├── auth/               — security, router, oauth, password_reset
│   │   │   ├── admin/              — admin endpoints + realtime WS
│   │   │   ├── user/registration + login/rbac
│   │   │   ├── student/            — drafts, badges (Sprint 7.5)
│   │   │   ├── teacher/            — AI-материалы, workflow draft→approved→published
│   │   │   ├── parent/             — дашборд, privacy 404
│   │   │   ├── diagnostics/        — CAT адаптивная (Sprint 8.5)
│   │   │   ├── progress/           — SM-2 spaced repetition
│   │   │   ├── practice/           — чекеры (Sprint 8.2)
│   │   │   ├── rag.py + rag_persist.py + rag_models.py
│   │   │   ├── v2/                 — /api/v2 каркас
│   │   │   ├── notifications/weekly.py (Sprint 9.1)
│   │   │   ├── observability.py    — Prometheus metrics
│   │   │   ├── config.py           — pydantic-settings
│   │   │   └── db/session.py       — SQLAlchemy session
│   │   ├── alembic/versions/       — 12 миграций
│   │   ├── tests/                  — 40 файлов, 250+ pytest тестов
│   │   ├── requirements.txt        — locked версии
│   │   └── Dockerfile
│   │
│   └── frontend/
│       ├── app/                    — Next.js App Router (14 страниц)
│       │   ├── page.tsx            — root
│       │   ├── login/, register/, forgot-password/
│       │   ├── diagnostic/         — адаптивная диагностика
│       │   ├── subjects/[id]/       — список предметов/тем
│       │   ├── topics/[id]/        — главная страница ученика (chat + practice)
│       │   ├── teacher/            — генерация материалов через AI
│       │   ├── parents/ + parent/dashboard/[studentId]/  — для родителя
│       │   ├── student/badges/     — Sprint 7.5
│       │   ├── admin/ + admin/realtime/  — Sprint 9.3
│       │   └── link-parent/
│       ├── components/             — SafeMarkdown.tsx и др.
│       ├── lib/                    — api.ts, markdown.ts, admin-ws.ts
│       ├── e2e/                    — Playwright (smoke, teacher, parent, student)
│       └── package.json
│
├── deploy/
│   ├── docker-compose.yml          — 7 сервисов
│   ├── nginx/nginx.conf
│   ├── prometheus/prometheus.yml
│   ├── grafana/{provisioning,dashboards}/
│   ├── backup/                     — backup.sh, test-restore.sh, offsite.sh
│   ├── monitoring/                 — healthcheck.sh, error-rate.sh
│   ├── smtp/smtp-worker.sh
│   ├── ssl/LETS-ENCRYPT.md
│   ├── cron/audit_cleanup.py
│   ├── proxmox/                    — заметки по деплою
│   └── CICD.md
│
├── docs/
│   ├── ROADMAP.md                  — Sprint 1-5 план
│   ├── architecture.md
│   ├── api.md
│   ├── security.md
│   ├── deployment.md
│   ├── sprint-4.md
│   ├── plans/SPRINT-6-PLAN.md      — Sprint 6-10 план (561 строк)
│   └── MASTER-HANDOVER-PROMPT.md   — ВОТ ЭТОТ ДОКУМЕНТ
│
├── deploy/ssl/certs/               — self-signed (fullchain.pem + privkey.pem)
└── (etc.)
```

---

## 🔧 3. BACKEND — ДЕТАЛЬНО

### 3.1 Таблицы БД (12 миграций, ключевые поля)

| Миграция | Таблица | Назначение |
|---|---|---|
| 0001 | `users`, `student_profiles`, `parent_student_links` | пользователи |
| 0002 | `subjects`, `sections`, `topics`, `learning_materials`, `questions` | программа 7 класса |
| 0003 | `attempts`, `mistakes`, `progress` | попытки и прогресс |
| 0004 | `diagnostic_sessions`, `diagnostic_answers` | сессии диагностики |
| 0005 | `audit_logs` | аудит (5xx → автоматически) |
| 0006 | `notifications`, `email_notifications` | email-уведомления |
| 0007 | `password_reset_tokens` | сброс пароля |
| 0008 | `learning_materials.status` enum + workflow поля | Sprint 1 |
| 0009 | `progress.{next_review_at, last_reviewed_at, review_count, easiness_factor}` | SM-2 (Sprint 2) |
| **0010** | **`topic_drafts`** | автосохранение урока (Sprint 7.3) |
| **0011** | **`badge_definitions`, `user_badges`** | баджи (Sprint 7.5) |
| **0012** | **`rag_chunks`, `embedding_cache`** | RAG persistence (Sprint 8.3) |

### 3.2 HTTP API (~85 REST + 5 WS)

#### Auth (5 endpoints, `/api/v1/auth/*`)
- `POST /auth/login` → JWT access + refresh + **httpOnly cookies** (Sprint 10.1)
- `POST /auth/refresh` → rotation, поддерживает body ИЛИ cookie (Sprint 10.1)
- `POST /auth/logout` → clear cookies (Sprint 10.1)
- `GET /auth/me` → current user
- `POST /auth/register` → создание (rate-limited)
- OAuth2: `/api/v1/auth/oauth/{provider}/*` (Google/Yandex/GitHub, Sprint X)

#### AI (`/api/v1/ai/*`)
- `POST /ai/explain` → объяснение темы (markdown → HTML, Sprint 7.1)
- `POST /ai/chat` → свободный диалог (с историей)
- `POST /ai/hint` → подсказка с `level: 1|2|3` (Sprint 7.4)
- `POST /ai/check-answer` → проверка ответа (is_correct, score, explanation)
- `POST /ai/generate-exercise` → сгенерировать задачу (structured output, Sprint 8.1)
- `GET /ai/ping` → health
- `GET /ai/budget/usage` → текущее использование (Sprint 9.4)
- `GET /ai/admin/budget/top` → top-users (admin only)

#### Student (`/api/v1/student/*`)
- `GET /materials` → опубликованные (ученик видит только status=published)
- `GET /materials/{id}` → детали
- `PUT /topics/{id}/draft` → автосохранение (Sprint 7.3)
- `GET /topics/{id}/draft` → восстановление
- `DELETE /topics/{id}/draft` → clear (идемпотентно, 204)
- `GET /badges` → 10 баджей с статусом (Sprint 7.5)
- `POST /badges/evaluate` → переоценка (возвращает freshly awarded)

#### Parent (`/api/v1/parents/*`)
- `POST /invite` → код привязки
- `GET /children` → N привязанных детей (multi-child, Sprint 9.2)
- `GET /students/{id}/dashboard` → расширенный дашборд
- `GET /students/{id}/dashboard.pdf` → HTML для печати
- `GET /children/{id}` → краткий обзор

#### Teacher (`/api/v1/teacher/*`)
- `POST /materials/generate` → AI-генерация 9-блокового материала (Sprint 1.2, retry Sprint 8.1)
- `GET /materials` → список с фильтрами
- `PATCH /materials/{id}` → редактирование
- `POST /materials/{id}/approve` → `ai_generated → teacher_approved`
- `POST /materials/{id}/publish` → `teacher_approved → published`
- `DELETE /materials/{id}` → soft delete (RBAC)

#### Admin (`/api/v1/admin/*`)
- `GET /users`, `PATCH /users/{id}/deactivate`
- `GET /audit-log`, `POST /audit-log/purge` (TTL по умолчанию 90 дней)
- `GET /stats`, `POST /diagnostics/expire-stale`, `POST /notifications/test`
- `WS /admin/ws` → real-time метрики (Sprint 9.3, admin only)

#### V2 каркас (`/api/v2/*`, Sprint 10.3)
- `GET /v2/health`, `GET /v2/info` — namespace exists
- Пока пустой — готов для breaking changes

#### Прочее
- `POST /voice/transcribe` → audio → text (rate-limit 20/мин, Sprint 7.2)
- `WS /ws/ai/explain` (legacy)
- `WS /ws/ai/ws` (chunked)
- `POST /rag/{index,search}`, `GET /rag/stats`
- `POST /diagnostic/start`, `GET /diagnostic/{sid}/next`, `POST /diagnostic/{sid}/answer`
- `GET /progress/due-for-review` (SM-2), `POST /progress/review-result`
- `GET /metrics` (Prometheus exposition)

### 3.3 RBAC

| Роль | Доступ |
|---|---|
| `student` | `/student/*`, `/api/v1/ai/*` (с budget), `/api/v1/auth/me` |
| `parent` | + `/parents/*` (только свои дети, privacy 404) |
| `teacher` | + `/teacher/*` (только свои материалы) |
| `admin` | + `/admin/*` + `/api/v1/ai/admin/budget/top` + WS `/admin/ws` |

Реализация: `app/common/deps.py` → `require_admin()`, `require_parent()`, `require_teacher_or_admin()`, `require_teacher()`.

### 3.4 Безопасность

- bcrypt rounds=12, JWT HS256, 24h access + 30d refresh
- **JWT в httpOnly cookie** (Sprint 10.1) с `Secure`/`SameSite=Lax`. В тестах/dev — Secure=False чтобы ASGI TestClient пропускал через http://.
- Rate-limit: Redis-backed для multi-worker (Sprint X), in-memory fallback для single-worker (Sprint 9.4 budget)
- XFF-trust: `TRUSTED_PROXIES` (CIDR) — `TRUSTED_PROXIES=""` → XFF игнорируется
- Audit log: автозапись всех 5xx, `audit_log_purge` после 90 дней
- `_client_ip()` хелпер — используется для rate-limit
- Sanitize user input через `app/ai/sanitize.py` (anti-prompt-injection)
- Запрет eval/secret в логах через `sanitize_output()`

### 3.5 Транзакции и миграции

- `Base.metadata.drop_all` + `create_all` в тестах (через `_reset_state`)
- `conftest.py`: `app.config.get_settings.cache_clear()` (pydantic кэш)
- Alembic: `batch_alter_table` для SQLite-совместимости

---

## 🎨 4. FRONTEND — ДЕТАЛЬНО

### 4.1 Стек

Next.js 16.2 (App Router, Turbopack), React 19, TypeScript strict, Tailwind CSS 3.4.
Без UI-библиотек (shadcn, MUI), без state management (zustand, redux), без роутера (только Next).

### 4.2 Страницы (14)

| Путь | Описание | Sprint |
|---|---|---|
| `/` | Главная — список предметов | 1 |
| `/login`, `/register`, `/forgot-password` | Auth flow | 1 |
| `/subjects`, `/subjects/[id]` | Browse curriculum 7 класса | 1 |
| `/topics/[id]` | **Главная страница ученика** — chat (markdown WS-stream) + practice cycle (с автосохранением) + микрофон + backdraft restore | 1, 7.1, 7.2, 7.3 |
| `/teacher` | Список материалов учителя | 1 |
| `/teacher/generate` | 3-step мастер генерации | 1 |
| `/teacher/materials/[id]` | Detail + approve/publish | 1 |
| `/diagnostic` | CAT-адаптивная диагностика | 8.5 |
| `/parents` | Список привязанных детей + выбор | 9.2 |
| `/parent/dashboard/[studentId]` | KPI дашборд родителя (subject_mastery, streak, mistakes, daily_activity) | 3 |
| `/student/badges` | **Список баджей** (за усилие, не за streak) — earned/locked карточки | 7.5 |
| `/admin` | Audit log + Users + Stats + Tools | 1, 5 |
| `/admin/realtime` | **Real-time KPI dashboard** через WS (AI токены, вызовы, 5xx, system status) | 9.3 |
| `/link-parent` | Привязка ученика к родителю через код-инвайт | 3 |

### 4.3 Hot-path: `/topics/[id]` (главная страница ученика)

Клиент-сайд:
1. `api.topic(topicId)` → загрузка метаданных
2. `useChatStream(token)` → WebSocket stream (chunks)
3. Кнопки «Объясни» → `api.aiExplain(topicId)` → markdown рендерится с typewriter
4. Кнопка «Дай задание» → `api.aiGenerate(topicId, difficulty)` → load fields
5. «Проверить» → `api.aiCheck(q, ref, user)` + `api.recordAttempt(...)` → show result
6. **Автосохранение каждые 5с** в localStorage, **каждые 15с** на сервер (`PUT /student/topics/{id}/draft`)
7. При возврате на страницу — восстановление из server draft, fallback на localStorage
8. Кнопка микрофона → MediaRecorder → POST `/voice/transcribe` → вставляет в поле ввода

### 4.4 Frontend stack — что НЕ используется

| Технология | Почему |
|---|---|
| Redux/Zustand | useState + custom hooks достаточно (но 10.2 — кандидат) |
| UI library | Tailwind + ручные компоненты (single-purpose) |
| Tailwind UI/shadcn | Избегаем npm weight |
| SWR/TanStack Query | `api.ts` wrappers (15+ endpoints) + ручная cache |
| Service Worker | Минимальный no-op в `/sw.js` |
| i18n | Семья русскоязычная, без фреймворка |
| OAuth client | Sprint X — PKCE flow на бэке, фронт ещё ждёт UI |

---

## 🚀 5. PRODUCTION — ДЕТАЛЬНО

### 5.1 Контейнеры (`docker compose ps`)

| Сервис | Image | RAM | Назначение |
|---|---|---|---|
| `deploy-backend-1` | `deploy-backend:latest` (наш Dockerfile) | 206MB | FastAPI + uvicorn |
| `deploy-frontend-1` | `deploy-frontend:latest` (наш Dockerfile) | 43MB | Next.js prod |
| `deploy-db-1` | `postgres:16-alpine` | 54MB | Primary DB |
| `deploy-redis-1` | `redis:7-alpine` | 4MB | Rate-limit cache, AI-budget |
| `deploy-proxy-1` | `nginx:1.27-alpine` | 3MB | TLS, proxy, IP-whitelist |
| `deploy-prometheus-1` | `prom/prometheus:v2.55.1` | 33MB | Scrape backend /metrics |
| `deploy-grafana-1` | `grafana/grafana:11.3.1` | 57MB | UI дашборды |
| **Total** | | **~398MB / 4GB** | |

**memory_limit** настроен только для prometheus/grafana (256M), backend/frontend/postgres не лимитированы — но фактически удерживаются в 4GB общей RAM.

### 5.2 Networks

```
external  ← external traffic (HTTPS), bind на 0.0.0.0:443
internal  ← между контейнерами (backend <-> db/redis, prometheus <-> backend)
```

### 5.3 Volumes

`pgdata` (postgres), `redisdata` (redis), `uploads` (для файлов Учителя),
`grafanadata` (Grafana state).

### 5.4 Cron jobs на хосте (`/etc/cron.d/` + crontab)

```
# crontab -l:
0 3 * * *  /opt/ai-tutor/deploy/backup/backup.sh >> /var/log/ai-tutor-backup.log 2>&1
*/5 * * * *  /opt/ai-tutor/deploy/monitoring/healthcheck.sh
*/5 * * * *  /opt/ai-tutor/deploy/monitoring/error-rate.sh
*/5 * * * *  /opt/ai-tutor/deploy/smtp/smtp-worker.sh

# /etc/cron.d/ai-tutor-audit-cleanup   (Sprint 4.2)
0 3 * * *   docker exec -u root deploy-backend-1 python3 /app/audit_cleanup.py
            (источник: /etc/ai-tutor/.env через `set -a; source; set +a`)

# /etc/cron.d/ai-tutor-weekly-summary  (Sprint 9.1)
0 15 * * 0  weekly_summary (HTML f-string → SMTP или DRY-RUN)

# /etc/cron.d/ai-tutor-backup-verify   (Sprint 10.4)
0 4 * * 1  test-restore.sh → проверка MD5 + pg_dump + count
```

### 5.5 Секреты — `/etc/ai-tutor/.env`

```
DATABASE_URL=postgresql+psycopg2://tutor:PTCYGF8x4NoK_V2LkPHjVQy1y2F03zv7@db:5432/tutor
POSTGRES_USER=tutor
POSTGRES_PASSWORD=PTCYGF8x4NoK_V2LkPHjVQy1y2F03zv7
APP_SECRET_KEY=<32+ char HMAC>
```

Права 600, owner root:root. Inline-пароли в cron удалены (Sprint 6.4).

### 5.6 Endpoints overview (smoke)

```bash
curl -sk -o /dev/null -w '%{http_code}\n' https://192.168.1.86/health         # 200
curl -sk -o /dev/null -w '%{http_code}\n' https://192.168.1.86/api/v2/health   # 200
curl -sk https://192.168.1.86/api/v1/openapi.json | jq '.paths | keys' | wc -l
# ~85 endpoints
```

---

## ⚙️ 6. AI INTEGRATION

### 6.1 MiniMax-M3 через OpenAI-compatible API

- **Базовый URL**: `https://api.minimax.io/v1`
- **Endpoints**: `/chat/completions` (works), `/embeddings` (НЕ работает — нет)
- **Режимы**: `explain`, `chat`, `hint`, `check`, `generate`, `teacher`
- **Timeouts**: 30s default; hint и check требуют быстрый ответ
- **Structured output**: НЕ поддерживается — fallback на JSON-парсинг + retry × 3 + Pydantic validation (Sprint 8.1)

### 6.2 AI Service Flow

```
AI endpoint → AIService.{explain_topic, chat, hint, check_answer, generate_exercise}
  → AIRequest(messages, mode, max_tokens, temperature)
  → Provider.complete(req)  # synchronous, blocks
  → AIResponse(content, model, input_tokens, output_tokens, structured)
  → record_ai_request() → Prometheus counter
  → parse через Pydantic (structured), иначе text → JSON → Pydantic (с retry)
```

### 6.3 Budget контроль (Sprint 9.4)

```
AI call → _enforce_budget(user)
  → Redis: ai-budget:{today}:req:{uid}  (TTL 86400)
         ai-budget:{today}:tok:{uid}  (TTL 86400)
  → Fallback in-memory (per-process) если Redis недоступен
  → 200 req / 200K tok / день по умолчанию
  → Переменные: AI_BUDGET_REQUESTS_PER_DAY, AI_BUDGET_TOKENS_PER_DAY
```

### 6.4 Adapter pattern

`app/ai/hermes.py:build_provider()` — единственное место выбора провайдера.
`provider.complete(req)` — интерфейс AIProvider из `app/ai/types.py`.
Mock-провайдер (`app/ai/mock.py`) — для тестов (возвращает JSON-MaterialContent).

---

## 📊 7. МЕТРИКИ И НАБЛЮДАЕМОСТЬ

### 7.1 Текущие метрики

```
Sprint  Тестов    Endpoints    Миграций    UI pages    Cron    Контейнеров
0(старт) 247      70+3 WS     0009        11         5       5
10      405      ~85+5 WS    0012         14         8       7
```

### 7.2 Prometheus метрики

| Метрика | Тип | Что показывает |
|---|---|---|
| `http_requests_total{method,path,status}` | Counter | HTTP трафик |
| `http_request_duration_seconds{method,path}` | Histogram | латентность |
| `ai_tokens_total{role}` | Counter | in/out AI токены |
| `ai_requests_total{mode,status}` | Counter | вызовы AI |
| `ai_parse_status_total{mode,result}` | Counter | ok / fallback / error парсинга |
| `python_gc_*` | Counter | Python runtime |

Grafana provisioned с дашбордом «AI-репетитор — обзор» (5 панелей).

---

## 🧪 8. ТЕСТЫ

### 8.1 Backend (pytest, 405 pass)

```
apps/backend/tests/
├── conftest.py              (_reset_state autouse, get_settings.cache_clear)
├── test_ai.py               — AI modes, sanitization
├── test_admin.py            — admin endpoints + RBAC
├── test_auth.py             — login, register, password reset
├── test_diagnostic_expire.py — Sprint 4
├── test_email_per_lesson.py — milestone notifications
├── test_email_retry.py       — Sprint 4
├── test_health.py
├── test_login_rate_limit.py  — Sprint 4.1
├── test_notifications.py
├── test_oauth.py
├── test_observability.py     — Sprint 5.1
├── test_ocr.py
├── test_parent_dashboard.py — Sprint 3
├── test_parents_materials.py
├── test_password_reset.py   — Sprint 4
├── test_progress_diagnostics.py — SM-2 (Sprint 2.2)
├── test_rag.py
├── test_rbac.py              — role isolation
├── test_refresh.py           — refreshed after Sprint 10.1
├── test_student_review.py
├── test_subjects.py
├── test_teacher.py           — workflow
├── test_techdebt.py          — Sprint 4 audit log
├── test_voice.py
├── test_websocket.py
├── test_ws_rate_limit.py
├── test_sprint7.py           — Markdown + topic_drafts (22)
├── test_sprint7_voice.py     — voice rate-limit (4)
├── test_sprint7_hint.py      — hint 3 levels (9)
├── test_sprint7_badges.py    — badges за усилие (13)
├── test_sprint8.py           — teacher generation retry (7)
├── test_sprint8_checkers.py  — numeric/keyword (32)
├── test_sprint8_rag.py       — embedding cache (12)
├── test_sprint8_cat.py       — CAT adaptive (20)
├── test_sprint9_budget.py    — AI budget Redis/in-memory (6)
├── test_sprint9_weekly.py    — weekly summary (7)
├── test_sprint9_multichild.py — multi-child (6)
├── test_sprint9_realtime.py  — admin WS (7)
├── test_sprint10_auth_cookie.py — JWT cookie (9)
├── test_sprint10_v2.py        — /api/v2 каркас (4)
```

### 8.2 E2E (Playwright)

```
e2e/smoke.spec.ts        — 15 smoke (login, basic flows)
e2e/teacher.spec.ts      — Sprint 1.5, 3 smoke
e2e/student.spec.ts      — Sprint 7.6, 4 теста полного цикла
e2e/parent.spec.ts       — Sprint 10.5, parent dashboard
```

Запуск: `cd apps/frontend && npm run e2e` (требует поднятый бэкенд).

---

## 🐛 9. ИЗВЕСТНЫЕ PITFALLS / PITFALLS, КОТОРЫЕ ЗАЩИЩАЛИСЬ

### При работе с проектом ОБЯЗАТЕЛЬНО соблюдать

| Pitfall | Где | Опасность |
|---|---|---|
| `pydantic-settings` кэш leaks | `app/config.py: get_settings()` | переменные из одного теста попадают в другой — обязательно `get_settings.cache_clear()` в conftest |
| `autoincrement user_id` ≠ порядок в фикстуре | `tests/conftest.py` | kid=id=3, не id=2 |
| FastAPI middleware sync/async | `app/observability.py` | sync-обёртка ломает downstream → только `async def` + `await call_next()` |
| Alembic `batch_alter_table` + FK на SQLite | `alembic/versions/0010_*.py` | SQLite не поддерживает `ALTER CONSTRAINT` → всегда `batch_alter_table` |
| `audit_logs.details` хранится как JSON-строка | `tests/test_rbac.py` | парсить через `json.loads(response.json()["details"])` |
| SQLite in-memory + `engine.begin()` | conftest.py | StaticPool для sharing, но `.begin()` работает только для UPDATE не INSERT |
| SM-2 defaults | `app/progress/spaced.py` | после `s.add()` обязательно `s.flush()` — иначе `easiness_factor=2.5` default не подхватывается до commit |
| Безопасная установка cookie | Sprint 10.1 | TestClient не передаёт Secure cookies по http:// → `secure=False` если `APP_ENV != production` |
| Маршрут в nginx `/grafana/` | `deploy/nginx/nginx.conf` | требует `location ^~` для приоритета над `location /` (regex/prefix) |
| Crontab через SSH ключ | `~/.ssh/id_ed25519_kirill_ai` | `scp` через ssh-agent ненадёжен → используй `cat local | ssh remote 'cat > file'` |
| `docker compose exec proxy nginx -s reload` | после правки nginx.conf | теряет state → даунтайм → используй hot-reload через exec |
| psql через cron | `/etc/cron.d/ai-tutor-audit-cleanup` | прокидывать `DATABASE_URL` через env-file (600) НЕ inline |
| Permission denied на файлы конфига | `deploy/prometheus/`, `deploy/grafana/` | контейнеры под nobody — root-owned файлы (644) нужно `chmod 644` ПОСЛЕ docker cp |
| **Bind mount не перечитывается контейнером nginx** | `deploy/nginx/nginx.conf` | после `scp` файла — `docker compose restart proxy` обязателен, не только `nginx -s reload` |
| **MiniMax не имеет `/embeddings`** | `app/rag_persist.py` | fallback на SHA-256 hash-fallback (стабильный псевдо-вектор) |
| **JWT в localStorage → XSS-вектор** | Sprint 10.1 | перевели на httpOnly cookie с Secure+SameSite=Lax |

---

## ❓ 10. ЗАПРОСЫ К AI-АУДИТОРУ

Пожалуйста, по результатам изучения проекта дайте **структурированный ответ**:

### A. Технический аудит (архитектура, код)

1. **Backend**: качество разделения по модулям, нет ли дублирования логики?
2. **FastAPI patterns**: правильно ли используются Depends, response_model, exception handlers?
3. **SQLAlchemy**: типизация моделей (Mapped[]), сессии, N+1 риски? Стоит ли добавить `selectinload`?
4. **AI service**: правильно ли retry и fallback реализованы? Нет ли утечки структур в логи при structured_output errors?
5. **Async**: где блокирующий код в async-функциях (asyncio.run внутри запроса)?
6. **Безопасность**: CSRF, XSS, SQLi — какие есть риски, которые я не покрыл?
7. **Тесты**: качество покрытия. Что протестировано поверхностно?

### B. Архитектурные предложения

1. Нужен ли API gateway / BFF? Учитывая что мы часто делаем N+1 запросов с фронта.
2. Какие сервисы стоит выделить из монолита? (Notification dispatcher, AI orchestrator?)
3. **Cache strategy**: где добавить кэш? Redis уже есть. Какие дорогие операции кэшировать?
4. **Observability gaps**: что ещё добавить кроме Prometheus? OpenTelemetry? Distributed tracing?
5. **Database migrations strategy**: 12 миграций с `down_revision` цепочкой — это надёжно? Или нужен squash?

### C. UX (с учётом T1D и Кирилла)

1. Какие ещё проблемы UI могут быть у 13-летнего с T1D? Может быть история про «когда я не могу додуматься, я просто хочу прочитать ответ»?
2. **Геймификация для T1D**: Sprint 7.5 убрал streak'и. А какие не-streak механики реально мотивируют подростков с T1D?
3. **Доступность**: a11y WCAG AA для Кирилла (крупный шрифт, screen reader)?
4. **Голос**: Sprint 7.2 — только transcription. Может быть стоит TTS (text-to-speech) для ответов AI?
5. **Оффлайн**: интернет дома может быть нестабильным. Что сохранить локально?

### D. Roadmap (что НЕ в плане, но стоит рассмотреть)

1. **Multi-tenancy**: что нужно чтобы расширить на других семей? (Auth0, Stripe, multi-region)
2. **Mobile PWA**: уже есть manifest.json, sw.js stub. Что нужно для нормального PWA?
3. **Game-based мотивация вместо баджей**: что если сделать мини-квесты (escape room по математике)?
4. **Teacher UX**: сейчас UI скудный. Что бы сделал teacher flow лучше?
5. **Parent reports**: weekly summary уже есть. Какие ещё метрики родителю интересны?

### E. Конкретные улучшения (готовые к реализации)

Дай **список из 5-10 конкретных issues**, которые мог бы сделать Junior/Mid разработчик за 1-3 дня:

- **Bug fix**: [что-то неправильно работает]
- **Performance**: [что-то медленно]
- **A11y**: [что-то не accessibility]
- **Test coverage**: [что-то протестировано слабо]
- **DX (developer experience)**: [как упростить жизнь будущему разработчику]

### F. Финальная оценка (1 предложение + 3-5 пунктов)

> Дай summary в 1 абзаце + bullet-points «что хорошо / что улучшить / что критично»

---

## 📎 11. ПРИЛОЖЕНИЕ: КАК РАЗВОРАЧИВАЕТСЯ

### Чистая установка (с нуля)

```bash
# 1. На хосте Proxmox LXC (4GB, Ubuntu 22.04)
ssh root@<host>
apt-get update && apt-get install -y docker docker-compose python3-venv git

# 2. Клонируем
git clone https://github.com/<owner>/ai-tutor.git /opt/ai-tutor
cd /opt/ai-tutor

# 3. Конфиг
cp apps/backend/.env.example .env
# Заполнить: APP_SECRET_KEY (openssl rand -hex 32), DATABASE_URL, MiniMax API key

# 4. Поднимаем
cd deploy
docker compose pull
docker compose build backend frontend
docker compose up -d
sleep 30

# 5. Migration
docker exec -u root deploy-backend-1 python3 -m alembic upgrade head

# 6. Smoke
curl -sk https://localhost/health  # → {"status":"ok"}

# 7. Создаём пользователей (seed)
docker exec -u root deploy-backend-1 python3 -m app.subjects.scripts_seed_runner
```

### Конфигурация — `.env`

```env
# --- App ---
APP_SECRET_KEY=<32+ byte random>
APP_ENV=production  # для Secure cookies
DATABASE_URL=postgresql+psycopg2://tutor:PASSWORD@db:5432/tutor
REDIS_URL=redis://redis:6379/0

# --- AI ---
AI_API_KEY=<MiniMax API key>
AI_BASE_URL=https://api.minimax.io/v1
AI_MODEL=minimax-M3
WHISPER_API_URL=<optional>

# --- Cron secrets (separate /etc/ai-tutor/.env) ---
# DATABASE_URL etc.

# --- Budget ---
AI_BUDGET_REQUESTS_PER_DAY=200
AI_BUDGET_TOKENS_PER_DAY=200000

# --- Observability ---
LOG_LEVEL=INFO
PROMETHEUS_ENABLED=1
```

### Связанные файлы для глубокого изучения

- `apps/backend/app/main.py` — точка входа backend (420 строк, все routers)
- `apps/backend/app/ai/service.py` — AI service core
- `apps/backend/app/observability.py` — Prometheus
- `apps/frontend/app/topics/[id]/page.tsx` — UI ученика (470 строк)
- `deploy/docker-compose.yml` — все 7 сервисов
- `docs/plans/SPRINT-6-PLAN.md` — детальный план Sprint 6-10
- `AI-DEEP-AUDIT-PROMPT.md` — предыдущий AI-промт (990 строк)

---

## 📞 12. КОНТАКТЫ ДЛЯ ОБРАТНОЙ СВЯЗИ

**Разработчик**: Игорь (владелец LXC 192.168.1.86, родитель Кирилла).
**Связь при разработке**: через Hermes Agent.

Ответы от AI-аудитора ожидаются:
- Чёткие issue с конкретными файлами/строками (не «сделать лучше»)
- Ссылка на лучшие практики (PEPs, security guides)
- Учёт T1D-контекста (никакого давления на ребёнка)

**Спасибо за ревью.** 🚀
