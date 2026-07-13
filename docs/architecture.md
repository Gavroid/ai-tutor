# Архитектура

## Высокоуровневая схема

```
Интернет
  ↓
Reverse Proxy (Nginx, порт 80/443)
  ↓
Proxmox VM или LXC
  ├── Frontend (Next.js, internal:3000)
  ├── Backend  (FastAPI, internal:8000)
  ├── DB       (PostgreSQL, internal:5432)
  └── (опц.) Redis
```

Наружу открыт **только** Nginx. Backend, Frontend и Postgres живут в
двух bridge-сетях (`internal` — для служебного трафика, `external` — для
Nginx). Postgres изолирован в `internal` и недоступен из Nginx.

## Слои backend (FastAPI)

```
app/
├── main.py            # создание приложения, lifespan, middleware
├── config.py          # pydantic-settings (всё через env)
├── observability.py   # Prometheus middleware (Sprint 5.1)
├── db/                # SQLAlchemy engine, Base, get_db()
├── common/            # общие зависимости (require_role), ошибки
├── auth/              # JWT, password reset, OAuth2 (WIP)
├── users/             # User + StudentProfile + PUBLIC_REGISTRATION_ALLOWED_ROLES
├── subjects/          # 12 предметов × 186 тем × 42 подтемы, curriculum_7_class
├── topics/            # (внутри subjects)
├── diagnostics/       # generate questions, expire, CAT-адаптивная
├── progress/          # mastery, attempts, spaced repetition (SM-2, Sprint 2)
├── ai/                # AI Gateway (Sprint 5): provider protocol, MockProvider,
│                      # HermesProvider, sanitize, websocket, budget, markdown_render
├── teacher/           # Sprint 1: AI-генерация материалов + workflow статусов
├── materials/         # upload (PDF/DOCX/TXT), OCR, sources
├── parents/           # dashboard (Sprint 3), privacy, invite
├── admin/             # CRUD users, audit log, realtime (Sprint 5), budget
├── voice/             # Whisper ASR (Sprint 2)
├── notifications/     # in-app + email (aiosmtplib) + retry
├── v2/                # Pilot Core Phase 2: secure exercises (/exercises/{generate,answer})
├── rag.py             # in-memory hash-based vector store (Sprint 8 → pgvector)
├── rag_router.py      # RAG endpoints (/index, /search, /material/{id}, /stats)
└── scripts/           # seed.py, seed_users.py (CLI с PILOT_SEED_TOKEN)
```

Каждый модуль в `apps/backend/app/<module>/` придерживается одинаковой
структуры: `models.py` (SQLAlchemy), `schemas.py` (Pydantic),
`service.py` (бизнес-логика), `router.py` (FastAPI endpoints).
Это упрощает навигацию и поддержку.

**Версионирование API:** breaking changes → `/api/v2/...` (например, secure exercise
flow в Pilot Core Phase 2). Старая версия живёт ≥ 6 месяцев после релиза новой.

## Frontend (Next.js App Router)

```
apps/frontend/
├── app/                 # маршруты (страницы)
│   ├── layout.tsx       # корневой layout, html lang="ru"
│   ├── page.tsx         # главная (MVP-каркас)
│   └── ...
├── components/          # переиспользуемые компоненты (Этап 4+)
├── lib/                 # утилиты, API-клиент
├── hooks/               # React hooks (useAuth, useTopics, ...)
├── types/               # TypeScript-типы, дублирующие Pydantic
└── public/              # статические файлы
```

Все запросы к backend идут через относительный путь `/api/*`, который
Next.js проксирует на `NEXT_PUBLIC_API_URL` через `next.config.mjs`.

## Поток данных

### Создание темы (пример, Этап 3)
```
teacher (frontend)
  → POST /api/v1/topics  (Next.js → FastAPI)
    → auth dependency (JWT verify, role=teacher)
    → Pydantic schema validation
    → service.create_topic(db, data, current_user)
      → INSERT INTO topics ...
    → 201 Created, JSON
```

### Объяснение темы AI (пример, Этап 6)
```
student (frontend, чат)
  → POST /api/v1/ai/explain  { topic_id }
    → auth (role=student)
    → service.explain_topic(db, topic_id, current_user)
      → загружает тему, историю, профиль
      → ai_gateway.complete(prompt, context, mode="explain")
        → httpx → AI_BASE_URL/chat/completions
        → retries, timeout, sanitization
      → сохраняет chat_message
      → возвращает ответ
    → 200 OK, JSON
```

## AI Gateway

`apps/backend/app/ai/` инкапсулирует всё взаимодействие с внешней моделью.
Контракт:

```python
class AIProvider(Protocol):
    async def complete(self, req: AIRequest) -> AIResponse: ...
```

Реализации:
- `HermesProvider` — реальный провайдер (OpenAI-compatible, MiniMax-M3 через Anthropic endpoint)
- `MockProvider` — для тестов и локальной разработки без ключа (активируется по `key == "mock-*"`)

Все параметры (`AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`, таймауты,
retry, лимиты длины) берутся из `.env`. Ключ **никогда** не пишется
в лог или в ответ API.

**Режимы AI** (7 всего): `explain`, `hint`, `check`, `generate`, `diagnose`, `chat`, **`quiz`** (Sprint 1, добавлен 13.07.2026). Каждый режим — отдельный endpoint в `app/ai/router.py` со своим системным промптом (`app/ai/prompts.py`) и structured-output схемой.

**Бюджет:** дневной лимит (5xx/день) реализован в `app/ai/budget.py` (Redis-backed). При превышении — 429.

**Метрики:** все AI-вызовы инкрементят `ai_tokens_total{role}` и `ai_requests_total{mode,status}` (Sprint 5.1). Парсинг ответа в `structured` JSON для режимов `check`, `generate`, `quiz`.

## RAG (Retrieval-Augmented Generation)

`apps/backend/app/rag.py` + `app/rag_router.py`. **Текущее состояние:** in-memory
hash-based vector store (теряется при рестарте контейнера, но приемлемо для MVP).
Embeddings: hash fallback (без sentence-transformers, чтобы не съедать RAM на 4 GB LXC).

**Endpoints:** `POST /api/v1/rag/index`, `POST /api/v1/rag/search`, `DELETE /api/v1/rag/material/{id}`, `GET /api/v1/rag/stats`.

**Sprint 8 план:** переход на pgvector (`chunks` таблица, `hnsw` индекс), API embeddings + Redis cache. RAM-инженеринг: 4 GB LXC + sentence-transformers = риск OOM, предпочтение — external API.

## Хранилище файлов

Локальная папка `apps/backend/uploads/` монтируется как volume
(`uploads:/app/uploads`). В дальнейшем легко заменить на S3 — для
этого меняется только `materials/service.py`, контракт не страдает.

## Мониторинг и observability (Sprint 5)

- **`/metrics`** (Prometheus text format) — `http_requests_total{method,path,status}`,
  `http_request_duration_seconds{method,path}`, `ai_tokens_total{role}`,
  `ai_requests_total{mode,status}`, `active_sessions_total`.
- **Middleware** (`app/observability.py`) — собирает метрики автоматически
  с path normalization.
- **Prometheus сервис** в `docker-compose.yml`, scrape `backend:8000/metrics`
  каждые 15 сек. **Grafana** с provisioning (`deploy/grafana/dashboards/ai-tutor-overview.json`),
  доступ через nginx proxy.
- **5xx → audit_log**: middleware логирует `action=error.5xx` в `audit_logs`
  для последующего анализа в `/admin/audit-log`.

## Миграции БД

Alembic, автогенерация отключена на старте (чтобы не было сюрпризов).
Каждое изменение схемы — отдельная миграция в `apps/backend/alembic/versions/`.
Применение: `make migrate` или `docker compose exec backend alembic upgrade head`.