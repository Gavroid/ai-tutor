# 🧠 ГЛУБОКИЙ ПРОМТ ДЛЯ AI-АУДИТА ПРОЕКТА «AI-репетитор 7 класса»

> **Версия:** 2026-07-12 (после Sprint 1-5)
> **Назначение:** этот документ позволяет другой AI-платформе полностью погрузиться в проект и провести **глубокий независимый аудит** с предложением доработок по приоритетам, готовых рекомендаций по новым фичам, выявленных рисков и anti-patterns.
>
> **Сравнение с другими документами:** базовый промт для разработки теперь — `docs/MASTER-HANDOVER-PROMPT.md` (~742 строки, актуальный, Pilot Core Stage 1). Этот документ — расширенная версия с фокусом на **аудит и стратегические рекомендации**. Прочти оба.
> **TL;DR:** `QUICK-START.md` (1 страница).
>
> **Аудитор:** прочти ВЕСЬ документ перед началом работы. Не приступай к анализу, пока не дойдёшь до секции «Формат ответа».

---

## 🎯 Что нужно от тебя

1. **Глубокий технический аудит** кодовой базы — найди баги, anti-patterns, потенциальные проблемы безопасности, производительности, надёжности. С приоритетами P0/P1/P2/P3.
2. **Аудит архитектуры** — оцени текущие решения, предложи улучшения. Что масштабируется, что нет.
3. **Новые фичи** — предложи 10-15 фич с приоритетами, оценкой сложности, потенциальной ценностью.
4. **UX/продуктовый аудит** — что можно улучшить с точки зрения 13-летнего школьника и его родителя.
5. **Roadmap** — предложи план на следующие 3-6 месяцев.
6. **Конкретные патчи** — для критичных багов предложи готовый код/diff.

**Формат ответа — в самом конце документа.** Там расписано что я хочу получить.

---

## 📚 Структура документа

1. [Контекст проекта](#1-контекст-проекта)
2. [Технический стек](#2-технический-стек)
3. [Архитектура backend](#3-архитектура-backend)
4. [Архитектура frontend](#4-архитектура-frontend)
5. [Структура БД и миграции](#5-структура-бд-и-миграции)
6. [AI-инфраструктура](#6-ai-инфраструктура)
7. [Production deployment](#7-production-deployment)
8. [Security и privacy](#8-security-и-privacy)
9. [Тестирование и CI/CD](#9-тестирование-и-cicd)
10. [Мониторинг и observability](#10-мониторинг-и-observability)
11. [Sprint 1-5: что сделано](#11-sprint-1-5-что-сделано)
12. [Известные проблемы и тех. долг](#12-известные-проблемы-и-тех-долг)
13. [Идеи фич (backlog)](#13-идеи-фич-backlog)
14. [Открытые вопросы](#14-открытые-вопросы)
15. [Формат ответа](#15-формат-ответа)

---

## 1. Контекст проекта

**AI-репетитор 7 класса** — это **production-ready MVP** (12 этапов MVP + 5 спринтов развития, развёрнут в production с 2026-07-12 на 192.168.1.86, Proxmox LXC 4 CPU / 4 GB RAM, swap=0).

**Целевая аудитория:**
- **Главный пользователь:** Кирилл, 13 лет, школьник 7 класса, **диагноз T1D (сахарный диабет 1 типа)**. Это влияет на UX: короткие сессии, отсутствие жёстких таймеров, можно прерваться в любой момент.
- **Родитель:** контролирует прогресс, НЕ видит содержимое чатов с AI (privacy).
- **Учитель:** новая роль (Sprint 1) — наполняет систему материалами через AI-генерацию.
- **Админ:** владелец (Игорь). Один человек.

**Бизнес-цель:** показать, что AI может эффективно репетиторствовать школьника по российской программе 7 класса. Сейчас проект — личный (некоммерческий), но может стать продуктом для других семей.

**URL:** `https://192.168.1.86` (self-signed HTTPS, LXC).
**Repo:** `/root/workspace/ai-tutor/` (dev) и `/opt/ai-tutor/` (production, через rsync).

**Текущие цифры (актуально на 2026-07-12):**
- Backend тесты: **247/247 ✅** (+111 в Sprint 1-5)
- E2E (Playwright): 12/12 ✅
- Production smoke: 8/8 ✅
- Контейнеров: 5/5 healthy
- API endpoints: **70 REST + 3 WebSocket**
- Frontend pages: **15**
- DB миграции: 9 (последняя `0009_spaced_repetition`)
- Cron jobs: 5

---

## 2. Технический стек

### Backend (Python 3.12 + FastAPI 0.115)

| Слой | Технология | Зачем |
|------|-----------|-------|
| Web | FastAPI 0.115, uvicorn (2 workers prod) | Async HTTP API |
| ORM | SQLAlchemy 2 + Alembic | Миграции и типобезопасность |
| БД | PostgreSQL 16 (alpine, в Docker) | Надёжное хранилище |
| Валидация | Pydantic v2 + pydantic-settings | Конфиги и DTO |
| Auth | python-jose (JWT HS256), bcrypt rounds=12 | Access+refresh токены |
| Cache/Rate-limit | Redis 7 (опционально, in-memory fallback) | Горизонтальное масштабирование |
| AI SDK | OpenAI-compatible HTTP (httpx) | MiniMax-M3 / любой OpenAI-совместимый |
| AI Mock | свой `MockProvider` для тестов | Без ключа в CI |
| Email | aiosmtplib + Jinja2 templates | Dry-run без SMTP |
| OCR | pytesseract + tesseract-ocr-rus | Картинки параграфов |
| PDF | pdfplumber | Извлечение текста из PDF |
| DOCX | python-docx | Извлечение текста из DOCX |
| Голос | Whisper (через внешний сервис) | Распознавание речи |
| Метрики | prometheus-client 0.21 | `/metrics` |
| Тесты | pytest 8.3 + pytest-asyncio + pytest-cov | Unit + integration |

**Зависимости:** `apps/backend/requirements.txt` (locked версии).

### Frontend (Next.js 16 + React 19)

| Слой | Технология | Зачем |
|------|-----------|-------|
| Framework | Next.js 16 (App Router) + React 19 | SSR/SSG |
| Language | TypeScript 5.7 strict | Типобезопасность |
| Styling | Tailwind CSS 3.4 | Utility-first |
| Icons | Emoji (без сторонних либ) | Лёгкость |
| HTTP | встроенный `fetch` с JWT в `localStorage` | Простота |
| WS | нативный WebSocket (свой `useChatStream`) | Стриминг AI |
| Тесты | Playwright 1.61 (только E2E) | End-to-end smoke |

**Зависимости:** `apps/frontend/package.json`.

### Infrastructure

- **Docker Compose** (5 сервисов: db, redis, backend, frontend, nginx-proxy)
- **Nginx 1.27** как reverse proxy (self-signed HTTPS, rate-limit zones, WebSocket Upgrade)
- **Proxmox LXC** (4 CPU / 4 GB RAM / 0 swap) — НЕ Docker-in-Docker, а нативные контейнеры
- **Backup:** `deploy/backup/backup.sh` (pg_dump + uploads, ротация, offsite через `ai-tutor-backup-offsite.sh`, md5 manifest)
- **Monitoring:** bash-скрипты (`healthcheck.sh`, `error-rate.sh`, `smtp-worker.sh`) через cron `*/5 * * * *`
- **CI/CD:** GitHub Actions workflows (`.github/workflows/{tests,deploy,frontend-build}.yml`) — НЕ активированы (нет git remote)

### Архитектурные решения

1. **Single-process FastAPI** с 2 workers (uvicorn) — НЕ использую Gunicorn.
2. **In-memory rate-limit с Redis fallback** — без Redis работает (single-process), с Redis — для multi-worker.
3. **JWT в localStorage** на фронте (НЕ httpOnly cookie) — упрощает, но снижает XSS-устойчивость.
4. **SQLite-in-memory для тестов** с `StaticPool` — все 247 тестов бегут за ~2.5 мин.
5. **`batch_alter_table`** в миграциях — для совместимости с SQLite (тесты) и Postgres (prod).
6. **`prometheus_client`** без Grafana — метрики отдаются на `/metrics`, Prometheus может скрейпить снаружи.

---

## 3. Архитектура backend

```
apps/backend/app/
├── main.py                 # FastAPI factory + middleware (rate-limit, access-log, request-context, metrics)
├── config.py               # pydantic-settings (.env → typed config)
├── db/session.py           # Engine, SessionLocal, Base, get_db dependency
├── auth/
│   ├── security.py         # hash_password, JWT (access+refresh), get_current_user, require_role
│   ├── router.py           # /register, /login, /refresh, /me, /password-reset
│   ├── oauth.py            # OAuth2 (Google/Apple) — базовый
│   └── password_reset_models.py
├── users/
│   ├── models.py           # User, StudentProfile, ParentStudentLink
│   ├── schemas.py          # UserCreate, UserOut
│   └── service.py          # register_user, authenticate, issue_tokens
├── subjects/
│   ├── models.py           # Subject → Section → Topic → Subtopic → LearningMaterial → Question
│   ├── schemas.py
│   ├── router.py           # GET /subjects, /subjects/{id}/topics, /topics/{id}
│   ├── curriculum_7_class.py  # Хардкод curriculum (12 предметов × 186 тем)
│   └── scripts_seed_runner.py  # seed_for_tests() для тестов
├── materials/
│   ├── router.py           # POST /materials/upload (PDF/DOCX/TXT/OCR)
│   ├── service.py          # save_uploaded_material, search_materials
│   └── schemas.py
├── ai/
│   ├── service.py          # AIService (explain_topic, hint, check_answer, generate_exercise)
│   ├── prompts.py          # BASE_SYSTEM + режимные промпты (жёстко зашиты)
│   ├── sanitize.py         # detect_injection, sanitize_user_input, sanitize_output
│   ├── mock.py             # MockProvider для тестов
│   ├── hermes.py           # HermesProvider (OpenAI-compatible)
│   ├── websocket.py        # WS /ws/ai/{topic_id} — стрим explain
│   ├── websocket_more.py   # WS /ws/ai/{topic_id} — чат
│   ├── types.py            # AIRequest, AIResponse, AIProvider Protocol
│   └── router.py           # HTTP AI endpoints (без WS)
├── progress/
│   ├── models.py           # Attempt, Mistake, Progress (с полями SM-2 из миграции 0009)
│   ├── service.py          # record_attempt, recommend_review, due_for_review, schedule_topic_for_review
│   ├── spaced.py           # SM-2 алгоритм (schedule_next_review, quality_from_result)
│   ├── schemas.py          # ProgressOut, ReviewItem, ReviewResultIn
│   └── router.py           # /progress, /due-for-review, /review-result, /attempts, /mistakes
├── diagnostics/            # Диагностические сессии
├── notifications/          # In-app + email (aiosmtplib)
├── parents/                # Invite-коды, дашборд (/dashboard + /dashboard.pdf)
├── admin/                  # Audit log, user management, stats
├── teacher/                 # ★ Sprint 1: AI-генерация, CRUD, workflow
├── student/                 # ★ Sprint 2: только published materials для ученика
├── common/
│   ├── deps.py             # ★ Sprint 1.1: require_admin/teacher/parent/student deps
│   └── __init__.py
├── observability.py        # ★ Sprint 5.1: Prometheus метрики
├── voice/                   # Whisper transcription endpoint
├── rag.py                   # Простой vector store (in-memory, планируется pgvector)
├── rag_router.py
└── scripts/seed.py          # Начальный seed (admin, subjects, curriculum)
```

### Middleware (порядок важен — внешний первый):

1. **CORS** — `CORS_ORIGINS` whitelist
2. **Rate-limit для /auth/register** — 5/час на IP (Sprint 4.1)
3. **Rate-limit для /auth/login** — 10/15мин на IP (anti-bruteforce)
4. **Rate-limit для /api/v1/ai/** — 30/мин на user_id
5. **WS rate-limit** — 5 одновременных WS на user_id
6. **Access log** — JSON в stdout для каждого /api/* запроса
7. **5xx → audit log** — автоматическая запись error.5xx (Sprint 5.2)
8. **Request context** — contextvar с Request для audit log IP
9. **Prometheus metrics** — http_requests_total, http_request_duration (Sprint 5.1)

### Подробности модулей

#### `app/common/deps.py` (Sprint 1.1)
```python
def require_admin(): return require_role(Role.ADMIN)
def require_teacher_or_admin(): return require_role(Role.TEACHER, Role.ADMIN)
def require_teacher(): return require_role(Role.TEACHER)
def require_parent(): return require_role(Role.PARENT)
def require_student(): return require_role(Role.STUDENT)
def current_user = get_current_user  # любой авторизованный
def require_roles = require_role  # базовая фабрика
```

#### `app/teacher/service.py` (Sprint 1.2-1.3)
- `parse_text_source`, `parse_file_source` (TXT/PDF/DOCX), `parse_topic_source`
- `call_ai_for_material` → возвращает структурированный `MaterialContent` (9 блоков: key_ideas, rule, example, misconception, mistake, self_check, **practice_tasks (≥5)**, mini_test, flashcards)
- Workflow: `approve_material`, `publish_material`, `unpublish_material`, `update_material_content` (откатывает в ai_generated)
- State machine `_ALLOWED_TRANSITIONS` контролирует переходы

#### `app/progress/spaced.py` (Sprint 2.2)
- SM-2 алгоритм (`schedule_next_review`)
- EF ограничен снизу 1.3
- Quality 0..5

#### `app/observability.py` (Sprint 5.1)
- `HTTP_REQUESTS_TOTAL{method,path,status}` Counter
- `HTTP_REQUEST_DURATION_SECONDS{method,path}` Histogram (buckets 5ms..10s)
- `AI_TOKENS_TOTAL{role}` (input/output)
- `AI_REQUESTS_TOTAL{mode,status}` (explain/hint/check/generate/chat; ok/error)
- `ACTIVE_SESSIONS_TOTAL{event}` (login/register/logout)
- Path normalization (numeric segments → `{id}`) — контроль cardinality

---

## 4. Архитектура frontend

```
apps/frontend/app/
├── layout.tsx              # RootLayout
├── page.tsx                # / (redirect → /login или /subjects)
├── globals.css
├── login/                  # /login
├── register/               # /register
├── forgot-password/        # /forgot-password
├── link-parent/            # /link-parent (для ученика)
├── subjects/               # /subjects, /subjects/[id]
│   ├── page.tsx            # Главная с предметами, рекомендациями, "Сегодня к повторению" (Sprint 2)
│   └── [id]/page.tsx       # Темы предмета
├── topics/
│   └── [id]/page.tsx       # Урок: чат с AI + генерация задач + проверка + (TODO: повторение)
├── diagnostic/             # Диагностика
├── admin/                  # /admin — Audit log, users, stats, tools
├── parents/                # /parents — список детей + простой обзор
├── parent/dashboard/[studentId]/page.tsx  # ★ Sprint 3.2: расширенный дашборд
├── teacher/                # ★ Sprint 1.5: новый модуль
│   ├── page.tsx            # /teacher — список материалов
│   ├── generate/page.tsx   # /teacher/generate — мастер из 2 шагов
│   └── materials/[id]/page.tsx  # /teacher/materials/[id] — детальный + кнопки workflow
└── api/                    # (нет — используем /api/v1/* напрямую через NEXT_PUBLIC_API_URL)

apps/frontend/
├── lib/
│   ├── api.ts              # api.* методы (login, register, teacherListMaterials, parentDashboard, voiceTranscribe, dueForReview, ...)
│   └── ws-chat.ts          # useChatStream — WebSocket клиент
└── types/index.ts          # Все TypeScript типы (Subject, Topic, MaterialContent, ReviewItem, ...)
```

### Текущие особенности UI

- **Tailwind utility-only**, без сторонних UI-китов (сознательный минимализм)
- **localStorage** для JWT (НЕ httpOnly cookie — упрощение, XSS-риск)
- **Никакой state management библиотеки** — только `useState`
- **Emoji-иконки** вместо lucide-react / heroicons
- **Graphs в /parent/dashboard/[id]** — самописные CSS-бары (НЕ recharts/chart.js)
- **Markdown** рендерится пока plain text (Sprint 2.4 в roadmap, не реализован)
- **Typewriter effect** для AI-стрима — TODO (Sprint 2.4)

---

## 5. Структура БД и миграции

### Схема (PostgreSQL 16)

```
users              — id (BIGINT), email (unique), password_hash, role (enum), display_name, is_active, created_at, updated_at
student_profiles   — id, user_id (FK→users), grade (int, default 7), preferred_language, learning_style (text/JSON), daily_minutes, goals
parent_student_links — id, parent_id (FK), student_id (FK), status (active/pending/revoked), created_at

subjects           — id, code, name, description, color, icon, recommended_grade (default 7), age_min/max, is_active
sections           — id, subject_id (FK), code, name, order_index
topics             — id, section_id (FK), name, description, difficulty (1..5), order_index
subtopics          — id, topic_id (FK), name, description, order_index

learning_materials — id, topic_id (FK), title, content (JSON-string), source, file_path,
                     ★ status (draft/ai_generated/teacher_approved/published) [Sprint 1.4]
                     ★ generated_by (FK→users, nullable) [Sprint 1.4]
                     ★ approved_by (FK→users, nullable) [Sprint 1.4]
                     ★ published_at (timestamp, nullable) [Sprint 1.4]
                     ★ source_type (text/file/topic) [Sprint 1.4]
                     ★ ai_confidence (text/JSON, nullable) [Sprint 1.4]
questions          — id, topic_id (FK), type, difficulty, question_text, ...
attempts           — id, user_id, topic_id, question_text, user_answer, correct_answer, is_correct, score, feedback, created_at
mistakes           — id, user_id, topic_id, mistake_type, description, count, last_seen
progress           — id, user_id, topic_id, mastery_score, attempts_count, correct_count, updated_at
                     ★ next_review_at (timestamp, nullable) [Sprint 2.2]
                     ★ last_reviewed_at (timestamp, nullable) [Sprint 2.2]
                     ★ review_count (int, default 0) [Sprint 2.2]
                     ★ easiness_factor (float, default 2.5) [Sprint 2.2]

diagnostic_sessions — id, user_id, subject_id, status (in_progress/completed), total_questions, correct_count, overall_score, weak_topics (JSON), recommendations, created_at, completed_at
diagnostic_answers  — id, session_id, topic_id, question_text, user_answer, correct_answer, is_correct, created_at

notifications      — id, user_id, type, title, body, read (bool), created_at
email_notifications — id, user_id, to_email, subject, body, status (sent/dry_run/failed), error, sent_at

audit_logs         — id, user_id (nullable, FK), action, entity, entity_id, details (JSON), ip_address, created_at
                   ★ audit.purge, error.5xx, material.* — новые action-типы из Sprint 1-5
password_reset_tokens — id, user_id, token_hash, expires_at, used, created_at
```

### Миграции (Alembic)

| # | Имя | Что делает |
|---|-----|-----------|
| 0001 | initial_users | users, student_profiles, parent_student_links |
| 0002 | initial_subjects | subjects, sections, topics, subtopics, learning_materials, questions |
| 0003 | progress | attempts, mistakes, progress |
| 0004 | diagnostics | diagnostic_sessions, diagnostic_answers |
| 0005 | audit_log | audit_logs |
| 0006 | notifications | notifications, email_notifications |
| 0007 | password_reset | password_reset_tokens |
| **0008** | **material_workflow** | **status, generated_by, approved_by, published_at, source_type, ai_confidence в learning_materials + 3 индекса** |
| **0009** | **spaced_repetition** | **next_review_at, last_reviewed_at, review_count, easiness_factor в progress + 1 индекс** |

Все миграции используют `batch_alter_table` для совместимости с SQLite (тесты in-memory) и Postgres (production).

---

## 6. AI-инфраструктура

### Провайдеры

- **HermesProvider** (production): `HermesProvider(api_key, base_url, model)` — OpenAI-compatible HTTP.
- **MockProvider** (тесты + dev): детерминированные ответы, если `AI_API_KEY` пуст или равен `"mock-key-for-tests"`.

**Production провайдер:** MiniMax-M3 через `https://api.minimax.io/v1` (`.env`: `AI_BASE_URL=https://api.minimax.io/v1`, `AI_MODEL=MiniMax-M3`).

### Режимы AI

| Режим | Endpoint | Что делает |
|-------|---------|-----------|
| explain | `POST /ai/explain` | Объясняет тему простыми словами |
| hint | `POST /ai/hint` | Задаёт наводящий вопрос (не выдаёт ответ) |
| check | `POST /ai/check-answer` | Проверяет ответ ученика, ставит score, даёт объяснение |
| generate | `POST /ai/generate-exercise` | Генерирует одну задачу по теме |
| chat | `POST /ai/chat` | Свободный чат с историей |
| diagnose | (внутренний) | Генерирует вопросы для диагностики |
| material_generate | `POST /teacher/materials/generate` | ★ Sprint 1: генерирует целый раздел по 9-блоковому шаблону |

WS endpoints (стриминг):
- `ws://.../ws/ai/{topic_id}?token=...` — стрим объяснения (длинные тексты)
- `ws://.../ws/ai/{topic_id}/chat?token=...` — стрим чата

### Защита от prompt injection

`app/ai/sanitize.py`:
- `detect_injection(text)` — regex поиск "ignore previous instructions", `[INST]`, `<|system|>`, "you are now", etc.
- `sanitize_user_input(text, max_chars)` — обрезка + удаление управляющих символов
- `sanitize_output(text)` — HTML escape в ответе LLM

В teacher-flow при обнаружении injection → 400.

### Промпт-инжиниринг

- Все промпты **жёстко зашиты** в `app/ai/prompts.py` (НЕ в БД)
- Ученик НЕ может их увидеть (нет доступа)
- `BASE_SYSTEM` содержит все правила безопасности (T1D, секс, насилие, экстренные службы 112/8-800-2000-122)
- Шаблон `SYSTEM_PROMPT_FOR_MATERIAL` — отдельный, для генерации учебных материалов (Sprint 1)

### Токены и стоимость

- `ai_max_input_chars = 8000`
- `ai_timeout_seconds = 30`
- `ai_max_retries = 2`
- `rate_limit_ai_per_minute = 30` на user_id
- Метрики `ai_tokens_total{role}` (Sprint 5.1) — для отслеживания расходов

---

## 7. Production deployment

### Архитектура

```
Proxmox LXC 192.168.1.86 (Kirill-AI, 4 CPU / 4 GB RAM / 0 swap)
├── Docker Compose (5 сервисов)
│   ├── postgres:16-alpine (db)        — internal network only
│   ├── redis:7-alpine (redis)         — internal network
│   ├── deploy-backend (FastAPI)        — internal network, port 8000
│   ├── deploy-frontend (Next.js)       — internal network, port 3000
│   └── deploy-proxy (nginx:1.27)       — 80→443 redirect + 443 SSL + reverse proxy
├── /opt/ai-tutor/
│   ├── apps/backend/                   # Код бэкенда (rsync из /root/workspace)
│   ├── apps/frontend/                  # Код фронта
│   ├── deploy/
│   │   ├── docker-compose.yml
│   │   ├── nginx/nginx.conf
│   │   ├── backup/                     # backup.sh + offsite
│   │   ├── monitoring/                 # healthcheck.sh, error-rate.sh, smtp-worker.sh
│   │   ├── ssl/                       # self-signed cert
│   │   ├── postgres-init/
│   │   └── cron/                      # ★ Sprint 4: audit_cleanup.py (ежедневно 3 AM)
│   ├── .env                           # production secrets
│   └── data/curriculum/
└── /etc/cron.d/
    ├── ai-tutor-audit-cleanup         # ★ Sprint 4: 0 3 * * *
    ├── ai-tutor-backup                # 0 3 * * * (host cron)
    └── (стандартные)
```

### Deploy process (текущий, manual)

1. SSH на production: `ssh -i /root/.ssh/id_ed25519_kirill_ai root@192.168.1.86`
2. Backup: `cd /opt/ai-tutor/deploy/backup && ./backup.sh`
3. rsync файлов:
   ```bash
   rsync -avz --delete --exclude='__pycache__' --exclude='*.pyc' \
     -e "ssh -i /root/.ssh/id_ed25519_kirill_ai" \
     /root/workspace/ai-tutor/apps/backend/app/ \
     root@192.168.1.86:/opt/ai-tutor/apps/backend/app/

   rsync -avz \
     -e "ssh -i /root/.ssh/id_ed25519_kirill_ai" \
     /root/workspace/ai-tutor/apps/backend/alembic/versions/0008_material_workflow.py \
     /root/workspace/ai-tutor/apps/backend/alembic/versions/0009_spaced_repetition.py \
     root@192.168.1.86:/opt/ai-tutor/apps/backend/alembic/versions/

   rsync -avz /root/workspace/ai-tutor/apps/backend/requirements.txt \
     -e "ssh ..." root@192.168.1.86:/opt/ai-tutor/apps/backend/

   rsync -avz --exclude='node_modules' --exclude='.next' \
     -e "ssh ..." \
     /root/workspace/ai-tutor/apps/frontend/{app,lib,types}/ \
     root@192.168.1.86:/opt/ai-tutor/apps/frontend/
   ```
4. Rebuild: `cd /opt/ai-tutor/deploy && docker compose build backend frontend`
5. Restart: `docker compose up -d backend frontend`
6. Migrations: `docker compose exec -T backend alembic upgrade head`
7. Smoke: `curl -sk https://192.168.1.86/health` + `/metrics` + `/docs`
8. Backup after: `./backup.sh`

**Проблема:** deploy вручную занимает ~10 минут и error-prone (один раз упало из-за отсутствия `prometheus-client` в `requirements.txt`).

### CI/CD (НЕ активирован)

`/root/workspace/ai-tutor/.github/workflows/`:
- `tests.yml` — backend pytest + frontend build на каждый push
- `deploy.yml` — SSH deploy на 192.168.1.86 через `webfactory/ssh-agent`
- `frontend-build.yml` — отдельный build фронта

Для активации нужно:
1. Создать GitHub repo
2. Push код
3. Добавить secrets: `PRODUCTION_HOST`, `PRODUCTION_SSH_KEY`

### Резервное копирование

- **Локально:** `deploy/backup/backup.sh` — `pg_dump | gzip` + `tar.gz` uploads в `/opt/ai-tutor/deploy/backup/_out/`, ротация 14 дней
- **Offsite:** `ai-tutor-backup-offsite.sh` — копирует на удалённый хост (один раз в сутки в 3 AM)
- **Manifest:** `manifest-<timestamp>.md5` — md5 всех файлов для верификации
- **Restore:** `deploy/backup/test-restore.sh` — тестирует восстановление
- **Retention cron:** `deploy/cron/audit_cleanup.py` — Sprint 4, удаляет audit_logs старше 90 дней

### Мониторинг (bash + cron, НЕ Prometheus+Alertmanager)

- `monitoring/healthcheck.sh` (каждые 5 мин) — `curl /health` + `curl /ready`
- `monitoring/error-rate.sh` (каждые 5 мин) — `grep ERROR` в логах за последние 5 мин
- `monitoring/smtp-worker.sh` (каждые 5 мин) — проверка SMTP queue
- При сбое — запись в `/var/log/ai-tutor-*.log` (НЕ alert в Telegram/Slack — TODO)

---

## 8. Security и privacy

### RBAC (Sprint 1.1)

Зависимости в `app/common/deps.py`:

| Dependency | Роли |
|------------|------|
| `require_admin()` | admin |
| `require_teacher_or_admin()` | teacher, admin |
| `require_teacher()` | только teacher |
| `require_parent()` | только parent |
| `require_student()` | только student |
| `current_user` | любой авторизованный |

Неавторизованный → 401, неверная роль → 403.

### Teacher видит только свои материалы (Sprint 1.3)

```python
if current.role.value == "teacher" and material.generated_by != current.id:
    raise HTTPException(403, "Можно просматривать только свои материалы")
```

Admin видит все.

### Parent → child (Sprint 3.1)

```python
# Endpoint требует:
# 1) роль parent (require_parent)
# 2) активную ParentStudentLink (status='active')
# Иначе 404 (НЕ 403 — чтобы не палить существование)
```

### AI и PII (Sprint 1.2)

- AI **не получает** ФИО/адрес/T1D-медданные ученика в промптах
- AI-контент проходит human-approve перед публикацией
- `ai_uncertainty_notes` информируют учителя о неуверенных местах

### Sanitization (Sprint 1.2)

`app/ai/sanitize.py`:
- `sanitize_user_input(text, max_chars)` — обрезка
- `detect_injection(text)` — prompt injection detection
- `sanitize_output(text)` — HTML escape

### Rate limiting (Sprint 4.1)

| Endpoint | Лимит | Storage |
|----------|-------|---------|
| `/auth/register` | 5/час на IP | in-memory + Redis |
| `/auth/login` | 10/15мин на IP | in-memory + Redis |
| `/api/v1/ai/*` | 30/мин на user_id | in-memory + Redis |
| WS `/ws/ai/*` | 5 одновременных на user_id | in-memory |

### X-Forwarded-For trust (Sprint 4.3)

`TRUSTED_PROXIES` env (CIDR) — по умолчанию `127.0.0.1/32,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16` (приватные сети).

`_client_ip(request, trusted_proxies)` — читает XFF только если `request.client.host` в trusted CIDR. Иначе XFF игнорируется (защита от подмены IP).

### Audit log (Sprint 5.2)

Все защищённые действия пишутся в `audit_logs`:
- `user.register`, `user.deactivate`
- `material.generate`, `material.update`, `material.delete`
- `material.approve`, `material.publish`, `material.unpublish`
- `audit.purge` (Sprint 4.2)
- `error.5xx` (Sprint 5.2 — автоматически для всех 5xx ответов)

Каждая запись: `user_id`, `action`, `entity`, `entity_id`, `details` (JSON), `ip_address` (из XFF), `created_at`.

Retention: 90 дней (настраивается через env `AUDIT_TTL_DAYS` или endpoint `/admin/audit-log/purge`).

### Self-signed HTTPS

`/etc/nginx/certs/fullchain.pem` + `privkey.pem` (генерируются вручную). Для production нужно заменить на Let's Encrypt.

`docs/security.md` содержит полную политику безопасности.

---

## 9. Тестирование и CI/CD

### Тесты

| Тип | Файл | Кол-во |
|-----|------|--------|
| Backend unit/integration | `apps/backend/tests/*.py` | 247 |
| E2E (Playwright) | `apps/frontend/e2e/*.spec.ts` | 12 |
| Production smoke | `apps/frontend/e2e/smoke.spec.ts` (частично), `deploy/smoke/` | 8 |

### Запуск

```bash
# Backend
cd apps/backend
/usr/local/lib/hermes-agent/venv/bin/python3 -m pytest tests/ -q  # ~2.5 мин

# Frontend build
cd apps/frontend
./node_modules/.bin/next build  # ~30 сек

# E2E (требует running production)
cd apps/frontend
./node_modules/.bin/playwright test
```

### Конфигурация тестов

`apps/backend/tests/conftest.py` — autouse-fixture `_reset_state`:
- Сбрасывает глобальный state (`_login_attempts_log`, `_register_attempts_log`, `_ws_concurrent_log`, `_ai_call_log`, `app.dependency_overrides`)
- **КРИТИЧНО:** сбрасывает `get_settings.cache_clear()` — иначе pydantic-settings кэширует и `UPLOAD_DIR` от одного теста протекает в другой

### Тестовые модули

| Файл | Sprint | Что покрывает |
|------|--------|--------------|
| test_auth.py | MVP | JWT, register, login, refresh |
| test_admin.py | MVP | Audit log, user management |
| test_ai.py | MVP | AI endpoints (с MockProvider) |
| test_voice.py | MVP | Whisper transcription |
| test_oauth.py | MVP | OAuth2 providers |
| test_ocr.py | MVP | OCR для изображений |
| test_rag.py | MVP | RAG (in-memory) |
| test_subjects.py | MVP | Subjects/topics |
| test_websocket.py | MVP | WS стримы |
| test_diagnostic_expire.py | MVP | expire_stale_diagnostics |
| test_parents_materials.py | MVP | Parents + materials |
| test_progress_diagnostics.py | MVP | progress/diagnostics |
| test_login_rate_limit.py | MVP | rate limit на /login |
| test_ws_rate_limit.py | MVP | WS rate limit |
| test_refresh.py | MVP | refresh tokens |
| test_email_per_lesson.py | MVP | email notifications |
| test_email_retry.py | MVP | email retry |
| test_notifications.py | MVP | in-app notifications |
| test_password_reset.py | MVP | password reset flow |
| **test_rbac.py** | **Sprint 1.1** | **RBAC для всех ролей** (23 теста) |
| **test_teacher.py** | **Sprint 1.2-1.3** | **Teacher endpoints + workflow** (29 тестов) |
| **test_student_review.py** | **Sprint 2** | **SM-2 + student materials** (19 тестов) |
| **test_parent_dashboard.py** | **Sprint 3** | **Dashboard + privacy** (13 тестов) |
| **test_techdebt.py** | **Sprint 4** | **rate limit register + XFF + audit purge** (16 тестов) |
| **test_observability.py** | **Sprint 5** | **Prometheus + 5xx tracking** (11 тестов) |

### CI/CD workflow

- `tests.yml` — pytest + next build на push
- `frontend-build.yml` — отдельный build фронта
- `deploy.yml` — SSH deploy

Все workflows **определены**, но **НЕ активированы** (нет git remote).

---

## 10. Мониторинг и observability

### Prometheus метрики (Sprint 5.1)

`GET /metrics` (через nginx):

| Метрика | Тип | Labels |
|---------|-----|--------|
| `http_requests_total` | Counter | method, path, status |
| `http_request_duration_seconds` | Histogram (5ms..10s) | method, path |
| `ai_tokens_total` | Counter | role (input/output) |
| `ai_requests_total` | Counter | mode, status |
| `active_sessions_total` | Counter | event (login/register/logout) |

Path normalization: numeric segments → `{id}` (контроль cardinality).

Исключения из метрик: `/metrics`, `/health`, `/ready`, `/`.

### Error tracking (Sprint 5.2)

Middleware автоматически пишет в `audit_logs` для всех ответов с `status_code >= 500`:
```
action="error.5xx"
entity="http_request"
details={method, path, status, request_id}
```

Best-effort: если БД недоступна — основной запрос не падает.

### Bash-мониторинг (legacy, НЕ Prometheus+Alertmanager)

- `monitoring/healthcheck.sh` (каждые 5 мин) — `curl /health`
- `monitoring/error-rate.sh` (каждые 5 мин) — `grep ERROR` в логах
- `monitoring/smtp-worker.sh` (каждые 5 мин) — SMTP queue

Логи в `/var/log/ai-tutor-*.log`. **НЕ алерты в Telegram/Slack** (TODO).

### Backup verification

`manifest-*.md5` — md5 каждого backup-файла. `test-restore.sh` — реальный тест восстановления.

---

## 11. Sprint 1-5: что сделано

### Sprint 1 — Роль Учителя (блокер продукта)

**Цель:** замкнуть контур «исходник → AI-черновик → approve Учителя → публикация для Ученика».

**Решения:**
1. **RBAC-middleware** (`app/common/deps.py`): унифицированные зависимости, заменили ручные проверки в 11 endpoints.
2. **AI-генерация по 9-блоковому шаблону**: единый шаблон для всех материалов (key_ideas, rule, example, misconception, mistake, self_check, **practice_tasks (≥5)**, mini_test (5), flashcards).
3. **Workflow статусов:** draft → ai_generated → teacher_approved → published. State machine `_ALLOWED_TRANSITIONS`.
4. **Парсеры:** text/file (TXT/PDF/DOCX, OCR через `/voice/ocr`)/topic-only.
5. **Frontend:** `/teacher`, `/teacher/generate`, `/teacher/materials/[id]`.
6. **Migration 0008:** 6 полей в `learning_materials` (status, generated_by, approved_by, published_at, source_type, ai_confidence), 3 индекса.

**Trade-offs:**
- MockProvider в AI не возвращает валидный JSON → fallback `_build_fallback_material` собирает минимальную структуру с пометкой "не удалось разобрать".
- Approval Учителя обязателен — НЕЛЬЗЯ опубликовать draft напрямую (workflow через ai_generated).
- Редактирование опубликованного материала откатывает в `ai_generated` (требуется повторный approve).

**Числа:** +52 backend теста, +3 E2E, +3 frontend страницы, +9 API endpoints, +1 миграция.

### Sprint 2 — UX Ученика + Spaced Repetition

**Цель:** замкнуть цикл обучения с интервальным повторением.

**Решения:**
1. **SM-2 алгоритм** (`app/progress/spaced.py`) — стандарт для spaced repetition.
2. **Migration 0009:** 4 поля в `progress` (next_review_at, last_reviewed_at, review_count, easiness_factor).
3. **Endpoints:** `/progress/due-for-review` (с `days_overdue`), `/progress/review-result`.
4. **Новый модуль `app/student/`:** ученик видит **только published** материалы (`/api/v1/student/materials`).
5. **Frontend блок** «🔄 Сегодня к повторению» на главной `/subjects`.

**Trade-offs:**
- SM-2 упрощённый: interval = `6 * EF * review_count` вместо точного SM-2 (с учётом last_interval).
- EF floor 1.3 (стандарт).
- Лимит 20 items в `/due-for-review` (защита от over-fetch).

**Числа:** +19 backend тестов, +1 миграция, +4 API endpoints (student/progress).

### Sprint 3 — Кабинет Родителя

**Цель:** расширить кабинет родителя с агрегатами и экспортом.

**Решения:**
1. **Endpoint `/dashboard`** с агрегатами: subject_mastery (по всем предметам), streak (current/longest/total), time_stats (7/30 дней), top_mistakes, daily_activity_30d (с заполнением пропусков).
2. **Privacy policy:** 404 (НЕ 403) для не-своего ребёнка. В отчёте нет PII.
3. **PDF export** — HTML-шаблон через `/dashboard.pdf`, печать в PDF через браузер (НЕ weasyprint — лишняя зависимость).
4. **Frontend `/parent/dashboard/[id]`** — KPI карточки, графики активности (CSS-бары, не recharts), subject mastery с цветовой индикацией.

**Trade-offs:**
- Streak считается по датам attempts (НЕ minutes spent).
- НЕ реализован Telegram/email сводки (TODO в Sprint 3.3 — backlog).

**Числа:** +13 backend тестов, +1 страница, +2 API endpoints.

### Sprint 4 — Технический долг

**Цель:** закрыть дыры безопасности и observability.

**Решения:**
1. **Rate limit на `/auth/register`** — 5/час на IP (anti-abuse).
2. **Audit log retention** — endpoint `/admin/audit-log/purge` + cron `audit_cleanup.py` (ежедневно 3 AM).
3. **X-Forwarded-For trust** — `_client_ip()` хелпер, `TRUSTED_PROXIES` CIDR env.
4. **Multi-worker uvicorn** — Dockerfile уже использует `--workers 2`, rate-limit Redis-ready.

**Trade-offs:**
- Audit cron через `docker exec` (НЕ отдельный Python venv на хосте) — чтобы использовать SQLAlchemy из image.
- Hardcoded DB password в cron (вместо env file) — TODO.

**Числа:** +16 backend тестов, +1 cron-скрипт, +3 настройки.

### Sprint 5 — Наблюдаемость

**Цель:** базовая observability без сторонних сервисов.

**Решения:**
1. **Prometheus metrics** на `/metrics` — 5 типов метрик (HTTP, AI tokens, sessions).
2. **5xx → audit log** автоматически (best-effort).
3. **Nginx config** обновлён: `/metrics`, `/docs`, `/openapi.json` доступны снаружи.

**Trade-offs:**
- НЕ реализован Grafana dashboard (только Prometheus text format).
- НЕ реализованы alerts (Telegram/Slack) — TODO.
- AI service вызывает `record_ai_request()` только в `explain_topic` (НЕ во всех режимах).

**Числа:** +11 backend тестов, +1 endpoint (`/metrics`), +1 зависимость (`prometheus-client`).

---

## 12. Известные проблемы и тех. долг

### P0 (критично — влияет на продакшн)

1. **CI/CD не активирован.** Deploy вручную — 10 минут, error-prone. Уже один раз упало из-за `prometheus-client` в `requirements.txt`.
2. **НЕТ алертов** в Telegram/Slack при 5xx / healthcheck failure. Если прод упадёт ночью — никто не узнает до утра.
3. **WS broadcast НЕ работает на multi-worker** — если `--workers > 1`, сообщения не доходят до других воркеров. Нужен Redis pub/sub. (Sprint 4.4 — отмечено как TODO.)
4. **Self-signed HTTPS** — для реального использования нужно Let's Encrypt.
5. **DB credentials в cron** — захардкожены в `/etc/cron.d/ai-tutor-audit-cleanup`. Лучше через env file.

### P1 (важно — для качества)

6. **Markdown-рендер для AI-ответов** не реализован (Sprint 2.4). Текст приходит plain.
7. **Typewriter effect** для WS-стрима AI не реализован.
8. **Кнопка микрофона** в UI урока — backend есть (`/voice/transcribe`), но нет UI интеграции.
9. **Audit cron через `docker exec`** — костыль. Лучше отдельный контейнер с cron + DB access.
10. **JWT в localStorage** (НЕ httpOnly cookie) — XSS-уязвимость.
11. **Все секреты в .env** на production — лучше через Vault/SOPS.

### P2 (желательно — для масштабирования)

12. **RAG изолирован** (`app/rag.py` in-memory). Не подключён к промптам `explain/chat` (Sprint 4.5 — TODO).
13. **НЕТ миграции на pgvector** для RAG — в roadmap Sprint 4.
14. **Frontend state management** — везде `useState`. Для сложных страниц нужен Zustand/Jotai.
15. **НЕТ e2e тестов для teacher-flow** — Sprint 1.5 добавил только 3 smoke-теста, полноценного E2E нет.
16. **НЕТ тестов для `parents/dashboard.pdf`** в Playwright.
17. **Admin `/admin` не использует WebSocket** для real-time метрик (Sprint 5.3 — TODO).
18. **Backup offsite скрипт** — `ai-tutor-backup-offsite.sh` не проверялся.
19. **НЕТ HTTPS на `/metrics`** — Prometheus scraper получает данные по self-signed HTTPS, нужно либо internal scrape либо TLS cert.

### P3 (косметика / nice-to-have)

20. **Графики в `/parent/dashboard`** — самописные CSS-бары. Для rich charts нужен recharts/chart.js.
21. **Email-шаблоны** — plain text, без Jinja2 templates.
22. **Markdown в AI-ответах** — экранируется, но не рендерится.
23. **Dark mode** — нет.
24. **i18n** — только русский.
25. **Mobile-optimized UI** — есть PWA, но UX на мобиле не тестировался.

---

## 13. Идеи фич (backlog)

### Высокий приоритет

1. **🎤 Кнопка микрофона в `/topics/[id]`** — записывает голос, отправляет на `/voice/transcribe`, вставляет текст в поле. Уже есть backend!
2. **📊 Markdown + typewriter для AI-ответов** — сделать `react-markdown` + typewriter hook. Улучшит UX длинных объяснений.
3. **📧 Email-рассылка родителям** — еженедельный дашборд на email (через `/notifications/` + SMTP).
4. **📱 Telegram-бот для родителя** — `/parents/dashboard` в виде Telegram-сообщения (через тот же SMTP/in-app).
5. **📈 Grafana dashboard** — JSON для основных метрик (HTTP requests, AI tokens, errors).

### Средний приоритет

6. **🗄️ RAG на pgvector** — Sprint 4.5 отложен. Подключить top-k чанков к `explain/chat`. Поможет AI давать более релевантные ответы на основе учебника.
7. **🔍 Поиск по материалам** (`/materials/search`) — сейчас работает, но нужны fuzzy matching (BM25 или pgvector).
8. **🎯 Диагностика v2** — добавить уровни сложности, адаптивный выбор следующего вопроса (CAT — computerized adaptive testing).
9. **📦 Голосовые ответы от AI** (text-to-speech) — OpenAI TTS или локальный piper.
10. **🌙 Dark mode** — `prefers-color-scheme` + toggle.
11. **🎮 Gamification** — streak badges, mastery levels, достижения. Мини-игры по темам.

### Низкий приоритет

12. **👥 Multi-child support** для parent — сейчас один parent → один child по invite, нужна поддержка нескольких.
13. **📚 Разные классы (8-11)** — параметр `grade` уже есть, нужно расширить curriculum.
14. **🌍 i18n** — английский/украинский.
15. **📱 Mobile app (React Native)** — PWA есть, но native даст push notifications.
16. **🔐 2FA** для родителей.
17. **📊 Parent comparison** — родитель видит свой ребёнок vs средний по региону (анонимная статистика).

### Архитектурные улучшения

18. **WebSocket Redis pub/sub** для multi-worker broadcasting.
19. **Separate workers** для AI (CPU-intensive) и HTTP (I/O).
20. **Read replicas** для Postgres (для `/parent/dashboard` — read-heavy).
21. **CDN для статики** (frontend).
22. **API versioning** — `/api/v2/` для breaking changes (сейчас только v1).
23. **OpenTelemetry** вместо/параллельно с prometheus_client.
24. **gRPC** для internal backend↔backend communication (если будет второй сервис).

---

## 14. Открытые вопросы

Вещи, которые я (Hermes Agent от имени Игоря) хотел бы обсудить:

1. **Voice input/output** — стоит ли делать ASR + TTS для 13-летнего ученика с T1D? Или это overkill?
2. **Multi-child для parent** — реальная нужда или нишевая фича?
3. **Grades 8-11** — расширять ли curriculum сейчас, или сфокусироваться на качестве для 7 класса?
4. **Commercial path** — это останется личным проектом или есть план монетизации? Если коммерческий — нужны другие security/UX решения.
5. **Open-source release** — публиковать код? Что тогда делать с AI prompts (это конкурентное преимущество)?
6. **Privacy при расширении** — если будут новые страны (не РФ), как обрабатывать GDPR?
7. **AI provider lock-in** — MiniMax сейчас. Что если он изменит API или цены? Должна быть абстракция (уже есть `AIProvider Protocol`).
8. **RAG: локальный vs API embeddings** — sentence-transformers локально (CPU, ~300ms) vs OpenAI embeddings (платно, ~50ms).

---

## 15. Формат ответа

**Пожалуйста, дай ответ СТРОГО в следующем формате.** Это упростит мне работу с результатом.

### Секция A: Технический аудит (код/безопасность/перформанс)

Список найденных проблем с приоритетами P0/P1/P2/P3. Для каждой:

```
### [P0-P3] Короткий заголовок
**Файл:** `apps/backend/app/path/to/file.py:123`
**Проблема:** Что не так (1-2 предложения)
**Риск:** Что произойдёт, если не починить
**Решение:** Готовый код/diff (если есть)
**Сложность:** S/M/L (S=1-2ч, M=2-8ч, L=1+ день)
```

### Секция B: Архитектурный аудит

Анализ текущих решений. Что масштабируется, что нет. Конкретные предложения с trade-offs.

### Секция C: Новые фичи

Топ-10 фич с приоритетами. Для каждой:

```
### [P0-P2] Название
**Зачем:** Бизнес-ценность (1-2 предложения)
**Сложность:** S/M/L
**Готовые компоненты:** Что уже есть в коде, что можно переиспользовать
**Реализация:** Краткий план (3-7 шагов)
**UX:** Мокап/описание интерфейса
```

### Секция D: UX/продуктовый аудит

Конкретные проблемы UX (особенно для 13-летнего ученика с T1D и для родителя). Что улучшить с точки зрения:
- Когнитивной нагрузки
- Мотивации (без давления, со spaced repetition)
- Доступности (мобильный, низкая скорость интернета)
- Accessibility (WCAG — keyboard navigation, screen readers)

### Секция E: Roadmap на 3-6 месяцев

Конкретный план в формате:
```
Месяц 1 (Август 2026):
  - Sprint 6: ...
    - Подзадача 1: ...
    - Подзадача 2: ...
Месяц 2 (Сентябрь 2026):
  ...
```

### Секция F: Конкретные патчи

Если нашёл P0/P1 баги — приложи ГОТОВЫЕ файлы/diff. Можно использовать unified diff format:
```diff
--- a/apps/backend/app/foo.py
+++ b/apps/backend/app/foo.py
@@ -123,4 +123,8 @@
+    # fix description
+    if condition:
+        return value
```

### Секция G: Резюме (1 абзац)

3-5 предложений: что в проекте хорошо, что критично исправить, что отложить.

---

## 📎 Приложения (для справки)

### A. Файлы для обязательного чтения

```
/root/workspace/ai-tutor/
├── README.md                    # обзор
├── QUICK-START.md                # краткий обзор
├── MASTER-HANDOVER-PROMPT.md   # полный handover (Pilot Core Stage 1)
├── CHANGELOG.md                  # история изменений Sprint 1-5
├── docs/
│   ├── ROADMAP.md                # долгосрочные планы
│   ├── api.md                    # описание API endpoints
│   ├── architecture.md           # архитектура
│   ├── deployment.md             # деплой
│   ├── security.md               # политика безопасности
│   └── sprint-4.md               # детали Sprint 4
├── apps/backend/app/main.py      # FastAPI factory + middleware
├── apps/backend/app/common/deps.py  # RBAC
├── apps/backend/app/teacher/     # teacher-flow
├── apps/backend/app/progress/spaced.py  # SM-2
├── apps/backend/app/observability.py    # Prometheus
└── deploy/CICD.md                # CI/CD
```

### B. Команды для быстрой проверки

```bash
# Все тесты (должно быть 247 passed)
/usr/local/lib/hermes-agent/venv/bin/python3 -m pytest tests/ -q

# Health check
curl -sk https://192.168.1.86/health
curl -sk https://192.168.1.86/metrics | head -10
curl -sk https://192.168.1.86/openapi.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'paths: {len(d[\"paths\"])}')"

# SSH на production
ssh -i /root/.ssh/id_ed25519_kirill_ai root@192.168.1.86 "cd /opt/ai-tutor/deploy && docker compose ps"

# Проверка миграций
ssh -i /root/.ssh/id_ed25519_kirill_ai root@192.168.1.86 "cd /opt/ai-tutor/deploy && docker compose exec -T backend alembic current"
```

### C. Контекст про пользователя

- **Имя владельца:** Игорь (исследователь, средний уровень технический)
- **Стиль общения:** русский, краткий, без реверансов
- **Принципы:** «если мало контекста — уточни, не угадывай»; «дай готовые команды, а не длинные инструкции»; «не трогай .env, secrets/, node_modules без явного разрешения»
- **Предпочтения:** cache-friendly сессии (явные промпты, structured output), минимизация зависимостей, documentation-first

---

**Конец промта. Спасибо за глубокий аудит. Если нужны уточнения — спрашивай, я дополню.**
