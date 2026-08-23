# AI-Tutor — Сильные стороны

**Дата:** 2026-08-23

Проект имеет существенную зрелую базу. Это не прототип — это промышленный код с серьёзной архитектурой. Ниже — что реально хорошо и на чём можно строить.

---

## 1. Архитектура и продукт

### 1.1 Полноценный multi-role продукт

Четыре роли с RBAC, реальными endpoints и UI:

- **Student** — свои маршруты `/subjects`, `/topics/[id]`, `/student/badges`, `/diagnostic`
- **Parent** — `/parents`, `/parent/dashboard/[id]`, `/link-parent`, multi-child
- **Teacher** — `/teacher/generate`, `/teacher/materials`, `/teacher/topics`, workflow `draft → ai_generated → teacher_approved → published`
- **Admin** — `/admin/{realtime, tools, users, invites}` + `/admin/realtime` (WS dashboard)

Это не mock — реальные пользователи, реальная база, реальные права. Кирилл + родитель = нужны все 4.

### 1.2 Реальные школьные маршруты

42 темы в math (6 класс по Виленкину), 19 в алгебре, 24 в физике, 17 в литературе. Названия конкретные: «Среднее арифметическое», «НОД и взаимно простые», «Дробные выражения», «Прямая и обратная пропорциональные зависимости» — это содержание 7 класса, не generic плейсхолдеры.

Контрольные темы выделены бейджем «Контроль» (видно в UI), base/medium/hard уровни проставлены в данных.

### 1.3 Production-grade backend stack

| Слой | Технология | Зрелость |
|---|---|---|
| API | FastAPI 0.115 (async) | ✅ modern |
| ORM | SQLAlchemy 2 + Alembic | ✅ 12+ миграций |
| БД | PostgreSQL 16 | ✅ |
| Cache | Redis 7 (rate-limit, budget, OCR cache) | ✅ |
| ASGI | uvicorn multi-worker (2 на проде) | ✅ |
| Search | RAG с vector store (paraphrase-multilingual embeddings) | ✅ |
| AI gateway | Multi-provider (MiniMax primary, hash-based fallback) | ✅ |
| Observability | Prometheus 0.21 + Grafana дашборд + audit log | ✅ |
| Reverse proxy | Nginx 1.27 (SSL, rate-limit, WS upgrade, /grafana/ subpath) | ✅ |
| Container | Docker Compose (7 контейнеров, healthchecks) | ✅ |

### 1.4 Контент-pipeline (RAG)

- `pdftotext -layout` с single-call + split-on-\f (избегает N subprocess overhead).
- Chunker с 1200/200 char overlap для topics.
- Embedding cache в БД (`rag_chunks`).
- BM25 + vector hybrid ranking.
- Retrieval probes с recall@k, MRR@k по каждому subject.
- Изолированный SQLite импорт для каждого предмета (`tmp/isolated_import_and_probes.py`).

---

## 2. AI-возможности

### 2.1 5 режимов AI

| Режим | Что умеет | T1D-friendly |
|---|---|---|
| Explain | правило + пример + самопроверка, markdown | ✅ длинный, но структурированный |
| Hint | 3 уровня подсказки (от мягкого намёка до разбора) | ✅ protects frustration |
| Check | серверная валидация через `GeneratedExerciseInstance` (Pilot Core) | ✅ прозрачность |
| Generate | задания по теме | ✅ |
| Chat | диалог по теме с контекстом | ✅ |

### 2.2 Structured output + retry

3 retry с ужесточённым промптом при invalid JSON. Метрика `ai_parse_status_total{mode, result}` видна в Grafana. Fallback не молчит — записывается как `parse_status="fallback"` для UI/алертов.

### 2.3 Markdown rendering на сервере

`markdown-it-py` + regex sanitizer для AI-вывода. Не используется `dangerouslySetInnerHTML` без фильтра. WS-стрим имеет параллельный client-side parser (`lib/markdown.ts`) для realtime typewriter-курсора.

### 2.4 AI budget + rate-limit (Sprint 9.4)

Per-user Redis counter с graceful in-memory fallback. Лимит 200 req/день + 200K токенов на user. Проверено: у Кирилла использовано 2/20000 — запас огромный.

---

## 3. UX / front-end

### 3.1 Prism/Split дизайн

Dark theme, split-layout на логине, плотная типографика, accent-цвета (фиолетовый/лавандовый). Нет белых панелей. Кирилл не увидит «корпоративный» UI — выглядит как продукт, а не как form-template.

### 3.2 T1D-критичные UX-фичи

- **Auto-save:** localStorage каждые 5 сек + server sync каждые 15 сек. При потере связи/перезагрузке — восстановление без вопроса.
- **3 уровня hint:** ребёнок не остаётся с задачей один на один.
- **Баджи без streak-pressure:** только за конкретные действия («Начал тему», «Объяснил своими словами»), не за consecutive days / missed days.
- **Voice rate-limit per-user:** in-memory sliding window, 60 сек, 6 попыток/час.
- **Понятный «следующий шаг»:** на странице темы виден CTA «Начать объяснение» / «Начать практику».

### 3.3 Mobile-friendly

Viewport container в Next.js, responsive CSS-grid на `/subjects`. Хотя не проверено детально в реальном мобильном браузере — структура готова.

### 3.4 Hint 3 уровня + auto-save + cat-адаптивная диагностика

Это базовая комбинация, которая превращает «учебник в браузере» в реального репетитора.

---

## 4. Безопасность и приватность

### 4.1 JWT в httpOnly cookies (Sprint 10.1)

- Access + refresh tokens в cookies (HttpOnly, Secure в prod, SameSite=Lax).
- Refresh rotation.
- Dual-source auth (Bearer + cookie) — плавная миграция.
- WS auth через query token (правильно для браузерного WS).
- 12+ pitfalls зафиксировано в `references/jwt-cookie-pattern.md`.

### 4.2 RBAC + rate-limit + audit

- 11+ endpoints защищены `require_role(...)` dep.
- Redis rate-limit на auth (login 10/15 мин, register 5/час) — закрывает brute force.
- AI rate-limit 30/мин/user + budget 200/день.
- Audit log с auto IP-capture (ContextVar), TTL 90 дней, 5xx auto-record.
- Admin endpoint для purge.

### 4.3 Server-owned assessment (Pilot Core 2026-07-13)

- `GeneratedExerciseInstance` — opaque projection без `correct_answer`.
- v2 endpoints `/api/v2/exercises/{generate, answer}` — server-trusted.
- Legacy v1 `/attempts` теперь проходит через `_server_validate_attempt`.
- Защита от client-side forgery.

### 4.4 Markdown XSS-safe

- Render только на сервере через `markdown-it-py` с `html=False`.
- Sanitizer regex удаляет `on*`, `style`, `javascript:`, `src`, `href`.

### 4.5 PII minimization

Parent dashboard НЕ показывает содержимое чатов с AI и сырые попытки — только агрегаты. 404 (не 403) для не-привязанного ребёнка, чтобы не палить существование.

---

## 5. Тестирование

### 5.1 Объём и стабильность

- **637 + 135 = ~772 backend тестов**, 20 skipped (по 2 рапортам — audit 2026-08-22 + status 2026-08-23).
- **Flake-фикс:** `asyncio_default_fixture_loop_scope=function` в `pytest.ini` закрыл `test_sprint32_parent_2fa` race condition.
- **Inverted test pattern:** при замене permissive теста на fail-closed — `assert algebra.mvp_status != "mvp_ready"` (защита от refactor regression).
- **HTTP-контракты:** `/health` schema, math-6 pilot contracts на 15 P0 topics.

### 5.2 Автоматический Playwright

- `mvp-student-flow.spec.ts` — login → catalog → subject → topic → explain → practice → answer.
- `parent.spec.ts` — parent dashboard E2E.
- Mobile viewport в плане (нужен disposable CI runner).

### 5.3 Контрактные тесты на evidence

- `test_evidence_schema.py` — fail-closed валидация evidence.json.
- `test_manifest_provenance.py` — checksums, source URL, license decision.
- `test_retrieval_benchmark.py` — recall@k / MRR@k per subject.

---

## 6. Инфра и devops

### 6.1 Tar-pipe deploy + env-passthrough

Один паттерн доставки: `tar | ssh "tar -xf - -C /opt"` + `docker compose build backend frontend` + `up -d` + smoke. Безопасный, проверенный, не требует git на проде.

### 6.2 Backup + offsite (частично fail-closed)

- Cron 03:00 для `backup.sh` + опционально offsite-скрипт.
- `test-restore.sh` запускается в понедельник 04:00 UTC — реальная проверка restore в test DB.
- Snapshot до и после изменений evidence (`/tmp/ai-tutor-deploy-snapshots/`).
- Fail-closed проверка: source и destination должны быть на разных mountpoints (`stat -c '%d:%i'` + `df --output=target`).

### 6.3 Disposable CI environment

`deploy/disposable-staging.sh` поднимает LXC-аналог на этой же машине — для replay миграций, проверки `/health`, `/ready`, Postgres/Redis/auth/deterministic flow.

### 6.4 Release pipeline (Pilot Core 2026-07-13)

Скрипты в `deploy/release/`:
- `preflight.sh` — health + backup + ready до deploy.
- `deploy.sh` — build + smoke + atomic up.
- `rollback.sh` — image snapshot restore (через `docker load -i`).
- `smoke.sh` — end-to-end `explain` smoke на production URL.

### 6.5 Cron hygiene

8 active cron jobs:
- 03:00 — backup DB + uploads + manifest
- */5 — healthcheck, error-rate, smtp-worker
- 03:00 — audit cleanup (TTL)
- воскресенье 18:00 MSK — weekly summary emails
- понедельник 04:00 UTC — backup verify (test-restore)

Все секреты вынесены в `/etc/ai-tutor/.env` (600 root:root), cron source'ит их через `set -a; source; set +a`.

---

## 7. Документация и process

### 7.1 Полная документация проекта

~4000 строк MD:
- README (503 строк) — overview + текущий статус
- QUICK-START (162) — быстрая справка
- PROMPT-FOR-OTHER-AI (559) — базовый AI-промт
- AI-DEEP-AUDIT-PROMPT (990) — глубокий аудит
- MASTER-HANDOVER-PROMPT (742) — handover для сторонней AI
- CHANGELOG (331+) — Sprint 1-10 история
- ROADMAP (380) — долгосрочный план
- api.md (179), architecture.md (121), deployment.md, security.md, sprint-4.md
- plans/SPRINT-6-PLAN.md (506) — спринты 6-10 с чекбоксами
- + ~30 спринт-репортов, audit-документов, handover-промтов от текущей итерации

### 7.2 Skills (reusable knowledge)

В `~/.hermes/skills/devops/`:
- `ai-tutor-deploy` — production runbook со всеми pitfalls (23+ зафиксированных)
- `ai-tutor-readiness-evidence-store` — fail-closed evidence-store pattern
- `ai-tutor-textbook-import` — Russian textbook PDF import
- `local-ssh-rsync-deploy` — verified rsync pattern
- + references: `pitfalls.md`, `jwt-cookie-pattern.md`, `nginx-subpath-and-grafana.md`, `server-owned-assessment-pattern.md`, `release-pipeline-design-review.md`

Это позволяет любой следующей сессии (другой AI-агент, другой человек) подхватить проект без re-discovery.

### 7.3 Autonomous execution pattern

Спринты 1-10 выполнены автономно за 2 сессии по handover-промту без повторяющихся вопросов. Каждый спринт:
1. todo list на старте
2. реализация
3. pytest gate
4. tar-pipe deploy
5. smoke на проде
6. CHANGELOG entry + commit

**Стиль «план → исполнить → доказать»** — именно то, что нужно для передачи Кириллу.

---

## 8. Конкретные достоинства для Кирилла + родителя

| Что умеет | Для кого | Как работает |
|---|---|---|
| `/login` и mobile-friendly вход | Кирилл | простая форма, secure cookies |
| `/subjects` — выбор предмета | Кирилл | красивый каталог, одна кнопка «Открыть» |
| `/topics/[id]` — урок | Кирилл | «Объяснить» → markdown + пример; «Практика» → проверка; «Чат» → диалог |
| Auto-save каждые 5 сек | Кирилл | закрыл вкладку, открыл — продолжает с того же места |
| Hint 3 уровня | Кирилл | не остаётся один на один с задачей |
| Voice rate-limit | Кирилл | микрофон не превращается в спам |
| Баджи без streak | Кирилл | мотивация не превращается в стресс |
| `/parents` | Родитель | видит всех детей, видит дашборд |
| Weekly summary email | Родитель | воскресенье 18:00 MSK, сводка за неделю |
| Parent dashboard со SM-2 | Родитель | mastery по предметам, streak, time stats, weak topics |

**Самый сильный момент:** Родитель получает еженедельный отчёт, а Кирилл получает личного репетитора с правильными safeguards. Это закрывает реальную проблему T1D-семьи.

---

## 9. Что отличает этот проект от «просто CRUD с AI»

1. **Real RAG, не просто stubs:** vector store + bm25 + cache + per-subject retrieval probes.
2. **Real SM-2, не просто счётчик:** interval EF, quality mapping, scheduled next_review_at.
3. **Real RBAC, не просто login:** deps, audit trail, per-role views.
4. **Real observability, не просто health:** Prometheus metrics + Grafana dashboard + audit log + per-feature rate-limits.
5. **Real offline-first для ребёнка:** auto-save в localStorage + server sync + topic_drafts в БД.
6. **Real server-owned assessment, не просто клиентская галочка:** GeneratedExerciseInstance + v2 endpoints + идемпотентность.
7. **Real Markdown render pipeline (не dangerouslySetInnerHTML):** server-side `markdown-it-py` + regex sanitizer + client-side parser для realtime.

Это 7 жёстких мест, где многие «учебные AI-приложения» сдаются и оставляют либо TODO, либо костыль. Здесь — закрыто.
