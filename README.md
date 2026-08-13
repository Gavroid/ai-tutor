# AI-репетитор 7 класса

Production-ready MVP для персонального AI-репетитора: ученик, родитель, учитель и администратор в одном self-hosted контуре.

## Текущий статус

- **Production:** `https://school.431a.ru`
- **LAN:** `https://192.168.1.86`
- **Branch:** `mvp-rescue`
- **Manual QA:** закрыт в `docs/pilot-walkthrough-notes.md`
- **Design source of truth:** `docs/PRISM-DESIGN-PATTERNS.md`
- **Further plan:** `docs/FURTHER-DEVELOPMENT-PLAN-2026-08-13.md`

Пароли, токены, ключи и `.env` не документируются в репозитории. Для тестовых аккаунтов используйте существующий QA-контекст/секреты, не вставляйте пароли в docs.

## Что работает

| Зона | Статус |
|---|---|
| Student Flow | Desktop/mobile smoke пройден; `/subjects`, `/subjects/[id]`, `/topics/[id]` |
| Lesson chat | Чат, объяснение, практика; mobile reading layout; SafeMarkdown tables/lists/paragraphs |
| Parent Flow | `/parents`, `/parent/dashboard/[studentId]`, privacy boundary, linked children summary |
| Teacher Flow | `/teacher`, `/teacher/generate`, materials/topics редакторы, тёмный Prism UI |
| Admin Flow | `/admin` как один URL с internal tabs; audit/users/stats/tools/invites/realtime |
| Realtime monitoring | Fixed snapshot + manual refresh; backend metrics single-worker until multiprocess mode |
| Backup | Local DB/uploads backup + SMB offsite verification |
| Ops | Docker Compose, Nginx, PostgreSQL, Redis, Prometheus, Grafana |

## Архитектура

```text
Internet / LAN
  ↓
Nginx / proxy layer
  ↓
Docker Compose on 192.168.1.86
  ├── frontend   Next.js 16 / React 19
  ├── backend    FastAPI / SQLAlchemy / Alembic / AI Gateway
  ├── db         PostgreSQL 16
  ├── redis      Redis
  ├── prometheus internal scrape of backend:8000/metrics
  └── grafana    provisioned dashboards
```

Backend сейчас намеренно запущен с `uvicorn --workers 1`: текущие Prometheus counters живут в памяти процесса, поэтому multiple workers дают прыгающие Realtime-значения. Возврат к нескольким воркерам — отдельная задача после Prometheus multiprocess mode.

## Основные маршруты

| Route | Назначение |
|---|---|
| `/login` | Авторизация |
| `/subjects` | Главная ученика / предметы |
| `/subjects/[id]` | Темы предмета |
| `/topics/[id]` | Урок: чат, объяснение, практика |
| `/parents` | Кабинет родителя |
| `/parent/dashboard/[studentId]` | Дашборд ребёнка |
| `/teacher` | Учительская библиотека материалов |
| `/teacher/generate` | Генерация материала |
| `/teacher/topics/[id]` | Редактор готовности темы |
| `/admin` | Админка: tabs внутри одного URL |
| `/diagnostic` | Диагностика |
| `/link-parent` | Привязка родителя |

`/admin/invites` и `/admin/realtime` сохранены только как compatibility redirects на `/admin`. Видимая навигация админки не должна уходить с `/admin`.

## Backend modules

```text
apps/backend/app/
  ai/              AI gateway, prompts, sanitize, WebSocket helpers
  admin/           admin APIs, realtime snapshot, audit/admin ops
  auth/            cookie/JWT auth, password reset, OAuth skeleton
  common/          shared deps/RBAC
  diagnostics/     diagnostic sessions
  materials/       uploads and source handling
  parents/         parent dashboard/invite privacy logic
  progress/        mastery/attempts/spaced repetition
  subjects/        curriculum and topics
  teacher/         teacher material generation/workflow
  users/           user models/services
  v2/              secure exercise flow
```

## Frontend modules

```text
apps/frontend/app/
  subjects/        student subject/topic surfaces
  topics/[id]/     split lesson UI: lesson/chat/practice
  parents/         parent console
  teacher/         teacher console/materials/topics
  admin/           single-route admin console
  diagnostic/      diagnostic flow
  link-parent/     parent link flow
```

Important UI rule: preserve dark Prism/Split design. Do not reintroduce white Tailwind cards, blue text links, `/admin?tab=...`, or duplicated admin routes.

## Verification commands

Frontend:

```bash
cd /root/workspace/ai-tutor/apps/frontend
npm run typecheck
npm run build
```

Backend targeted smoke:

```bash
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest tests/test_health.py -q
```

Production health:

```bash
curl -sk -w '\nHTTP=%{http_code}\n' https://192.168.1.86/ready
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
  'cat /opt/ai-tutor/.mvp-rescue-commit; cd /opt/ai-tutor/deploy && docker compose ps'
```

## Backup

Production backup scripts live in:

```text
/opt/ai-tutor/deploy/backup/backup.sh
/opt/ai-tutor/deploy/backup/ai-tutor-backup-offsite.sh
```

Typical backup creates:

```text
/opt/ai-tutor/deploy/backup/_out/db-YYYYMMDDTHHMMSSZ.sql.gz
/opt/ai-tutor/deploy/backup/_out/uploads-YYYYMMDDTHHMMSSZ.tar.gz
/opt/ai-tutor/deploy/backup/_out/manifest-YYYYMMDDTHHMMSSZ.md5
```

Do not print SMB credentials or secret file contents.

## Development priorities

See `docs/FURTHER-DEVELOPMENT-PLAN-2026-08-13.md`.

Recommended order:

1. Release/docs hygiene.
2. Frontend refactor without visual changes.
3. Monitoring cleanup.
4. Backend reliability/security debt.
5. RAG/content quality.
6. Student learning loop.
7. Parent and teacher product layers.
8. Ops/disk hygiene runbook.
