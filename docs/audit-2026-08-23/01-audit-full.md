# AI-Tutor — Полный аудит (код, UI, продакшен, инфра)

**Дата:** 2026-08-23
**Цель аудита:** Подготовка проекта к реальному использованию одним пользователем — Кириллом (ученик 7 класса, 13 лет, T1D) и его родителем.
**Метод:** Read-only разведка + UI smoke (login, subjects, topics, parent dashboard) + API smoke + проверка прод-сервера через ssh. Прод-код не изменялся, файлы на проде не правились.
**Аудитор:** Hermes Agent (automated, structured)

---

## 1. Оценка готовности (verdict)

| Аспект | Статус | Комментарий |
|---|---|---|
| Архитектура | ✅ Зрелая | backend FastAPI+SQLAlchemy+Postgres, frontend Next 16+React 19, 7 контейнеров, инфра-прокси, Prometheus+Grafana |
| Базовые функции | ✅ Работает | login, list subjects, list topics, AI explain, AI budget, parent dashboard, JWT cookies |
| Контент учебный | ⚠️ Частично | 16 предметов, 225 тем заявлено. Реально содержимое без проверки — м.б. generic fallback |
| **Готовность (readiness)** | **❌ СЛОМАНО** | `evidence.json` разрешает pilot для ВСЕХ 16 предметов, включая image-only/OCR. `promotion_allowed=true AND blocked_reason=blocked_ocr` одновременно — invariant нарушен |
| Полная автоматизация E2E | ⚠️ Частично | MVP E2E падает на Explain в рабочем окружении (по audit от 2026-08-23) |
| Безопасность | ⚠️ Средняя | JWT-cookie ✅, rate-limit ✅, XFF-trust ✅. CVEs в transitive deps (98) — high risk если ехать в реальный инет |
| Backup/restore | ⚠️ Частично | есть автоматический cron, но restore не проверен по offsite (SMB отсутствует) |
| Performance | ✅ OK | 7/7 контейнеров healthy, backend 14% RAM, latency в норме (browser UI отзывается быстро) |
| Наблюдаемость | ✅ OK | Prometheus метрики, Grafana дашборд, audit log retention 90 дней |
| T1D-UX | ⚠️ Средняя | Есть auto-save, hint 3 уровня, T1D-grade badges. Не проверено в реальном сеансе с Кириллом |

**Итоговая готовность: 65% — проект технически стабилен, но НЕ безопасен для передачи ребёнку как "готовая система" из-за сломанного readiness-gate.**

---

## 2. Состояние репозитория

- **HEAD:** `fc3e657` (`fix(ai-tutor): gate runtime deploy on pilot evidence`)
- **Ветка:** `design-audit-2026-08-20-fixes` (на 285 коммитов впереди `main`)
- **Файлов:** 54 .tsx + ~50 .ts на frontend, 115 .py модулей backend, 163 test_*.py, 12+ миграций
- **Dirty tree:** 10 изменённых файлов, ~28 untracked артефактов (textbook data, audit docs, presentation .pptx)
- **Ветвь dirty:** Не критично, не блокирует — но требует `git status` гигиены

---

## 3. Архитектура и стек

### Backend (FastAPI)

```
apps/backend/app/
├── ai/               # 368K — главный модуль AI (5+ режимов: explain, hint, chat, generate, check)
├── subjects/         # 216K — SubjectOut, fail-closed evidence, mappings, RAG
├── admin/            # 184K — audit log, real-time WS, user mgmt, evidence CLI
├── teacher/          # 176K — Sprint 1 генерация материалов
├── parents/          # 112K — multi-child dashboard, weekly summary
├── progress/         # 104K — SM-2 spaced repetition
├── auth/             # 104K — JWT + httpOnly cookies, OAuth, 2FA
├── diagnostics/      # 92K
├── student/          # 80K — topic_drafts, autopause, secure flow (Pilot Core 2026-07-13)
├── users/, notifications/, scripts/    # по 72K
└── v2/               # 52K — будущие breaking (security-flow, exercises)
```

**Оценка:** Модули хорошо разделены, dependency direction корректный (v2 не импортирует v1).

### Frontend (Next.js 16)

```
apps/frontend/app/
├── subjects/         # каталог + [id] (с TOP-маршрутом)
├── topics/[id]/      # главный student flow
├── student/badges/   # T1D-безопасные баджи
├── parents/          # кабинет родителя, multi-child
├── parent/dashboard/[id]/
├── teacher/          # генерация материалов
├── admin/{realtime,tools,users,invites}/
├── diagnostic/       # CAT адаптивная диагностика
├── cgm/              # Nightscout-интеграция (read-only, не трогаем)
├── topics/[id]/components/  # chat, explain, practice, hints
├── login, register, forgot-password, welcome, offline
└── invite, link-parent, error, global-error
```

**Оценка:** Хорошая App Router структура, маршруты понятны, модульный CSS.

### Инфра (Docker Compose, 7 контейнеров)

| Сервис | Статус | Health |
|---|---|---|
| backend | Up 10h | healthy |
| frontend | Up 21h | healthy |
| db (Postgres 16) | Up 4 weeks | healthy |
| redis | Up 4 weeks | healthy |
| prometheus | Up 8 days | healthy |
| grafana | Up 4 weeks | — |
| proxy (nginx) | Up 12 days | — |

**Оценка:** Production-grade, ресурсы в норме (backend 14% RAM, frontend 1.7%, db 4%). Но docker-compose проект называется `deploy-*` (а не `aitutor-*`) — это тех. долг для atomic rollback.

### Диск

- LXC root: `/dev/loop2 49G 35G 13G (74%)` — в норме, запас есть
- Backups in `/var/backups/ai-tutor` — с 12 июля 2026, ~193 bytes manifest/12 bytes uploads (очень куцые — это лишь метаданные; реальные .sql.gz должны быть отдельно)

---

## 4. AI-инфраструктура

### Провайдеры
- **Основной:** MiniMax-M3 через OpenAI-совместимый API (`https://api.minimax.io/v1`)
- **Embeddings:** Hash-based fallback (MiniMax не имеет /embeddings) + опционально sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`, 384-dim) на локальном — для RAG
- **Fallback:** cache + retry + 3-attempt structured JSON parse (Sprint 8.1)

### Режимы AI (5)

| Режим | Endpoint | Что делает |
|---|---|---|
| Explain | `POST /api/v1/ai/explain` | Развёрнутое объяснение темы + пример + самопроверка |
| Hint | `POST /api/v1/ai/hint` | Подсказка по задаче (3 уровня) |
| Check | `POST /api/v1/ai/check` | Проверка ответа (включая server-side validation) |
| Generate | `POST /api/v1/ai/exercises/generate` | Генерация задания (⚠️ 404 в моём smoke — endpoint может называться иначе) |
| Chat | `WS /ws/ai/chat` + `POST /api/v1/ai/chat` | Диалог с репетитором по теме |

**Проверено live:**
- `POST /api/v1/ai/explain` на `topic_id=121` (Что такое общество, обществознание) → вернул 600+ символов markdown с правильным форматированием, реальным контентом про «признаки общества», нумерованным списком.
- AI budget: `requests_used=2, requests_limit=20000, tokens_used=0, tokens_limit=20000000` — бюджет практически не тронут, ребёнок может учиться без лимита.

**Оценка AI:** Работает, контент осмысленный, формат корректный. Но в режиме `/ai/exercises/generate` у меня вернулся 404 — путь может быть другим или сломан после рефакторинга.

---

## 5. Безопасность и приватность

### Что есть ✅
- **Auth:** JWT HS256 в httpOnly cookies (`ai_tutor_access`, `ai_tutor_refresh`), `Secure` в prod, `SameSite=Lax`. Login + refresh rotation + logout.
- **RBAC:** 4 роли (student / parent / teacher / admin), FastAPI deps (`require_role(...)`), 11+ endpoints защищены.
- **Rate-limit:** Redis-backed (multi-worker ready). AI 30/мин/user; login 10/15мин/IP; register 5/час/IP.
- **AI budget:** 200/день + 200K токенов/день на user (Sprint 9.4).
- **XFF trust:** TRUSTED_PROXIES CIDR, защита от подмены IP.
- **Audit log:** IP capture через ContextVar, 5xx → auto-record (`action=error.5xx`), TTL 90 дней, admin `/audit-log/purge`.
- **Secure exercises:** server-owned projection через `GeneratedExerciseInstance` + `/api/v2/exercises/{generate,answer}` (Pilot Core 2026-07-13). Legacy v1 `/attempts` теперь проверяется через `_server_validate_attempt`.
- **Markdown safety:** `markdown-it-py` на backend + regex sanitizer (`on*`/`style`/`javascript:`). Frontend `SafeMarkdown.tsx`.

### Что отсутствует / известные проблемы ⚠️
- **CSRF:** F2.2 в Sprint 11 audit (вероятно НЕ закрыт). Не подтверждено в этой разведке (нужно читать auth/security.py).
- **PII leak в parent endpoints:** `child.email` утекает в `/api/v1/parents/children` и dashboard — нужно убрать из schemas (5 мин fix).
- **CVE-tail:** pip-audit snapshot показывает 98 уязвимостей в 12 пакетах. Закрыто 7 (python-jose 3.3→3.5, python-dotenv 1.0.1→1.2.2, pip 26.1.2→26.2). Не закрыто 91 (starlette, cryptography, pillow, pypdf, multipart, transformers). Требуется major version upgrade + plan (есть `AI-TUTOR-STARLETTE-1X-MIGRATION-PLAN.md`).
- **NPM:** 4 high severity (nanoid, next@16.2.10, postcss, sharp). Не закрыто, требует отдельного regression.

### T1D-конкретное (для Кирилла) ✅
- Баджи только за конкретные действия, НЕ за streak/missed (catalog tested in `TestBadgesNotStreak`).
- Auto-save темы каждые 5 сек + server sync.
- Voice rate-limit per-user.
- Cat-адаптивная диагностика.

---

## 6. Главный блокирующий риск — fail-closed evidence-store СЛОМАН

### Что наблюдается в проде

`POST /api/v1/subjects` возвращает:

```
id=14  code=hist-world  mvp_status=mvp_ready   pilot_visible=True   promotion_allowed=True   practice_ready=True   rag_ready=True   blocked_reason=blocked_ocr
id=13  code=chem        mvp_status=mvp_ready   pilot_visible=True   promotion_allowed=True   practice_ready=True   rag_ready=True   blocked_reason=blocked_ocr
id=11  code=bio         mvp_status=mvp_ready   pilot_visible=True   promotion_allowed=True   practice_ready=True   rag_ready=True   blocked_reason=blocked_ocr
... всего 16/16 mvp_ready
```

Это прямое нарушение как минимум 3 инвариантов:

1. **Logical contradiction:** `promotion_allowed=True AND blocked_reason=blocked_ocr` — promotion не должно быть разрешено при blocked_reason.
2. **Coverage lie:** UI показывает «ПРАКТИКА 0/10» для hist-world (и 0/17 lit-2, 0/13 rus-2, 0/15 chem), API говорит `practice_ready=True`. Это означает, что `practice_ready` в evidence.json = True, но фактически fallback-bank пуст.
3. **Утерянный protection:** `_DEFAULT_EVIDENCE` в коде содержит только `math`. Значит `evidence.json` на проде перезаписан руками и валидация не сработала.

### Что должно быть

```python
# псевдо-инвариант:
promotion_allowed ⇒ (
  manifest_ready AND
  mapping_ready AND
  import_ready AND
  rag_ready AND
  practice_ready AND
  manual_smoke_ready AND
  blocked_reason IS NULL
)

# ВСЕ нарушения должны быть помечены в evidence.json и
# валидатор должен ОТКЛОНЯТЬ такой файл (а не молча принимать).
```

### Что делать (Sprint H1 — см. 06-sprints.md)

1. Записать evidence-валидатор: при загрузке `evidence.json` проверять все 6 условий + `promotion_allowed ⇒ blocked_reason IS NULL`. Бросать ValueError при нарушении.
2. Переписать `evidence.json` на проде: только math имеет все 6 гейтов true; остальные 15 — `preview`/`internal_mvp`/`blocked_ocr`, `pilot_visible=false`, `promotion_allowed=false`.
3. Добавить regression-тест `test_evidence_invariants.py` который читает `evidence.json` + ассертит все инварианты.
4. Прогнать end-to-end smoke (см. `ai-tutor-readiness-evidence-store` skill): API должен вернуть `mvp_ready=False` для не-math.

---

## 7. Тестирование

### Текущее состояние тестов (по `AI-TUTOR-CURRENT-STATUS.md`)

```
test_sprint*.py:    637 passed, 20 skipped, 328 warnings in 177.07s
8 spec test files:  135 passed, 131 warnings, ~44s
```

### По audit от 2026-08-23

- `tests/test_admin_evidence.py` — 1 passed, 9 errors (отсутствует `_EVIDENCE_PATH` fixture). Требует fix.
- Полный backend suite — timeout примерно на 41% (exit 124), не зелёный.
- `tests/test_progress_diagnostics.py tests/test_rag_integration.py` — 2 failed, 7 passed.
- MVP E2E (Playwright): 1 passed, 1 failed — Explain получает non-OK response.
- Frontend `npm run typecheck` ✅, `npm run build` ✅ (24 routes).
- `git diff --check` ✅.

### Оценка тестов

- **Покрытие:** хорошее для базовых flow (637 sprint-тестов), но student-facing E2E падает.
- **Async warnings:** `RuntimeWarning: coroutine ... was never awaited` в `test_rag_context_failure_does_not_crash` и `test_notification_on_milestone_attempts` — это маскированный bug (тело заканчивается на `pass`).
- **Flake:** `test_sprint32_parent_2fa` исправлен через `asyncio_default_fixture_loop_scope=function`.

---

## 8. UI — отдельный глубокий разбор в `04-ui-audit.md`

Краткая выжимка:

- **Login (`/login`):** Prism-стиль, dark, split-layout с заголовком слева и формой справа. Видна плотная типографика, корректные RU-сообщения. ✅
- **`/subjects`:** каталог 16 предметов, каждый в одинаковой карточке с badge `MVP-ready` сверху и 3 метриками снизу (МАРШРУТ/ИСТОЧНИКИ/ПРАКТИКА). KPI-блок «LIVE SYSTEM» в верхнем правом. ⚠️ Все 16 имеют одинаковый зелёный badge — даже hist-world с 0 практики. Нет визуального различия статусов.
- **`/subjects/3` (math):** 42 темы разложены как timeline с badges base/medium/hard, контрольные метки. ✅ плотно и читаемо.
- **`/subjects/16` (lit-2):** 17 тем, badges, но `МАРШРУТ 17/42` — это явный баг (число 42 взято из math, не из реального route).
- **`/topics/120`:** правильная структура (УРОК / ЧАТ / ПРАКТИКА), кнопка «Начать объяснение», подсказка «что дальше». ✅
- **`/parent/dashboard/1`:** Доступ через student токен даёт 403 «Requires role: ['parent']» — корректная RBAC-проверка, но login родителя не настроен (нет credentials на проде).

---

## 9. Что уже сделано (по спринтам 1-10 + аудит-итерации)

- ✅ Sprint 1 — Роль учителя + генерация материалов (52 теста)
- ✅ Sprint 2 — SM-2 spaced repetition + UX ученика
- ✅ Sprint 3 — Кабинет родителя + weekly summary
- ✅ Sprint 4 — Техдолг (rate-limit, audit retention, XFF)
- ✅ Sprint 5 — Prometheus метрики
- ✅ Sprint 6 — Секреты в cron, backup verify, SSL self-signed
- ✅ Sprint 7 — UX ученика: markdown, voice, auto-save, hints (3 уровня), баджи
- ✅ Sprint 8 — Structured output retry, record_ai везде, RAG embedding cache, CAT адаптив
- ✅ Sprint 9 — Родитель multi-child, real-time WS admin, AI budget, Grafana
- ✅ Sprint 10 — JWT cookies, /api/v2 каркас, backup verify cron, E2E parent
- ✅ Pilot Core 2026-07-13 — secure assessment (GeneratedExerciseInstance), 428/428 теста
- ✅ Sprint 11 F2 — частично (вердикт-таблица, есть 10 фолтов из 6 гипотез)
- ✅ Audit 2026-08-22 — полный аудит + отчёт о фальшивой readiness
- ✅ Audit 2026-08-23 — частичный fix (test_admin_evidence fixture fix, evidence-инварианты)
- ✅ Continuation S1-S8 — 135 passed по 8 spec-файлам (на текущий HEAD)

---

## 10. Что нужно сделать для Кирилла + родителя — high-level

В **2 недели** можно получить MVP, пригодный для ежедневного использования Кириллом и мониторинга родителем. Для этого в `06-sprints.md` детальный план:

1. **Hotfix H1 (3 дня)** — починить fail-closed evidence + API/UI consistency.
2. **Hotfix H2 (3 дня)** — закрыть MVP E2E + 15 P0 Math topics contracts.
3. **UX1 (1 нед)** — объяснение ошибки UI, статус-чипы в каталоге, тема про Кирилла (mobile-first проверка).
4. **Content1 (1 нед)** — доводим math-6 до textbook-grade, добавляем 2-3 простых предмета (география, биология).
5. **Pilot-with-Kirill (1 нед)** — реальная сессия с Кириллом + родителем + feedback-форма.

Подробный план — `05-roadmap.md` и `06-sprints.md`.
