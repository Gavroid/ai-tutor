# AI-Tutor — План каждого спринта

**Дата:** 2026-08-23

Каждый спринт имеет:
- **Длительность** (в рабочих днях при 1 разработчике).
- **Цель** (single sentence).
- **Конкретные чекбоксы** (что делать).
- **Команды** для verify.
- **Критерий выхода** (Definition of Done).

**Глобальные ссылки:**
- Аудит: [`01-audit-full.md`](01-audit-full.md)
- Проблемы: [`03-problems.md`](03-problems.md)
- Roadmap: [`05-roadmap.md`](05-roadmap.md)

---

## Глобальные правила

1. **RED → GREEN → REFACTOR для каждого теста.** Не «все сразу зелёные» — сначала увидеть failing, потом фикс.
2. **Каждое изменение в коде — с тестом.** Без теста — без изменения (кроме `evidence.json`, `manifest.csv`, чисто косметики).
3. **Production deploy только после tar-pipe + rebuild + smoke.** Не «на лету».
4. **Backup перед каждой mutation.** `bash scripts/backup-pre-edit.sh` (есть в `scripts/`).
5. **Pre-edit snapshot для evidence.json:** `python3 tmp/snapshot_evidence.py --label preflight`.
6. **Post-deploy smoke:** `python3 scripts/smoke.py` или curl на /health, /ready, /api/v1/subjects.
7. **Все commits атомарные.** Не «100 файлов в 1 commit».
8. **Каждый PR имеет ссылку на конкретный P0-X / P1-Y / UI-Z проблему.** Без ссылки — отказ.

---

## Фаза A. Trust baseline

---

## Sprint H1 — Fail-closed evidence + AI endpoints + async fix (3 дня)

**Цель:** Восстановить integrity invariant `promotion_allowed ⇒ all 6 gates true AND blocked_reason=NULL`. Восстановить работоспособность exercise endpoint. Закрыть async warning milestone email.

### H1.1 — Evidence validator (P0-1)

- [ ] `apps/backend/app/subjects/evidence.py` — добавить `validate_evidence_payload(data: dict) -> list[str]` возвращающий список нарушений.
- [ ] `validate_evidence_payload` вызывается при `_load_evidence()` — если есть нарушения, логируем и НЕ применяем данные (fallback на default policy).
- [ ] Минимум эти инварианта проверяются:
  - `promotion_allowed ⇒ all 6 gates (manifest/mapping/import/rag/practice/manual_smoke) == True`
  - `promotion_allowed ⇒ blocked_reason is NULL`
  - `pilot_visible ⇒ promotion_allowed`
  - `manual_smoke_ready ⇒ все evidence gates == True` (manual smoke — последний гейт)
- [ ] `apps/backend/tests/test_evidence_invariants.py` — минимум 8 тестов (по 2 на инвариант).

**Verify:**
```bash
cd apps/backend
.venv/bin/pytest -q tests/test_evidence_invariants.py
# Expected: 8 passed
```

### H1.2 — evidence.json на проде (P0-1)

- [ ] Pre-edit snapshot: `python3 tmp/snapshot_evidence.py --label preflight-H1`.
- [ ] Backup `/opt/ai-tutor/data/textbooks/7-class/evidence.json` через tar-pipe.
- [ ] Переписать evidence.json — только math имеет promotion_allowed=true.
- [ ] Залить через tar-pipe + volume reload (volumes уже смоунчены в docker-compose).
- [ ] Backend restart через `docker compose rm -sf backend && docker compose up -d backend` (нужно для очистки module-level кеша, не просто restart).
- [ ] Redis cache invalidate: `docker exec deploy-backend-1 bash -c "cd /app && python3 -c 'import sys; sys.path.insert(0,chr(47)+chr(97)+chr(112)+chr(112)); from app.cache import cache_invalidate; print(cache_invalidate(\"subjects:*\"))'"`.

**Verify:**
```bash
curl -sk -H "Authorization: Bearer $TOKEN" https://school.431a.ru/api/v1/subjects | python3 -c "
import json, sys
d = json.load(sys.stdin)
non_math_mvp = [s for s in d if s['code'] != 'math' and s['mvp_status'] == 'mvp_ready']
print(f'non-math mvp_ready: {len(non_math_mvp)} (expected: 0)')
prom_with_blocked = [s for s in d if s['promotion_allowed'] and s['blocked_reason']]
print(f'promotion_allowed AND blocked_reason: {len(prom_with_blocked)} (expected: 0)')
"
```

### H1.3 — POST /api/v1/ai/exercises/generate route fix (P0-4)

- [ ] Прочитать `apps/backend/app/ai/router.py` — найти реальный путь generate.
- [ ] Если `/ai/exercises/generate` не существует — найти альтернативу (`/api/v2/exercises/generate`, `/exercises/generate`, etc).
- [ ] Обновить OpenAPI schema и frontend `lib/api.ts::generateExercise()`.
- [ ] Тест `tests/test_exercise_routes.py` — каждый known endpoint route exists и возвращает 200/422 (не 404).

**Verify:**
```bash
TOKEN=$(curl -sk -X POST https://192.168.1.86/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"kirill@example.com","password":"Kirill2026!"}' | python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))")
for path in "/api/v1/ai/exercises/generate" "/api/v1/exercises/generate" "/api/v2/exercises/generate" "/api/v1/ai/exercise/generate"; do
  CODE=$(curl -sk -o /dev/null -w "%{http_code}" -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" "https://192.168.1.86${path}" -d '{"topic_id":121}')
  echo "$CODE  $path"
done
# Expected: at least 1 returns 200 or 422 (not 404)
```

### H1.4 — async coroutines fix (P0-5)

- [ ] `tests/test_email_per_lesson.py::test_notification_on_milestone_attempts` — найти `pass` в конце, добавить `await` или `asyncio.run_until_complete`.
- [ ] `tests/test_notifications.py::test_email_dry_run_without_smtp` — убрать `asyncio.run` внутри sync.
- [ ] `grep -rn "datetime.utcnow()" apps/backend/app/ | grep -v test_` — заменить на `datetime.now(timezone.utc)`.
- [ ] `pytest -W error::RuntimeWarning apps/backend/tests/test_email_per_lesson.py` — green, 0 warnings.

**Verify:**
```bash
cd apps/backend
.venv/bin/pytest -W error::RuntimeWarning -q tests/test_email_per_lesson.py tests/test_notifications.py
# Expected: passed, 0 warnings
```

### H1.5 — Admin / parent credentials (P0-3)

- [ ] Создать через `python3 -m app.scripts.seed_users --admin admin@example.com "..."` с `PILOT_SEED_TOKEN` env.
- [ ] Записать credentials в `/root/.ai-tutor-secrets/pilot.txt` (chmod 600).
- [ ] НЕ коммитить в git.

**Verify:**
```bash
TOKEN=$(curl -sk -X POST https://192.168.1.86/api/v1/auth/login -H "Content-Type: application/json" -d "{\"email\":\"admin@example.com\",\"password\":\"$ADMIN_PWD\"}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))")
test -n "$TOKEN" && echo "admin login OK" || echo "FAIL"
```

---

### Definition of Done — Sprint H1

- [ ] `pytest tests/test_evidence_invariants.py` — 8+ passed.
- [ ] `evidence.json` на проде корректный (15/16 non-math mvp_ready=False).
- [ ] `POST /api/v1/...exercises...` returns 200, не 404.
- [ ] 0 unawaited coroutine warnings в targeted tests.
- [ ] Admin/parent login с новым credentials работает.

**Estimate:** 3 рабочих дня (1 dev).

---

## Sprint H2 — Student flow integrity (5 дней)

**Цель:** Полностью Playwright MVP E2E зелёный на deterministic provider. Закрыть PII leak. Починить видимые UI-bugs.

### H2.1 — Expand Explain contract tests (P0-2)

- [ ] `tests/test_ai_explain_contract.py` — добавить кейсы:
  - 200 на valid topic_id с известным контентом
  - 404 на topic_id, не существующий в БД
  - 401 без auth
  - 429 при `_enforce_budget()` raise (mock budget counter)
  - 504 на provider timeout (mock with slow AsyncMock returning `asyncio.TimeoutError`)
  - 422 на malformed AI response (mock with bad JSON)
  - 200 на RAG context failure (graceful — без chunks, но с системным prompt)
- [ ] Использовать deterministic provider через monkeypatch `_get_provider()`.
- [ ] Интегрировать в pytest suite — файл должен быть в default collect, не skip.

**Verify:**
```bash
.venv/bin/pytest -q tests/test_ai_explain_contract.py
# Expected: 17+ passed, 0 errors
```

### H2.2 — Playwright MVP E2E fix (P0-2)

- [ ] Установить причину non-OK response (проверить network tab, response body, request headers).
- [ ] Fix backend (если provider integration) ИЛИ frontend (если pagination / WS).
- [ ] `apps/frontend/e2e/mvp-student-flow.spec.ts` — добавить safety capture в тесты:
  - [ ] `status`, `body`, `error_class`, `request_id` на каждом API call.
  - [ ] Screenshot на failure.
- [ ] Перевести test на deterministic mode (через env `E2E_DETERMINISTIC=1`).

**Verify:**
```bash
cd apps/frontend
E2E_DETERMINISTIC=1 npx playwright test mvp-student-flow.spec.ts --reporter=line
# Expected: 1 passed (was 1 failed)
```

### H2.3 — PII leak fix in parent endpoints (P1-3)

- [ ] `apps/backend/app/parents/schemas.py` — удалить `email: str` из `ChildOut` (или сделать `Optional`).
- [ ] `apps/backend/app/parents/router.py` — убедиться, что `child_overview` и `child_dashboard` не возвращают `student.email`.
- [ ] `apps/backend/tests/test_parent_no_email_leak.py` — assert не содержит `@example` в response.

**Verify:**
```bash
TOKEN=$(...)
curl -sk -H "Authorization: Bearer $TOKEN" https://192.168.1.86/api/v1/parents/children | grep -o "@" | wc -l
# Expected: 0 (no email addresses)
```

### H2.4 — UI bugs (UI-1, UI-3)

- [ ] `apps/frontend/app/subjects/page.tsx` — добавить status chips:
  - mvp_ready → зелёный «✅ MVP-ready»
  - internal_mvp → амбер «⏳ В обработке»
  - preview → нейтральный «🔍 Preview»
  - blocked_ocr → красный «📚 OCR»
- [ ] `apps/frontend/components/StatusChip.tsx` — вынести helper в отдельный component.
- [ ] `apps/frontend/app/subjects/[id]/page.tsx` — поправить «МАРШРУТ X/Y»:
  - Не hardcode 42 из MATH_TOPIC_PLAN.
  - Использовать `subject.topic_count` из API.
- [ ] E2E: после fix Playwright screenshot оба subjects и проверяет chip text.

**Verify:**
```bash
cd apps/frontend
npx playwright test subjects-page.spec.ts --reporter=line --headed
# Manual: проверить что hist-world имеет красный chip, а math — зелёный.
```

### H2.5 — Topics page loading state (UI-2 + UI-7)

- [ ] `apps/frontend/app/topics/[id]/page.tsx` — после клика «Объяснить»:
  - Skeleton или «AI печатает...» indicator.
  - При ошибке — error card (с retry button).
  - При success — markdown рендер через SafeMarkdown.
- [ ] Включить `aria-live="polite"` для region где explanation появляется.
- [ ] Verify WebSocket reconnect: при 401 на WS — fallback на HTTP POST.

**Verify:**
```bash
npm run build && npm run test:e2e -- mvp-student-flow
# Expected: 1+ passed (was 1 failed)
```

---

### Definition of Done — Sprint H2

- [ ] All H2.1 contract tests green.
- [ ] Playwright MVP E2E green на deterministic provider.
- [ ] `test_parent_no_email_leak.py` green.
- [ ] UI status chips работают на /subjects.
- [ ] /topics/[id] loading state виден.
- [ ] Полный backend suite (после H2.5) green ≥ 95%.

**Estimate:** 5 рабочих дней.

---

## Фаза B. UX stabilization

---

## Sprint U1 — UI consistency + mobile (5 дней)

### U1.1 — Status chip dedup (UI-1 продление)

- [ ] `apps/frontend/components/StatusChip.tsx` — единый компонент с цветовой дифференциацией.
- [ ] Использовать на: `/subjects` (card list), `/subjects/[id]` (header), `/admin` (operator view).
- [ ] Per-role filter: student видит только `pilot_visible=True`, teacher/admin видят всё.

### U1.2 — Mobile responsive (UI-5)

- [ ] Hamburger menu в `<Header>` (apps/frontend/components/Header.tsx или layout.tsx).
- [ ] `/topics/[id]` — tabs вместо одновременного показа 3 секций.
- [ ] Chat textarea — больше minHeight, fixed на mobile.
- [ ] Touch targets ≥ 44px (проверить через Lighthouse).

### U1.3 — Cleanup duplicates (UI-6, UI-8)

- [ ] Chat textarea высота на mobile (≥ 80px).
- [ ] Focus-visible стили для keyboard users.
- [ ] Submit-on-enter для всех forms (chat, login).

### U1.4 — Playwright mobile smoke

- [ ] `apps/frontend/e2e/mobile-topics.spec.ts` — viewport 375x812, screenshots.
- [ ] CI integration (если runner есть).

---

### Definition of Done — Sprint U1

- [ ] Lighthouse mobile ≥ 85, a11y ≥ 90.
- [ ] Hamburger menu visible на narrow viewport.
- [ ] Tabs работают на `/topics/[id]` для mobile.
- [ ] 3+ mobile screenshots в `docs/screenshots/`.

**Estimate:** 5 дней.

---

## Sprint U2 — A11y + admin (5 дней)

### U2.1 — A11y wiring (UI-4)

- [ ] `apps/frontend/app/topics/[id]/page.tsx` — добавить `aria-label` на textarea чата.
- [ ] `<div role="log" aria-live="polite">` для chat history.
- [ ] `<div role="alert">` для errors.
- [ ] Skip-link в root layout (`<a href="#main-content" class="sr-only focus:not-sr-only">Пропустить навигацию</a>`).

### U2.2 — Keyboard navigation

- [ ] Tab через login form — focus order: email → password → submit → register → forgot.
- [ ] Tab через `/topics/[id]` — focus order: explain button → practice button → chat input → send.
- [ ] Enter на `/subjects/[id]` — открывает первую тему.

### U2.3 — Admin smoke

- [ ] Залогиниться новым admin credentials.
- [ ] `/admin` — проверить tabs (users, audit-log, tools, realtime).
- [ ] `/admin/realtime` — WS connection test.
- [ ] `/admin/audit-log?action=error.5xx` — есть ли записи за последние 7 дней.

### U2.4 — Operator CLI smoke

- [ ] `python3 tmp/operator_evidence.py list` — все 16 subjects видимы.
- [ ] `python3 tmp/operator_evidence.py show math` — full evidence panel.
- [ ] `python3 tmp/operator_evidence.py validate` — все invariants OK.
- [ ] `python3 tmp/operator_evidence.py promote math` — success.
- [ ] `python3 tmp/operator_evidence.py promote algebra` — REFUSED (all gates not closed).

---

### Definition of Done — Sprint U2

- [ ] Lighthouse a11y ≥ 90 на 4 ключевых страницах.
- [ ] Keyboard navigation smoke Playwright зелёный.
- [ ] Admin login works, `/admin/realtime` shows metrics.
- [ ] Operator CLI promote/refuse работают по инвариантам.

**Estimate:** 5 дней.

---

## Фаза C. Content depth

---

## Sprint C1 — math-6 textbook-grade (5 дней)

### C1.1 — RAG quality boost

- [ ] Проверить chunking — убрать page numbers, headers, повторы.
- [ ] Per-topic: для каждой из 42 тем проверить ≥ 5 chunks с overlap.
- [ ] Настроить bm25 + vector reranking.

### C1.2 — Retrieval probes

- [ ] Расширить `tests/test_retrieval_benchmark.py` — 5 probe на каждую тему.
- [ ] Recall@5 ≥ 0.6 для каждой темы.
- [ ] MRR@5 ≥ 0.5.

### C1.3 — Generated exercises quality

- [ ] Для каждой из 42 тем: 3 generated exercises (base/medium/hard).
- [ ] Server-trusted correct_answer через `_server_validate_attempt`.
- [ ] Idempotent submit.

### C1.4 — Hint levels

- [ ] Verify 3 уровня hints работают корректно.
- [ ] Качество hints уровня 1 (намёк), 2 (подсказка), 3 (разбор).

### C1.5 — Manual review с Кириллом (если Pilot запущен)

- [ ] 5 случайных тем — Кирилл решает, комментирует, Игорь записывает feedback.

---

### Definition of Done — Sprint C1

- [ ] 42 темы math-6 имеют ≥ 5 chunks, 3 exercises, 3 hints.
- [ ] Recall@5 ≥ 0.6, MRR@5 ≥ 0.5.
- [ ] `_server_validate_attempt` не подменяется на client value.

**Estimate:** 5 дней.

---

## Sprint C2 — +2 предмета (5 дней)

### C2.1 — Выбор предметов

- [ ] Разговор с Кириллом: какие предметы ему интересны.
- [ ] Default: **география** (text layer) + **биология** (text layer).
- [ ] Альтернатива: **алгебра 7** (если Кирилл уже прошёл 6 класс).

### C2.2 — Полный pipeline для новых предметов

- [ ] Manifest row в `textbook-manifest.csv`.
- [ ] Mapping JSON для каждой темы (page-range reviewed).
- [ ] Import в БД.
- [ ] RAG chunks + embeddings.
- [ ] Exercises + hints.
- [ ] Evidence.json: новые subjects с `pilot_visible=true`.

### C2.3 — Регрессия

- [ ] Полный Playwright e2e для каждого нового subject.
- [ ] Operator validate.

---

### Definition of Done — Sprint C2

- [ ] 3 subject в evidence.json с pilot_visible + promotion_allowed.
- [ ] Каждый subject — Playwright e2e зелёный.

**Estimate:** 5 дней.

---

## Фаза D. Pilot with Kirill

---

## Sprint P1 — Kirill получает доступ (5 дней)

### P1.1 — Учётки созданы

- [ ] Kirill account (уже есть в seed).
- [ ] Parent account (если не был создан в H1.5).

### P1.2 — Onboarding с Игорем + Кириллом

- [ ] Kirill login на школьном устройстве.
- [ ] Игорь рядом 30 мин, показывает flow.
- [ ] Kirill самостоятельно открывает первый topic.

### P1.3 — Feedback capture

- [ ] Простая форма `/feedback` для Кирилла: понятно / скучно / сложно / хочу ещё.
- [ ] Форма для родителя: точность / тревожные сигналы.

### P1.4 — Weekly review

- [ ] Kirill 1 урок в день.
- [ ] Parent weekly summary email прочитан и прокомментирован.

---

### Definition of Done — Sprint P1

- [ ] Kirill 5 дней подряд заходил.
- [ ] ≥ 3 feedback записи с Кириллом.
- [ ] ≥ 1 feedback с родителя.

**Estimate:** 5 дней (manual + dev 1-2 часа в день).

---

## Sprint P2 — Iteration (5 дней)

### P2.1 — Feedback analysis

- [ ] Собрать feedback в Notion / markdown.
- [ ] Categorize: bug / UX improvement / new feature.

### P2.2 — Top-5 fixes

- [ ] Закрытие топ-5.
- [ ] Регрессия после каждой.

### P2.3 — Расширение до 2 уроков

- [ ] Kirill делает 2 темы в день.
- [ ] Parent видит динамику.

---

### Definition of Done — Sprint P2

- [ ] Kirill 7 дней подряд использовал.
- [ ] Manual smoke полностью пересмотрен.

**Estimate:** 5 дней.

---

## Фаза E. Hardening (после Pilot)

---

## Sprint X1 — Security + deps (5 дней)

- CSRF fix.
- Starlette 1.x migration.
- Cryptography / Pillow / pypdf / multipart major upgrade.
- npm audit fix (не breaking).
- Reverse proxy CSRF tokens.

---

## Sprint X2 — Infra + CI/CD (5 дней)

- Disposable CI runner.
- Real offsite backup.
- Compose project name fix.
- Weekly AI budget review.

---

## Сводка timeline

| Sprint | Дни | Цель | Status |
|---|---|---|---|
| H1 | 3 | Evidence + AI + async + creds | 🔴 NEEDED |
| H2 | 5 | Student flow E2E + PII + UI bugs | 🔴 NEEDED |
| U1 | 5 | UI consistency + mobile | 🟡 Important |
| U2 | 5 | A11y + admin + operator CLI | 🟡 Important |
| C1 | 5 | math-6 textbook-grade | 🟢 Stretch |
| C2 | 5 | +2 предмета | 🟢 Stretch |
| P1 | 5 | Kirill pilot start | 🟢 Pilot |
| P2 | 5 | Iteration | 🟢 Pilot |
| X1 | 5 | Security + deps | 🔵 Hardening |
| X2 | 5 | Infra + CI/CD | 🔵 Hardening |

**Total: 47 dev-days (1 dev) или 24 dev-days (2 dev параллельно).**

С учётом Kirill-pilot + parent onboarding + manual review — **реалистично 8-10 недель до production-ready**.
