# Sprint 3.9 — обновления после walk-through (2026-09-02)

Дополнение к PLAN-SIMPLE-2026-09-01.md. Закрытые задачи после релиза.

---

## Sprint 3.9.5 (Kirill feedback: rate-limits)

**Запрос:** 60 AI-запросов/час → 429 + нормальное объяснение. 250 req/day + 500k tokens/day на user. Login ×2.

**Что сделано:**
- `apps/backend/app/config.py`: `rate_limit_login_per_15min: int = 20` (было 10).
- `apps/backend/app/ai/budget.py`: `HOURLY_REQUESTS_LIMIT = 60`, `DAILY_REQUESTS_LIMIT = 250`, `DAILY_TOKENS_LIMIT = 500000`.
- `apps/backend/app/ai/router.py`: `_enforce_budget` теперь строит человеческое сообщение со сбросом:
  - Hourly: «Кирилл, ты сделал уже X запросов за этот час (лимит 60). Лимит сбросится через N мин, когда закончится текущий час.»
  - Daily req: «Кирилл, на сегодня лимит запросов исчерпан (X/250). Сбросится через N ч, в 03:00 по Москве.»
  - Daily tok: «Кирилл, на сегодня лимит слов исчерпан (Xk из 500k). Сбросится через N ч, в 03:00 по Москве.»
- `apps/backend/app/main.py`: middleware rate-limit `/ai/*` даёт «Подожди N сек, когда начнётся новая минута».
- `apps/frontend/lib/api.ts`: `ApiError.message` теперь берёт `body.detail` (FastAPI convention) — JSON больше не показывается пользователю.
- `apps/frontend/app/topics/[id]/page.tsx`: убрано жёстко-зашитое «Подожди минуту» — пробрасывается реальный message.
- `deploy/docker-compose.yml`: `RATE_LIMIT_LOGIN` дефолт 20 (было 10).

**Bonus fix:** `BudgetExceeded kind` — был баг: `kind="requests"` вместо `kind="daily_requests"` → пользователь видел «AI budget exceeded (requests)» вместо нормального сообщения. Починено в `1c04e23`.

**Commits:** `b15ca31`, `1c04e23`. На проде: `20260902T111519Z-1c04e23`.

---

## Sprint 3.9.6 (multi-provider AI + per-subject routing)

**Запрос:** возможность добавлять несколько AI-провайдеров в админке и назначать разные модели разным предметам, с запасным вариантом.

**Что сделано:**

### Backend
- `apps/backend/app/admin/ai_providers.py` — 3 модели SQLAlchemy:
  - `AIProvider` (name, kind, base_url, encrypted_api_key, is_active, note)
  - `AIModelCatalog` (provider_id, model_name, is_active, fetched_at) — модели выбранные админом
  - `SubjectAIModel` (subject_id, model_id, role: primary|fallback) — назначение модели на предмет
- `apps/backend/app/admin/ai_providers_schemas.py` — Pydantic-схемы (безопасность: api_key_encrypted НЕ возвращается, только last4).
- `apps/backend/app/admin/ai_providers_service.py` — сервис:
  - Fernet encryption (ключ из APP_SECRET_KEY через SHA256)
  - `fetch_models_from_provider` — дёргает GET {base_url}/models, парсит OpenAI-формат
  - `test_provider_connection` — ping /models endpoint
  - `resolve_provider_for_subject(role)` — резолвит провайдера для предмета (primary или fallback)
- `apps/backend/app/admin/ai_providers_router.py` — admin-only API:
  - CRUD провайдеров
  - `/test`, `/fetch`, `/models`
  - `/api/v1/admin/subjects/{id}/ai-assignment` GET / PUT (primary / fallback)
- `apps/backend/app/ai/service.py`:
  - `AIService._complete_with_fallback(db, subject_id, req)` — primary → fallback → env default.
  - `explain_topic` использует этот метод вместо прямого `self.provider.complete`.
- `apps/backend/alembic/versions/0023_ai_providers.py` — миграция (3 таблицы).

### Frontend
- `apps/frontend/app/admin/ai-providers/page.tsx` — страница:
  1. Список провайдеров (добавление, удаление, тест, fetch моделей)
  2. Развёрнутые модели провайдера (чекбоксы is_active)
  3. Таблица предметов с dropdown'ами primary / fallback
- `apps/frontend/lib/api.ts` — добавлены generic `get/post/patch/put/delete` для ad-hoc endpoints.
- `apps/frontend/app/admin/page.tsx` — ссылка «AI-провайдеры →» в header админки.

### Безопасность
- API-ключи хранятся зашифрованными (Fernet). В API ответы идёт только `api_key_last4` (`•••cdef`).
- Все `/admin/ai-*` endpoints защищены `require_admin()`.

### Тесты
- `apps/backend/tests/test_sprint396_ai_providers.py` — 23 passed:
  CRUD, encryption, fetch моделей (mock httpx), test connection (ok/fail), toggle model,
  subject assignment, resolve_provider_for_subject (включая fallback роль),
  _complete_with_fallback flow (primary ok / primary fail + fallback ok / no subject → default),
  non-admin 403, edge cases (404).
- Существующие тесты (test_ai, test_admin, test_s3_understand_check) — 35 passed.
- Всего backend pytest: **58 passed**.

### Verify на проде
- `https://192.168.1.86/admin/ai-providers` — страница работает, видна.
- Создан провайдер OpenRouter через curl.
- Fetch моделей вернул **421 модель** с реального OpenRouter (id=1).
- Test connection: `ok=true, latency=815ms, 421 моделей`.
- Включена модель `openai/gpt-5.6-luna` (id=65).
- Назначена primary на физику (subject_id=6).
- `/api/v1/ai/explain?topic_id=66` (физика) — HTTP 200, 1312 chars реального объяснения.
- Лог подтверждает fallback-логику: «Subject primary provider failed (OpenRouter основной/openai/gpt-5.6-luna): HermesProviderError('AI request failed after 3 attempts') — trying fallback».

**Commit:** `98de540`. На проде: `20260902T120020Z-98de540`. Миграция 0023 применена.

### Откат если что
- Код: `cd /root/workspace && tar -xzf backups/ai-tutor-pre-sprint-396-*.tar.gz`.
- БД: `gunzip -c backups/db-pre-sprint-396-*.sql.gz | docker compose exec -T db psql -U tutor tutor`.
- Backend rollback: `alembic downgrade -1` → 0022_feedback_reports (удаляет 3 таблицы).

---

## Следующие шаги

- **Sprint 3.9.7:** per-subject routing для остальных AI-endpoint'ов (generate, check, hint).
- **Sprint 3.9.8:** просмотр usage-статистики по каждой модели (сколько раз использовалась, сколько токенов).
- **Sprint 3.9.9:** шифрование ключей с per-provider salt (доп. защита).

---

## Sprint 3.9.6.1 (polish /admin/ai-providers)

**Запрос:** «Поравь дизайн, как остальных страниц админки, этим невозможно пользоваться. Так же добавь поле поиска при выборе моделей от провайдера.»

**Проблемы:**
- Страница использовала свои CSS-классы (`var(--bg)`, `var(--fg)`, `var(--border)`) и не вписывалась в prism-shell дизайн остальной админки.
- 421 модель OpenRouter — слишком длинный список чтобы скролтить без фильтра.

**Изменения:**
- `Header` + `prism-shell admin-console` + `prism-frame` + `prism-layer` обёртка (как у остальных админ-страниц).
- Все карточки: `admin-panel-surface` + `prism-card` + `prism-card.pad`.
- Кнопки: `prism-action` / `prism-action primary` (вместо `button[bg-accent]`).
- Inputs/selects: `prism-input`.
- **Hero header:** `prism-kicker` + заголовок `tracking-[-0.04em]` + описание + 2 кнопки.
- **Поиск моделей:** `type="search"` input с фильтрацией по `model_name` / `display_name`, чекбокс «Только активные», счётчик «Показано: X / Y», empty-state «Ничего не найдено».
- **PRIMARY / FALLBACK dropdown'ы:** uppercase tracking-wider labels, `prism-input`.

**Commit:** `7168d69`. На проде: `20260902T122122Z-7168d69`.

---

## Sprint 3.9.6.2 (scroll fix)

**Запрос:** «стало лучше но все три блока непомещаются и не скролятся».

**Проблема:** я использовал `prism-shell > prism-frame > prism-layer` без обёртки `admin-content-zone`. CSS `.prism-frame { overflow:hidden }` и `.prism-shell { overflow-x:hidden }` резали контент — страница не скроллилась.

**Fix:** обернул содержимое в `<section className="admin-content-zone mt-4 space-y-6">`. Этот класс добавляет `flex: 1 1 auto; min-height: 0; overflow: auto; scrollbar-gutter: stable` — даёт scroll внутри фиксированного `prism-frame`.

**Verify:**
- `scrollHeight: 738px > clientHeight: 620px` → `canScroll: true`.
- После `zone.scrollTop = scrollHeight` → `currentScroll: 118` ✓.

**Commit:** `cb8f968`. На проде: `20260902T123013Z-cb8f968`.
