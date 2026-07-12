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
├── main.py          # создание приложения, lifespan, middleware
├── config.py        # pydantic-settings (всё через env)
├── db/              # SQLAlchemy engine, Base, get_db()
├── common/          # общие зависимости, ошибки
├── auth/            # (Этап 2)
├── users/           # (Этап 2)
├── subjects/        # (Этап 3)
├── topics/          # (Этап 3)
├── exercises/       # (Этап 4)
├── diagnostics/     # (Этап 7)
├── progress/        # (Этап 8)
├── ai/              # AI Gateway (Этап 5)
├── materials/       # (Этап 10)
├── parents/         # (Этап 9)
├── admin/           # админский CRUD (Этап 3+)
└── api/v1/          # сборка роутеров FastAPI
```

Каждый модуль в `apps/backend/app/<module>/` придерживается одинаковой
структуры: `models.py` (SQLAlchemy), `schemas.py` (Pydantic),
`service.py` (бизнес-логика), `router.py` (FastAPI endpoints).
Это упрощает навигацию и поддержку.

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
- `HermesProvider` — реальный провайдер (OpenRouter/Hermes API)
- `MockProvider` — для тестов и локальной разработки без ключа

Все параметры (`AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`, таймауты,
retry, лимиты длины) берутся из `.env`. Ключ **никогда** не пишется
в лог или в ответ API.

## Хранилище файлов

Локальная папка `apps/backend/uploads/` монтируется как volume
(`uploads:/app/uploads`). В дальнейшем легко заменить на S3 — для
этого меняется только `materials/service.py`, контракт не страдает.

## Миграции БД

Alembic, автогенерация отключена на старте (чтобы не было сюрпризов).
Каждое изменение схемы — отдельная миграция в `apps/backend/alembic/versions/`.
Применение: `make migrate` или `docker compose exec backend alembic upgrade head`.