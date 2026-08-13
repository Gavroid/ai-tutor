# Архитектура AI-Tutor

_Last updated: 2026-08-13_

## Высокоуровневая схема

```text
Internet / LAN
  ↓
Nginx / proxy layer
  ↓
Docker Compose on 192.168.1.86
  ├── frontend    Next.js 16 / React 19
  ├── backend     FastAPI / SQLAlchemy / Alembic / AI Gateway
  ├── db          PostgreSQL 16
  ├── redis       Redis
  ├── prometheus  internal scrape of backend:8000/metrics
  └── grafana     provisioned dashboards
```

Наружу открыт только proxy/frontend/API edge. Backend, DB, Redis, Prometheus and Grafana живут внутри Docker/LAN контура. `/metrics` не должен быть публичным edge endpoint; Prometheus скрейпит backend внутри Docker network.

## Текущие важные решения

- Production domain: `https://school.431a.ru`.
- Canonical host redirect живёт в `apps/frontend/proxy.ts`.
- `/admin` — единый UI route с internal tabs.
- `/admin/invites` и `/admin/realtime` — compatibility redirects на `/admin`.
- Admin Realtime — fixed HTTP snapshot + manual refresh; WebSocket route legacy/internal.
- Backend работает с `uvicorn --workers 1`, потому что текущие Prometheus counters in-process. Возврат к multiple workers требует Prometheus multiprocess mode.
- Parent privacy boundary: parent видит агрегаты и рекомендации, но не сырой AI chat.
- Student-facing AI output must be sanitized/readable: no raw JSON, no `<think>`, no raw markdown tables, no broken math markers.

## Backend layers

```text
apps/backend/app/
  main.py             FastAPI app, middleware, health, metrics edge rules
  config.py           env-based settings
  observability.py    Prometheus middleware and metrics endpoint
  db/                 SQLAlchemy session/base
  common/             shared deps and RBAC
  auth/               cookie/JWT auth, password reset, OAuth skeleton
  users/              User / StudentProfile
  subjects/           curriculum, subjects, topics
  ai/                 AI gateway, prompts, sanitize, budget, WS helpers
  v2/                 secure exercise flow
  diagnostics/        diagnostic sessions
  progress/           attempts, mastery, spaced repetition
  parents/            parent invite/dashboard/privacy logic
  teacher/            teacher material workflow
  materials/          uploads/source parsing
  admin/              admin APIs, audit, realtime snapshot, ops
  cgm/                CGM integration surface
  voice/              voice/transcription endpoints
  notifications/      in-app notification infrastructure
```

Module pattern is generally:

```text
models.py   SQLAlchemy models
schemas.py  Pydantic schemas
service.py  business logic
router.py   FastAPI endpoints
```

## Frontend layers

```text
apps/frontend/
  app/                 App Router pages
  components/          shared UI components
  lib/                 API client, markdown renderer, utilities
  types/               TypeScript types
  public/              PWA/static assets
  proxy.ts             canonical host redirect
```

Key routes:

| Route | Role / purpose |
|---|---|
| `/subjects` | student subject landing |
| `/subjects/[id]` | topic list |
| `/topics/[id]` | split lesson UI: lesson/chat/practice |
| `/parents` | parent console |
| `/parent/dashboard/[studentId]` | parent child dashboard |
| `/teacher` | teacher material library |
| `/teacher/generate` | teacher material generation |
| `/teacher/topics/[id]` | topic readiness editor |
| `/admin` | admin single-route console |
| `/diagnostic` | diagnostic flow |
| `/link-parent` | parent linking flow |

## Admin architecture

The visible admin console must remain one route:

```text
/admin
```

Tabs are internal React state:

```text
Audit log
Пользователи
Статистика
Инструменты
Invites
Realtime
```

Rules:

- URL remains `/admin` while switching tabs.
- Do not use `/admin?tab=...` for visible navigation.
- Do not link visible tabs to `/admin/invites` or `/admin/realtime`.
- Long tables scroll inside the admin content area, not by stretching the outer frame.

## Lesson/chat architecture

`/topics/[id]` is the student learning surface:

```text
LessonRail      explanation controls and context
TutorChat       AI messages, SafeMarkdown, follow-up chips
PracticePanel   generated exercise and answer checking
```

Mobile layout uses tabs (`Чат`, `Урок`, `Практика`). `Объяснить` and `Практика` must switch to the relevant mobile panel after generating content.

## Realtime monitoring

Admin Realtime is intentionally not an auto-updating stream right now.

Current behavior:

- load one snapshot when opening the Realtime tab;
- manual `Обновить` button fetches another snapshot;
- counters are cumulative since backend start;
- backend RAM is shown from cgroup data (`memory.current`) as MiB unless a real cgroup limit exists;
- HTTP counters may increment on manual refresh because the snapshot endpoint itself is an HTTP request.

Why backend workers = 1:

- `prometheus_client` counters are in-process;
- multiple uvicorn workers create multiple independent metric registries;
- Realtime would alternate between workers unless Prometheus multiprocess mode is implemented.

## Monitoring

Prometheus scrapes:

```text
backend:8000/metrics
```

Important metrics:

- `http_requests_total{method,path,status}`
- `http_request_duration_seconds{method,path}`
- `ai_tokens_total{role}`
- `ai_requests_total{mode,status}`
- parent/student custom metrics where implemented

Expected 4xx should be classified separately from product errors. Example: missing draft `404` can be expected, while repeated unknown `404`, `403`, `429`, and any `5xx` need attention.

## Backup and restore boundary

Production backup scripts live on the server under:

```text
/opt/ai-tutor/deploy/backup/
```

Main artifacts:

```text
db-YYYYMMDDTHHMMSSZ.sql.gz
uploads-YYYYMMDDTHHMMSSZ.tar.gz
manifest-YYYYMMDDTHHMMSSZ.md5
```

Offsite SMB verification is part of the backup workflow. Do not expose SMB credentials or secret files.

## Technical debt map

Highest-value next work:

1. Split giant frontend files without visual changes.
2. Improve monitoring labels/expected 4xx classification.
3. Add register rate-limit and audit retention.
4. Plan Prometheus multiprocess before restoring multiple backend workers.
5. Move RAG toward persistent storage and topic-quality gates.
