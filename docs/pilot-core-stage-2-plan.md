# Pilot Core Stage 2 — план (черновик, требует ревью владельца)

> **Назначение:** следующая итерация после Pilot Core Stage 1 (завершён 2026-07-13,
> `docs/pilot-core-stage-1-report.md`). Все фазы stage 1 выполнены (Phase 1–6),
> 428/428 backend тестов, 7/7 контейнеров запущено, 3/4 E2E прошли.
>
> **Источники:**
> - `docs/pilot-core-stage-1-report.md` — Known limitations и рекомендации
> - `docs/plans/SPRINT-6-PLAN.md` — открытые пункты Sprint 6 (CI/CD, TG, WS, backup)
> - `docs/MASTER-HANDOVER-PROMPT.md` — стек, RBAC, security, prod-контур
> - `CHANGELOG.md` — текущая точка спринтов
>
> **Формат:** рабочий трекер, чекбоксы `[ ]` / `[x]`. Оценки **S/M/L** (S ≤ 1ч, M ≤ 4ч, L ≤ 1 день).
> **Правила:** не ломать 428 backend + 21 Playwright; БД — только миграции `0014+`;
> после каждой фазы — тесты + `CHANGELOG.md` + smoke на проде.

---

## 📊 Baseline на старте Stage 2 (2026-07-13)

| Слой | Состояние |
|---|---|
| Backend тесты | **428/428** ✅ |
| Frontend build | OK (8.5s) |
| Миграции | до `0013_secure_exercises` |
| Production | 7/7 контейнеров запущено (5/7 healthcheck, 2 без — как baseline) |
| `/health`, `/ready`, `/api/v2/health`, `/metrics` | все 200 |
| Backup offsite | **fail-closed** (нет SMB — см. блокер B-1) |
| CI/CD | workflows готовы, **GitHub remote отсутствует** (блокер B-2) |
| TG-алерты | **не настроены** (блокер B-3) |
| WS на multi-worker | **single-worker** (1 uvicorn worker, см. рекомендация R-3) |
| Audit `error.5xx` за 7д | **3 исторические записи** (R-7, ожидаемое обнуление через 7 дней) |

---

## 🧭 Карта направлений Stage 2

| Код | Направление | Блокер? | Источник |
|---|---|---|---|
| **B** | Bug-hunt / known issues из stage 1 | Частично | `pilot-core-stage-1-report.md` § Known |
| **C** | Остаток Sprint 6 (CI/CD, TG, backup verify, WS) | ✅ Владелец | `SPRINT-6-PLAN.md` 6.1/6.2/6.3/6.6 |
| **D** | Pilot hardening: тесты, observability, безопасность | ❌ | Рекомендации R-1…R-7 |
| **E** | Pilot UX: мелкие UX-фиксы, выявленные на сценариях | ❌ | `pilot-scenarios.md` ручной прогон |

> **Принцип:** B + D — внутренние, можем делать сами. C упирается в блокеры владельца
> (GitHub remote, TG-токен, SMB-mount). E — по результатам ручного прогона.

---

## ⚡ MVP-SCOPE (приоритет для быстрого тестирования)

> **Цель:** убрать только то, что **может сломать UX при ручном тестировании**.
> Нагрузка: 1 пользователь на роль, тестирует локально. Self-hosted, LAN-only.
>
> **Всё остальное (B.3/B.6, D-2/D-3/D-4/D-5/D-7, Фаза C, Фаза E) отложено** — см. журнал.

| # | Пункт | Размер | Зачем для теста |
|---|---|---|---|
| 1 | **B.1** `/ready` SQL-leak fix | S | Падение БД не должно показывать ugly error в UI |
| 2 | **B.2** Frontend v2 cutover (legacy recordAttempt) | M | Кирилл не теряет прогресс через legacy endpoint |
| 3 | **B.4** tesseract в Dockerfile | M | Teacher-flow работает с фото (Sprint 1.2) |
| 4 | **B.5** Admin WS 404 cleanup | S | `/admin` грузится без 404 в консоли |
| 5 | **D-1** seed CLI safety (`PILOT_SEED_TOKEN` обязателен) | S | Случайный запуск не ломает тестовых user'ов |
| 6 | **D-6** Security headers (HSTS, X-Frame-Options, X-Content-Type-Options) | S | Бесплатная гигиена, 1 правка nginx.conf |

**Не в scope MVP:**
- B.3 семантический match (Кирилл решает numeric — exact-match достаточно)
- B.6 audit 7d watch (time-only, не код)
- D-2/D-3/D-4/D-5/D-7 (CI/CD-уровень, не нужен для ручного теста)
- Вся Фаза C (CI/CD, TG-алерты, backup offsite, WS multi-worker — всё prod hardening)
- Вся Фаза E (UX-косметика по результатам ручного прогона)

---

# 🟥 ФАЗА B — Bug-hunt / закрытие known issues из Stage 1

**Цель:** устранить известные ограничения, объявленные в stage 1 как «expected residual».
**Выходной gate:** все B-пункты либо закрыты кодом, либо явно перенесены с обоснованием.

## B.1 `/ready` SQL-error leakage (privacy hygiene) — S

- [ ] Прочитать `app/main.py::ready()`, текущее поведение при DB-fail
- [ ] Убрать `repr(exc)` из response body, вернуть `{"status": "not_ready", "reason": "db_unavailable"}`
- [ ] Полный `exc` → только в логи (logging.exception), НЕ в HTTP body
- [ ] Тест: DB-down (через monkeypatch) → `/ready` отдаёт безопасный JSON, НЕ содержит `asyncpg.OperationalError` или host/credentials
- [ ] Smoke на проде: `/ready` = 200 (DB up). Имитировать down — не делаем, чтобы прод не сломать; верифицируем только через unit-тест

## B.2 Frontend v2 cutover (legacy `recordAttempt`) — M

- [ ] Прочитать `apps/frontend/app/student/badges/page.tsx` и `topics/[id]/page.tsx`
- [ ] Найти все вызовы legacy `recordAttempt` / `recordAttemptDiagnostic` (вне v2 flow)
- [ ] Решение: либо (a) мигрировать на v2 `/api/v2/exercises/{id}/answer`, либо (b) явно отметить как legacy/deprecated с TODO-комментарием
- [ ] Тест: убедиться, что v2 secure flow покрывает все use-cases (practice cycle, badges)
- [ ] Если мигрируем — обновить E2E в `apps/frontend/e2e/student.spec.ts`

> **Решение (фиксировано менеджером, default):** **мигрировать** на v2, legacy код удалить.
> Обоснование: v2 уже secure + server-trusted, оставлять parallel-стек = риск расхождения
> и лишняя поверхность для регресса. Если миграция ломает E2E — откатим и явно выделим
> legacy-маркировку как отдельный пункт.

## B.3 Семантический match для v2 exercise answer — L

- [ ] Прочитать `app/v2/exercises/answer.py`, текущая exact-match логика
- [ ] Добавить опциональный `semantic` режим: при не-числовом ответе и `len(user_answer) > 8 слов` → фолбэк через AI-judge (отдельный мини-промпт, не основной)
- [ ] Использовать уже готовый чекер-диспетчер из Sprint 8.2 (`app/practice/checkers.py`)
- [ ] Метрика `ai_judge_requests_total{result=match|miss|error}` в Prometheus
- [ ] Тесты: 3 кейса (числовой exact, keyword, semantic через mock judge), проверка что fallback не уходит в AI при очевидных ответах

> **Зависимость:** Sprint 8.2 уже в плане помечен как завершённый, но чекер-диспетчер нужно верифицировать в `app/practice/`. Если есть — переиспользовать.

## B.4 Production Dockerfile drift — отсутствует tesseract-ocr — M

- [ ] Прочитать `apps/backend/Dockerfile`, проверить наличие `tesseract-ocr*` пакетов
- [ ] Решение: либо (a) добавить `apt-get install tesseract-ocr tesseract-ocr-rus` в Dockerfile (rebuild image), либо (b) явно отключить OCR в teacher-flow с TODO
- [ ] Если (a) — после rebuild проверить, что `pytesseract.image_to_string` работает в контейнере
- [ ] Если (b) — обновить `app/materials/router.py` чтобы возвращал понятную ошибку «OCR недоступен, прикрепите PDF/DOCX»
- [ ] Тесты: unit — `ocr_available()` helper, integration — image upload → если OCR off → 422

> **Решение (фиксировано менеджером, default):** **(a) добавить tesseract в image**.
> Обоснование: OCR — заявленная функциональность teacher-flow (Sprint 1.2).
> Отключение = фича-регресс для владельца. Если rebuild вызовет OOM на проде (маловероятно,
> 4GB headroom) — откатим на (b) и зафиксируем как отдельный пункт для владельца.

## B.5 Admin WS 404 cleanup — S

- [ ] Прочитать `app/admin/realtime.py` (или аналог), понять почему `/admin/ws` отдаёт 404
- [ ] Решение: либо (a) починить endpoint (проверить роутинг, CORS для WS), либо (b) явно удалить код и UI-link (UI уже скрыт в stage 1 Phase 5)
- [ ] Тест: WS upgrade проходит ИЛИ endpoint отсутствует 404 без stacktrace

> **Зависимость:** если в Фазе C делаем WS через Redis pub/sub — закрываем здесь.

## B.6 Audit `error.5xx` 7-day gate — time-only — S

- [ ] Не код, а **процессный пункт**: задокументировать в `docs/deployment.md`, что гейт
      «0 за 7 дней» достижим не ранее `2026-07-20` (через 7 дней после последней записи 2026-07-13 07:26 UTC)
- [ ] Создать cron-скрипт `deploy/monitoring/audit-5xx-watch.sh`, который:
  - читает `/metrics` → `http_requests_total{status="5xx"}` rate за последние 7 дней
  - **алертит в TG** (после Фазы C-2) если rate > 0 (пока только в лог)
  - возвращает non-zero exit если rate > 0 (для CI gate)
- [ ] Тест: ручной запуск с замоканным метрика-эндпоинтом — exit code правильный

---

# 🟧 ФАЗА C — Остаток Sprint 6 (CI/CD, TG, backup, WS)

**Цель:** закрыть единственный реальный блокер продукта (по SPRINT-6-PLAN.md).
**Блокер:** все 4 подфазы требуют участия владельца.

## C-1 CI/CD — активация (требует GitHub remote) — M (после блокера)

**Зависит от владельца:**
- [ ] Владелец создаёт приватный GitHub-репо (например, `Gavroid/ai-tutor-private`)
- [ ] `git remote add origin git@github.com:Gavroid/ai-tutor-private.git && git push -u origin main`
- [ ] Владелец добавляет GitHub secrets: `PRODUCTION_HOST=192.168.1.86`, `PRODUCTION_SSH_KEY=<содержимое ~/.ssh/id_ed25519_cicd>`

**После блокера (код готов, ожидает push):**
- [ ] Workflows `.github/workflows/{tests,deploy,frontend-build}.yml` уже валидны — верифицировать на первом push
- [ ] Тестовый push в feature-ветку → полный pipeline tests → deploy → smoke
- [ ] Документация `docs/CICD.md` обновить: добавить раздел «Первый push и rotation ключей»

## C-2 Telegram-алерты (требует TG bot token) — L

**Зависит от владельца:**
- [ ] Владелец создаёт TG-бота через @BotFather, получает `TELEGRAM_BOT_TOKEN`
- [ ] Владелец присылает `chat_id` (можно через `@userinfobot` или `getUpdates` после `/start` боту)
- [ ] Кладёт оба в `/etc/ai-tutor/.env` (600 root:root)

**После блокера:**
- [ ] Прочитать `deploy/monitoring/{healthcheck,error-rate}.sh`
- [ ] Добавить `deploy/monitoring/notify-telegram.sh` — curl к `api.telegram.org`
- [ ] Алерт «5xx всплеск»: error-rate.sh шлёт в TG если >N/5 мин
- [ ] Алерт «healthcheck fail»: healthcheck.sh шлёт при `code != 200`
- [ ] Алерт «backup stale»: если последний backup > 24ч
- [ ] Алерт «Redis/SMTP/DB down»: `pg_isready`, `redis-cli ping`, SMTP через `swaks`
- [ ] **Rate-limit на TG**: не более 1 алерта/категория/10 мин (защита от flood)
- [ ] Тест-инцидент: `docker compose stop redis` на 1 мин → алерт в TG → старт обратно
- [ ] `docs/SKILL.md` (devops/ai-tutor-deploy) — раздел «Telegram-алерты»

## C-3 WS через Redis pub/sub (требует согласования multi-worker) — L

> **Решение (фиксировано менеджером, default):** **отложить**, оставить `--workers=1`,
> добавить явный `# TODO(multi-worker, Stage 3+)` в `Dockerfile` и `deploy/release/deploy.sh`.
> Обоснование: multi-worker требует согласования по ресурсам, race-condition аудита
> Redis pub/sub, и graceful shutdown WS. Это не bug, это архитектурное решение.
> Текущий 1 worker не блокирует пилот (4GB RAM, low traffic), а Stage 2 фокусируется
> на bug-hunt и hardening.

**Вариант A (multi-worker + pub/sub):**
- [ ] Прочитать `app/ai/websocket*.py`, текущий ConnectionManager
- [ ] Реализовать `app/realtime/redis_bus.py` (publish/subscribe через `redis.asyncio`)
- [ ] Канал `ws:{role}:{user_id}`, long-running task per worker
- [ ] WS endpoints → bus.publish вместо локального manager.send_json
- [ ] Graceful shutdown: при SIGTERM закрывать WS-сессии, отписываться
- [ ] Тесты: 2 worker'а, ученик A на worker 1, ученик B на worker 2 → сообщение A доходит до B
- [ ] Smoke: deploy с `--workers 4`, ping/pong latency < 100ms p95

**Вариант B (1 worker + sticky):**
- [ ] Зафиксировать `--workers=1` в Dockerfile CMD
- [ ] Nginx: `ip_hash` upstream для backend (sticky по client IP)
- [ ] Документировать ограничение в `docs/architecture.md` (1 worker = 1 CPU bound)

**Вариант C (отложить):**
- [ ] Обосновать deferral, оставить 1 worker, добавить `TODO(multi-worker)` в код

## C-4 Backup offsite test-restore (требует SMB-mount) — M (после блокера)

**Зависит от владельца:**
- [ ] Подключить SMB-шару `192.168.1.91` (или иную), смонтировать в `/mnt/ai-tutor-smb`
- [ ] Прописать `BACKUP_OFFSITE_DEST=/mnt/ai-tutor-smb/ai-tutor-backups` в `/etc/ai-tutor/.env`
- [ ] Проверить `mount | grep ai-tutor-smb` → видим шару

**После блокера (скрипт fail-closed уже написан в stage 1 Phase 4):**
- [ ] Прочитать `deploy/backup/ai-tutor-backup-offsite.sh` (fail-closed проверки)
- [ ] Развернуть чистый LXC (или временный docker-контейнер с Postgres 16) → восстановить backup → проверить `pg_dump --schema-only` + count таблиц
- [ ] Замерить RTO (restore time objective) → задокументировать
- [ ] Добавить в TG-алерты (после C-2): «offsite backup fail»
- [ ] Тест-регламент: еженедельно (понедельник 04:00 — уже есть cron `ai-tutor-backup-verify`),
      реальный test-restore → лог + запись в `docs/deployment.md`

---

# 🟨 ФАЗА D — Pilot hardening (тесты, observability, безопасность)

**Цель:** сделать пилот устойчивым к типичным проблемам, которые мы увидим при росте активности.
**Выходной gate:** +N тестов, улучшенная observability, явные security-инварианты.

## D-1 Production seed-users CLI → сделать безопасным — M

- [ ] Прочитать `app/scripts/seed_users.py`, текущая логика
- [ ] Добавить: `--require-pilot-token` флаг → CLI refuse без `PILOT_SEED_TOKEN` в env
- [ ] Audit log: каждый вызов seed_users → `audit_logs(action="user.seed", ...)`
- [ ] Тест: без токена → exit 1, с токеном → пользователь создан + audit-запись
- [ ] Документация: `docs/security.md` — раздел «Pilot seed CLI»

## D-2 Rate-limit на дорогие endpoint (audit) — S

- [ ] Прочитать `app/common/rate_limit.py` (если есть) и список endpoint'ов
- [ ] Аудит: какие дорогие endpoint **без** rate-limit?
  - `/api/v1/ai/explain` (есть ли?)
  - `/api/v1/teacher/materials/generate` (Sprint 1.2 — есть ли?)
  - `/api/v1/rag/search`
  - `/api/v1/voice/transcribe` (есть, 20/мин — Sprint 7.2)
- [ ] Добавить недостающие через `app.common.rate_limit`
- [ ] Тест: 11-й запрос за минуту → 429

## D-3 Frontend production guards — S

- [ ] Прочитать `apps/frontend/lib/api.ts`, `next.config.mjs`
- [ ] Проверить, что production build **не** содержит `console.log` с PII
- [ ] Проверить, что dev-only tools (`/admin/realtime` старый link, PDF download старый) — действительно скрыты
- [ ] Проверить, что `NEXT_PUBLIC_*` env'ы не утекают секреты (только публичные)
- [ ] Тест: `next build` → grep `process.env.SECRET_*` → 0 результатов

## D-4 Crash-only smoke для прод-контура — M

- [ ] Прочитать `deploy/release/smoke.sh` (есть, 7 проверок из stage 1 Phase 3)
- [ ] Расширить smoke на:
  - `/api/v1/admin/audit-log` (admin-only, не 500)
  - `/api/v1/parents/children` (parent-only, multi-child из Sprint 9.2)
  - `/api/v1/student/badges` (нет 5xx)
- [ ] Добавить `--strict` флаг: exit 1 если хотя бы одна проверка вернула 5xx (а не только если health=down)
- [ ] Тест: замокать healthcheck-404 → smoke.sh --strict → exit 1

## D-5 Backup-verify автоматизация (еженедельно) — M

> Сейчас есть `deploy/cron/audit_cleanup.py` (ежедневно) и `backup-verify` cron (еженедельно).
> Нужно проверить, что test-restore реально работает.

- [ ] Прочитать `deploy/backup/test-restore.sh`
- [ ] Запустить вручную на staging-like окружении → измерить RTO, RPO
- [ ] Задокументировать RTO/RPO в `docs/deployment.md`
- [ ] Добавить TG-алерт (после C-2) если verify fail

## D-6 Security headers (Nginx) — S

- [ ] Прочитать `deploy/nginx/nginx.conf`
- [ ] Добавить `Strict-Transport-Security: max-age=31536000` (LAN-only, но полезно)
- [ ] Добавить `X-Content-Type-Options: nosniff`
- [ ] Добавить `X-Frame-Options: DENY`
- [ ] Добавить `Referrer-Policy: strict-origin-when-cross-origin`
- [ ] Не добавлять CSP — сломает Next.js devtools, оставить TODO
- [ ] Smoke: `curl -I https://192.168.1.86/ | grep -i strict-transport`

## D-7 Prometheus labels: PII-leak аудит — S

- [ ] Прочитать `app/observability.py` (Sprint 5.1)
- [ ] Проверить, что labels метрик (`http_requests_total`, `ai_tokens_total`) **не содержат** user_id, email, topic_name
- [ ] Если содержат — убрать, агрегировать
- [ ] Тест: `prometheus_client.generate_latest()` → grep user_id → 0

---

# 🟩 ФАЗА E — Pilot UX: мелкие фиксы по сценариям

**Цель:** закрыть косметические / usability проблемы, выявленные в `pilot-scenarios.md` при ручном прогоне.
**Выходной gate:** все 4 роли проходят ручной прогон за ≤ 60 мин без замечаний.

## E-1 Список «открытых замечаний» — заполняется после ручного прогона

- [ ] Владелец запускает `docs/pilot-scenarios.md` (4 сценария, ≤ 60 мин)
- [ ] Каждое замечание → строка в этом разделе с пометкой P0/P1/P2

> **Ожидаемые кандидаты** (можно уточнить после прогона):
> - Microphone UX (Sprint 7.2 кнопка уже есть, но T1D-сценарий записи на паузе не тестировался)
> - Teacher: чужой материал по URL — текст 403 может быть неинформативным
> - Parent: invite-code виден только до refresh (фича) — но UX-копи можно улучшить
> - Admin: audit log фильтр по action — UX фильтра

---

# 📋 Definition of Done (Stage 2)

| Категория | Критерий | Как проверить |
|---|---|---|
| Тесты | 428+N зелёных (N = новые тесты B/D/E) | `pytest tests/ -q` |
| E2E | 21+M зелёных | `npx playwright test` |
| Production smoke | `deploy/release/smoke.sh --strict` → 0 | SSH на 192.168.1.86 |
| Блокеры владельца | C-1..C-4 либо закрыты, либо явно перенесены | CHANGELOG + handover |
| `/ready` privacy | Не утекает SQL-error в HTTP body | unit test |
| Audit `error.5xx` | 0 за 7 дней (time-only) | `deploy/monitoring/audit-5xx-watch.sh` |
| Frontend v2 cutover | Либо мигрировано, либо legacy маркировано | grep TODO в коде |
| Docker image | tesseract либо on, либо off с TODO | `docker exec deploy-backend-1 which tesseract` |
| Backup RTO/RPO | Задокументированы | `docs/deployment.md` |
| TG-алерты | Тест-инцидент дошёл | ручной прогон |

---

# 🔗 Связанные документы

- [`pilot-core-stage-1-report.md`](pilot-core-stage-1-report.md) — итог Stage 1
- [`MASTER-HANDOVER-PROMPT.md`](MASTER-HANDOVER-PROMPT.md) — полный handover
- [`plans/SPRINT-6-PLAN.md`](plans/SPRINT-6-PLAN.md) — Sprint 6+ план
- [`pilot-scenarios.md`](pilot-scenarios.md) — ручные сценарии
- [`deployment.md`](deployment.md) — деплой + RTO/RPO
- [`security.md`](security.md) — политика секретов и rate-limit

---

# 📝 Журнал прогресса

> Заполняется по мере выполнения.

### 2026-07-13 — Scope сужен до MVP (ручное тестирование)
- Владелец уточнил: нагрузка 1 user/роль, цель — быстро получить рабочий проект для тестирования
- **В scope:** только 6 пунктов (B.1, B.2, B.4, B.5, D-1, D-6)
- **Из scope:** B.3 (semantic match), B.6 (audit watch), D-2/D-3/D-4/D-5/D-7 (prod hardening), вся Фаза C (CI/CD, TG, SMB, WS multi-worker), вся Фаза E
- Обоснование: всё отложенное — prod-hardening/CI/мониторинг, не нужно для ручного теста 1 user/роль
- Делегирование: 1 sub-agent на все 6 пунктов разом (одна verify-сессия вместо двух)

### 2026-07-13 — Scope зафиксирован (решения менеджера, default'ы применены)
- **B.2** legacy recordAttempt → мигрировать на v2 `/api/v2/exercises/{id}/answer`, legacy удалить
- **B.4** tesseract → добавить в Dockerfile + rebuild image (вариант a)
- **C-3** WS multi-worker → отложить, оставить 1 worker с TODO в коде
- **Фаза C** целиком отложена до владельческих блокеров (TG-токен, GitHub remote, SMB-mount)
- **Фаза E** отложена до ручного прогона `pilot-scenarios.md`
- **Стартуем:** Фаза B (6 пунктов, ~1-2 дня) + Фаза D (7 пунктов, ~1 день)
- Делегирование: 2 sub-agent'а параллельно — один на B, другой на D. Verify после.

### Следующий: запуск B+D через delegate_task

### 2026-07-13 — Черновик создан
- Определены 4 направления: B (bug-hunt), C (Sprint 6 остаток), D (hardening), E (UX)
- Каждое направление разбито на конкретные пункты с оценкой S/M/L
- C-пункты явно помечены как «требует владельца» с перечислением зависимостей
- Definition of Done составлен
- План ожидает ревью владельца: ревью scope, расстановка приоритетов, выбор вариантов (B.2/B.4/C-3)