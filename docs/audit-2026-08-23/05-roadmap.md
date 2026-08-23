# AI-Tutor — Roadmap до передачи Кириллу + родителю

**Дата:** 2026-08-23
**Цель:** Из текущего состояния «internal MVP с broken readiness gate» в состояние «готово для ежедневного использования одним ребёнком (Кирилл 7 класс, 13 лет, T1D) и его родителем для еженедельного мониторинга».

**Горизонт:** 8-12 недель (при 1 разработчике параллельно с Игорем) или 4-6 недель (при 2 разработчиках параллельно).

**Главный принцип:** сначала trust baseline (P0 hotfixes), потом UX stabilization, потом контент, потом pilot.

---

## Фаза A. Trust baseline (Sprint H1-H2, 2 недели)

**Цель:** Исправить блокеры, которые не позволяют передать проект Кириллу без риска.

### Sprint H1 (3 рабочих дня) — fail-closed evidence + AI endpoints

**Описание:** Восстановить integrity invariant `promotion_allowed ⇒ all 6 evidence gates true AND blocked_reason IS NULL`. Восстановить работоспособность exercise generation endpoint. Исправить async warnings, маскирующие bug с milestone email.

**Задачи — см. `06-sprints.md` секция «Sprint H1».**

**Критерии выхода (Definition of Done):**
- [ ] `test_evidence_invariants.py` зелёный, проверяет все 6 гейтов + promotion_allowed ⇒ blocked_reason=NULL.
- [ ] `evidence.json` на проде переписан: только `math` имеет все 6 gates true.
- [ ] `POST /api/v1/subjects` на проде возвращает 15/16 `mvp_ready=False` (`math` исключение).
- [ ] `POST /api/v1/ai/exercises/generate` (или правильный путь) возвращает 200 c валидным JSON, не 404.
- [ ] `test_email_per_lesson.py::test_notification_on_milestone_attempts` НЕ имеет unawaited coroutine warning.

**Acceptance test:**
```bash
# End-to-end smoke
curl -sk -H "Authorization: Bearer $TOKEN" https://school.431a.ru/api/v1/subjects | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'16 subjects: mvp_ready for {sum(1 for s in d if s[\"mvp_status\"]==\"mvp_ready\")} (expected 1 — math)')
"

docker exec deploy-backend-1 bash -c "cd /app && python3 -c \"
import sys; sys.path.insert(0, '/app')
from app.subjects.evidence import validate_evidence_payload
validate_evidence_payload({})  # should raise ValueError if empty
\""
```

---

### Sprint H2 (5 рабочих дней) — student flow integrity

**Описание:** Полностью закрыть Playwright MVP E2E на deterministic provider, починить все известные UI-bugs от Playwright (status chips, math route plan bug, chat loading state). Закрыть PII leak (child.email) в parent endpoints.

**Задачи — см. `06-sprints.md` секция «Sprint H2».**

**Критерии выхода:**
- [ ] `tests/test_ai_explain_contract.py` расширен: success / 404 / 401 / 429 / 504 / 422 / RAG-failure.
- [ ] `tests/test_evidence_invariants.py` зелёный.
- [ ] `playwright mvp-student-flow.spec.ts` проходит на deterministic provider.
- [ ] `tests/test_parent_no_email_leak.py` — assert `email` отсутствует в parent responses.
- [ ] `subjects/[id]/page.tsx` — поправлен рендер «МАРШРУТ X/Y» (math-route-plan leak).
- [ ] `topics/[id]/page.tsx` — добавлен loading state «AI печатает...», `content_html` рендерится markdown.

**Acceptance test:**
```bash
# Полный Playwright
cd apps/frontend && npx playwright test mvp-student-flow.spec.ts --reporter=line
# Expected: 1 passed (was 1 failed)
```

---

## Фаза B. UX stabilization (Sprint U1-U2, 2 недели)

**Цель:** Сделать UI настолько стабильным, чтобы Кирилл мог пользоваться им самостоятельно, а родитель — мониторить прогресс без вопросов «как это работает».

### Sprint U1 (5 дней) — UI consistency + mobile

- Status chips на `/subjects` (UI-1): `✅ MVP-ready`, `⏳ В обработке`, `📚 OCR-заблокировано`, `🔍 Preview`. Цветовая дифференциация.
- Исправление `МАРШРУТ X/Y` bug на non-math предметах (UI-3).
- Hamburger menu + tabs на `/topics/[id]` для mobile.
- Chat UI: textarea больше, кнопка «Показать пароль» если будет в auth, focus-visible, submit-on-enter уже есть.

### Sprint U2 (5 дней) — accessibility hardening

- aria-label, aria-live regions, role="log".
- Skip-link к main.
- Focus-visible стили.
- Keyboard navigation smoke (Tab через всю форму).
- Mobile Playwright (нужен CI runner, или macанual через chrome devtools).
- Admin account создаётся через `seed_users.py` с новым паролем.

**Критерии выхода:**
- [ ] Lighthouse accessibility ≥ 90.
- [ ] Playwright mobile (375x812) — `/subjects`, `/subjects/[id]`, `/topics/[id]` без overflow.
- [ ] Admin login работает с новым credentials.

---

## Фаза C. Content depth (Sprint C1-C2, 2 недели)

**Цель:** Довести math-6 до textbook-grade и добавить 1-2 дополнительных предмета, на которых Кирилл может учиться с реальным контентом.

### Sprint C1 (5 дней) — math-6 textbook-grade

- 42 темы math-6: каждая topic должна иметь:
  - 5-10 chunks из учебника (RAG embeddings).
  - Page-range mapping reviewed (не auto-extracted).
  - 3-5 generated exercises разной сложности (base/medium/hard) с server-validated correct_answer.
  - 3 hints (level 1, 2, 3) качественного контента.
- Retrieval quality: recall@5 ≥ 0.6, MRR@5 ≥ 0.5.
- Manual review Кириллом (если в pilot-state).

### Sprint C2 (5 дней) — добавить 2 предмета

**Цель:** выбрать 2 предмета, которые Кирилл будет реально использовать — на основе разговора с ним.
- По умолчанию: **география** (16 тем, text layer PDF) + **биология** (19 тем, text layer).
- Если есть: **алгебра 7 класс** (19 тем).
- Каждый — повторить pipeline как в C1 (textbook-grade → readiness gates → manual review).

**Критерии выхода:**
- [ ] math-6 recall@5 ≥ 0.6, MRR@5 ≥ 0.5.
- [ ] 3 предмета в `evidence.json` с `pilot_visible=true AND promotion_allowed=true`.
- [ ] Каждый новый subject прошёл Playwright e2e (open → explain → practice → correct).

---

## Фаза D. Pilot with Kirill (Sprint P1-P2, 1-2 недели)

**Цель:** Реальная сессия с Кириллом + родителем, без smoke-тестов и агентов — живой пользователь.

### Sprint P1 (5 дней) — Kirill получает доступ

- Kirill login на школьном устройстве + родитель на своём.
- Один урок в день (math-6 topic) под присмотром Игоря.
- Feedback-форма для Кирилла: «было понятно?», «хочу ещё / устал».
- Feedback-форма для родителя: «что показалось странным / тревожным».

### Sprint P2 (5 дней) — итерация по фидбэку

- Закрытие топ-5 feedback-проблем.
- Возможно: улучшение chat-UX, добавление image-input для геометрии, video для биологии.
- Расширение до 2-3 уроков в неделю.
- Kirill самостоятельно открывает сайт и начинает урок.
- Родитель видит weekly email summary.

**Критерии выхода для Фазы D:**
- [ ] Кирилл 7 дней подряд использовал AI-Tutor без значимых жалоб.
- [ ] Родитель прочитал хотя бы 2 weekly summary и подтвердил точность.
- [ ] `manual_smoke_ready=true` для math-6 (реальный живой smoke, не агентский).
- [ ] Никаких P0-блокеров в production logs за последние 7 дней.

---

## Фаза E. Hardening (Sprint X1-X2, 2 недели, ПОСЛЕ первого успешного pilot)

**Цель:** Закрыть тех. долг, который не блокирует первый пилот, но критичен для долгосрочной работы.

### Sprint X1 (5 дней) — security + deps

- CSRF protection (SameSite=Strict для auth cookies ИЛИ double-submit cookie).
- Starlette 1.x migration (отдельный план уже есть).
- Cryptography / Pillow / pypdf / multipart — major version upgrades (по audit).
- NPM `npm audit fix` для nanoid, sharp (без breaking changes).

### Sprint X2 (5 дней) — infra + CI/CD

- Disposable CI runner (GitHub Actions) с Playwright.
- Real offsite backup (SMB / ssh-rsync).
- Release pipeline atomic project name `aitutor-*` (замена `deploy-*`).
- Weekly "AI budget review" alert в Telegram.

---

## Что НЕ в скоупе (явно отложено)

1. **Mobile native app** — нет смысла до тех пор, пока web не стабилен на mobile viewport.
2. **Multi-child parent UI полировка** — текущая версия работает, спринт 9.2 был сделан.
3. **CGM/Nightscout integration** — experimental, не часть обучения. T1D-managed в других системах.
4. **PWA, оффлайн-режим** — уже есть частично через `auto-save`, не критично.
5. **OAuth providers** (Google/Yandex/GitHub) — настроены ENV-var, но `configured: false`. Для Кирилла не нужны.
6. **Voice transcription Whisper** — endpoint существует, не проверен в живую. Не критично.
7. **Sprint 11 F1 (production hardening audit) блоки** — отложено до X-фазы.

---

## Summary timeline

| Фаза | Спринт | Неделя | Цель | Кто делает |
|---|---|---|---|---|
| A | H1 | 1 | Evidence + AI endpoint + async fix | backend |
| A | H2 | 1-2 | Student flow E2E + PII leak + UI-bugs | full-stack |
| B | U1 | 3 | UI consistency + mobile-ready | frontend |
| B | U2 | 4 | A11y + admin + keyboard | frontend |
| C | C1 | 5-6 | math-6 textbook-grade | backend + Kirill |
| C | C2 | 6-7 | +2 предмета | backend + Kirill |
| D | P1 | 8 | Kirill реальный pilot | Kirill + Igor |
| D | P2 | 9 | Итерация по feedback | full + Kirill |
| E | X1 | 10-11 | Security + deps | backend |
| E | X2 | 12 | Infra + CI/CD | infra |

**До 9-недели** — Кирилл + родитель получают стабильно работающий pilot.
**К 12-й неделе** — production-hardened для долгосрочной работы.

---

## Что можно начать делать уже сегодня

Если у Игоря есть 1 час на прямо сейчас:

1. **Починить evidence.json на проде** — manually убрать promotion_allowed=true для не-math предметов (10 мин). Это открывает путь к Kirill-pilot и не блокируется ничем.
2. **Создать admin/parent credentials** через `seed_users.py` (10 мин). Открывает admin-страницы для проверки.
3. **Починить `МАРШРУТ X/Y` bug** для non-math subjects (30 мин). Чисто клиентский фикс.

Эти 3 hotfix'а — на 1 час суммарно, и они убирают 3 главных «зрелищных» проблемы из UI. После этого можно спокойно идти в H1-H2.
