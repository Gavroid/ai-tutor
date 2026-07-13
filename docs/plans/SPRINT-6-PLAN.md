# SPRINT 6+ — План развития (по результатам внешнего AI-аудита)

> **Источник:** внешний глубокий AI-аудит (`pasted-text-2026-07-13_00-44-08-471.md`,
> дата 2026-07-13). Итог 5 спринтов: 247/247 backend + 12/12 E2E ✅, миграции до 0009,
> прод 5/5 контейнеров healthy (см. `SKILL.md` devops/ai-tutor-deploy).
>
> **Назначение файла:** рабочий трекер задач с чекбоксами — отмечать прогресс
> `[ ]` / `[x]` по мере работы. Заменяет/расширяет раздел «Sprint 6+» из
> `docs/ROADMAP.md`. Формат: блок → задача → подзадачи. Оценки S/M/L.
>
> **Правила ведения (из AI-DEEP-AUDIT-PROMPT.md):**
> 1. Перед задачей — прочитать релевантные файлы.
> 2. Не ломать 247 backend + 12 E2E (на момент старта); новые тесты на новый код.
> 3. БД — только новые миграции 0010+ (`batch_alter_table`).
> 4. После спринта: зелёные тесты + обновлённые `docs/` + `CHANGELOG.md` + новые pitfalls в SKILL.md + smoke на проде.
> 5. Уточняющие вопросы (≤5) — до тяжёлых решений.
>
> **Скоуп:** ТОЛЬКО 7 класс. Все новые поля параметризуются по `grade` (не хардкодить «7»).

---

## 📊 Baseline на старте Sprint 6 (2026-07-13)

| Слой             | Состояние                                                                |
|------------------|--------------------------------------------------------------------------|
| Production       | 192.168.1.86 (Proxmox LXC, 4 CPU / 4 GB RAM / swap=0) — 5/5 healthy       |
| Backend тесты    | **247/247** ✅                                                            |
| E2E (Playwright) | **15/15** ✅                                                              |
| Smoke (prod)     | 8/8 (OAuth, RAG, Voice)                                                   |
| Миграции         | до 0009                                                                  |
| Endpoints        | 70 REST + 3 WS                                                           |
| Спринты          | 1 ✅ Роль Учителя · 2 ✅ UX/SM-2 · 3 ✅ Кабинет Родителя · 4 ✅ Тех.долг · 5 ✅ Prometheus |
| Cron             | 5 active (backup 03:00, 3 монитора /5 мин, audit cleanup 03:00)          |
| Redis            | контейнер 5, multi-worker ready                                          |
| Deploy           | ручной rsync (~10 мин), без CI/CD                                        |
| AI               | MiniMax-M3 через OpenAI-compatible (без /embeddings — hash fallback для RAG) |
| TTS              | не делали (отложено)                                                     |

---

## 🗺️ Карта Sprint 6+

| #   | Спринт                                     | Цель                                              | Приоритет | Блокер? |
|-----|--------------------------------------------|---------------------------------------------------|-----------|---------|
| 6   | Надёжность прод-контура (закрыть P0)       | CI/CD, алерты, WS через Redis pub/sub, секреты    | **P0**    | ✅ ДА    |
| 7   | UX ученика (главный пользователь)          | Markdown, тип-эффект, микрофон, автосохранение, практика, мягкая геймификация | P0 | ❌ |
| 8   | Качество AI и контента (ядро ценности)     | structured output, эталонные решения, RAG, метрики AI | P0 | ❌ |
| 9   | Родитель + Админ (наблюдаемость и связь)   | weekly summary email/TG, multi-child, real-time /admin, бюджет AI, Grafana | P1 | ❌ |
| 10  | Техдолг и масштабируемость                 | JWT в httpOnly cookie, Zustand, /api/v2 каркас, backup verify, E2E покрытие | P2 | ❌ |

> **Принцип:** Sprint 6 — единственный реальный блокер (без CI/CD и алертов любой новый
> код рискует уронить прод молча). После него спринты независимы.

---

# 🟥 СПРИНТ 6 — Надёжность прод-контура (блокер)

**Цель:** прод не падает молча, деплой автоматический, ключевые P0 из аудита закрыты.
**Выходной gate:** 247/247 backend + 15/15 E2E + ручной smoke на проде + алерт в
Telegram реально срабатывает на тест-инциденте.

---

## 6.1 CI/CD — убрать ручной rsync (P0-1) — **ЧАСТИЧНО** (требуется владелец)

- [x] **6.1.1** Прочитать `.github/workflows/{tests,deploy,frontend-build}.yml` (все 3 файла есть)
- [x] **6.1.2** Git-репозиторий инициализирован (`git init -b main`), 2 коммита в main
- [x] **6.1.3** Создан **отдельный** SSH-ключ `~/.ssh/id_ed25519_cicd` (НЕ основной). Публичный добавлен в прод `authorized_keys`
- [x] **6.1.6** `deploy.yml` обновлён: rsync fallback + `docker compose config --quiet` перед rebuild
- [ ] **6.1.2-Б** **ТРЕБУЕТСЯ ОТ ВЛАДЕЛЬЦА:** создать приватный GitHub-репо → `git remote add origin ...` → `git push -u origin main` → настроить secrets `PRODUCTION_HOST=192.168.1.86`, `PRODUCTION_SSH_KEY=<приватный ключ>` (СОДЕРЖИМОЕ `~/.ssh/id_ed25519_cicd`, а не `id_ed25519_kirill_ai`)
- [ ] **6.1.4-6.1.5** Workflows `tests.yml` + `frontend-build.yml` существуют, но реальная проверка — после push
- [ ] **6.1.7-6.1.8** Тестовый push + откат — после создания remote
- [x] **6.1.9** Зафиксировано в `CHANGELOG.md` (Sprint 6)

## 6.2 Алерты в Telegram — прод не падает молча (P0-2)

- [ ] **6.2.1** Прочитать `deploy/monitoring/{healthcheck,error-rate}.sh` (текущие bash-мониторы)
- [ ] **6.2.2** Добавить `notify-telegram.sh` (или python) helper: `curl -s "https://api.telegram.org/bot${TOKEN}/sendMessage" -d chat_id=$CHAT_ID -d text=$MSG`
- [ ] **6.2.3** Алерт «5xx всплеск»: `error-rate.sh` отправляет в TG если >N ошибок за 5 мин (порог — текущая baseline / 2)
- [ ] **6.2.4** Алерт «healthcheck fail»: `healthcheck.sh` шлёт при `code != 200` или `uptime.json` отсутствует
- [ ] **6.2.5** Алерт «backup stale»: если последний backup >24 ч (читать timestamp из `/var/backups/ai-tutor/latest`)
- [ ] **6.2.6** Алерт «Redis/SMTP/DB недоступны»: проверка `docker compose exec redis redis-cli ping`, SMTP через `swaks` (или netcat), DB через `pg_isready`
- [ ] **6.2.7** Rate-limit на TG-уведомления: не более 1 алерта/категория/10 мин (защита от flood при панике)
- [ ] **6.2.8** Тест-инцидент: остановить `redis` на 1 мин → убедиться, что пришёл алерт → запустить обратно
- [ ] **6.2.9** Добавить в SKILL.md раздел «Telegram-алерты» с примерами триггеров

## 6.3 WS на multi-worker через Redis pub/sub (P0-3)

- [ ] **6.3.1** Прочитать `app/ai/websocket*.py`, `app/main.py` (broadcast-логика), `deploy/docker-compose.yml` (gunicorn/uvicorn workers)
- [ ] **6.3.2** Проверить текущий broadcast-механизм; задокументировать, почему ломается на workers>1 (каждый worker держит свой ConnectionManager)
- [ ] **6.3.3** Реализовать `app/realtime/redis_bus.py`: publish в канал `ws:{role}:{user_id}`, subscribe — long-running task per worker
- [ ] **6.3.4** Интегрировать в WS endpoints (`/api/v1/ai/chat/ws`, `/api/v1/admin/ws`, и т.д.): вместо локального manager.send_json → bus.publish + worker.listen
- [ ] **6.3.5** Тесты: 2 worker'а → ученик A на worker 1, ученик B на worker 2 → сообщение от A доходит до B (или админу) через Redis
- [ ] **6.3.6** Graceful shutdown: при SIGTERM worker закрывает WS-сессии, отписывается от Redis pub/sub
- [ ] **6.3.7** Альтернатива (если внедрение pub/sub затягивается): временно зафиксировать `--workers=1` + sticky-сессии nginx; задокументировать выбор
- [ ] **6.3.8** Миграция: 0010 (если нужна новая таблица `ws_sessions` для отслеживания)
- [ ] **6.3.9** Обновить `docs/architecture.md` (диаграмма pub/sub), новые тесты → backend

## 6.4 Секреты вне cron-cmdline (P0-4)

- [x] **6.4.1** Прочитать `/etc/cron.d/ai-tutor-audit-cleanup`, текущий способ передачи `DATABASE_URL`
- [x] **6.4.2** Создать `/etc/ai-tutor/.env` с правами 600, owner=root; положить туда `DATABASE_URL` (и другие секреты cron-job'ов)
- [x] **6.4.3** Поправить cron-строку: вместо inline `-c 'DATABASE_URL=...'` → `set -a; source /etc/ai-tutor/.env; set +a; docker exec ... python3 /app/audit_cleanup.py`
- [x] **6.4.4** Проверить права: `stat /etc/ai-tutor/.env` → `-rw------- root root`
- [x] **6.4.5** Тест: ручной запуск cron-команды → работает; `grep -r "DATABASE_URL.*postgresql" /etc/cron*` → пусто
- [x] **6.4.6** Зафиксировать в `docs/security.md` политику секретов в cron

## 6.5 Let's Encrypt или обоснование self-signed (P0-5)

- [x] **6.5.1** LAN-only (Kirill-AI.lan), нет публичного IP/DNS → решено оставить self-signed
- [x] **6.5.2-B** Документировано в `deploy/ssl/LETS-ENCRYPT.md`: threat model + условия перехода на LE
- [x] **6.5.3** Smoke: `curl -sk https://192.168.1.86/health` → 200 OK (см. baseline Sprint 5)

## 6.6 Backup offsite — реальный test-restore (P0-6)

- [ ] **6.6.1** Прочитать `deploy/backup/{backup.sh,ai-tutor-backup-offsite.sh,test-restore.sh}`
- [ ] **6.6.2** Проверить последний успешный offsite-backup (`ls -la /var/backups/ai-tutor-offsite/`), дату, размер
- [ ] **6.6.3** Развернуть чистый LXC (или временный docker-контейнер с Postgres 16) → восстановить последний backup → проверить целостность (`pg_dump --schema-only`, count таблиц, sample queries)
- [ ] **6.6.4** Замерить RTO (restore time objective) — документировать в `docs/deployment.md`
- [ ] **6.6.5** Довести `ai-tutor-backup-offsite.sh` до автоматической проверки (скрипт возвращает non-zero если transfer fail или checksum mismatch)
- [ ] **6.6.6** Добавить в TG-алерты: «offsite backup fail» (Sprint 6.2)
- [ ] **6.6.7** Тест-регламент: каждый квартал — реальный test-restore на чистом окружении, запись в `docs/deployment.md`

## 6.7 Документация Sprint 6

- [ ] **6.7.1** Обновить `docs/deployment.md` — CI/CD flow + Telegram-алерты + backup verify
- [ ] **6.7.2** Обновить `docs/security.md` — секреты в cron, self-signed/LE policy
- [ ] **6.7.3** Обновить `docs/architecture.md` — Redis pub/sub для WS (если внедрено)
- [ ] **6.7.4** `CHANGELOG.md` — запись Sprint 6 с цифрами (тесты, endpoints, контейнеры)
- [ ] **6.7.5** `SKILL.md` (devops/ai-tutor-deploy) — новые pitfalls (CI/CD secrets, TG rate-limit, WS pub/sub race conditions, offsite checksum)

## 6.8 Gate Sprint 6 (выход)

- [ ] **6.8.1** `pytest tests/ -q` → **247+N** зелёных (N — новые тесты Sprint 6)
- [ ] **6.8.2** `next build` → ✅
- [ ] **6.8.3** `docker compose ps` на проде → 5/5 healthy
- [ ] **6.8.4** Push в feature-ветку → полный pipeline tests → deploy → smoke проходит
- [ ] **6.8.5** Тест-инцидент (остановить redis на 1 мин) → пришёл алерт в TG
- [ ] **6.8.6** Реальный test-restore на чистом Postgres → данные целы
- [ ] **6.8.7** Производительность WS под нагрузкой — sanity check (2 клиента, ping/pong latency)

---

# 🟧 СПРИНТ 7 — UX ученика (главный пользователь — Кирилл, T1D)

**Цель:** практика как приоритет №1, материал фиксируется через цикл
«объясни → практика (≥5 задач) → проверка → фиксация → SM-2».
**Выходной gate:** +N тестов, Playwright E2E полного цикла ученика, нет регресса
существующего UX.

> T1D-учёт ВЕЗДЕ: крупные элементы, без обратных таймеров, автосохранение,
> мягкое возвращение после паузы, без «сгорающих» стриков.

---

## 7.1 Markdown-рендер AI-ответов + typewriter-эффект

- [ ] **7.1.1** Прочитать `apps/web/components/lesson/*`, текущий чат-вью
- [ ] **7.1.2** Установить `react-markdown@^9` + `remark-gfm`, `rehype-sanitize` (XSS-safe)
- [ ] **7.1.3** Компонент `<AiMarkdown text={...} />` — рендер markdown, code-blocks, math (KaTeX — оценить bundle-size)
- [ ] **7.1.4** Typewriter-эффект для WS-стрима: показывать чанки по мере получения, не ждать `done`
- [ ] **7.1.5** Тесты: XSS-защита (`<script>` в ответе AI не рендерится), math рендерится, код подсвечивается
- [ ] **7.1.6** Bundle-size audit: `next build` + проверить что `react-markdown` + плагины не раздувают bundle >200KB gzip

## 7.2 Кнопка микрофона в `/topics/[id]`

- [ ] **7.2.1** Прочитать `app/voice/router.py` (`POST /api/v1/voice/transcribe`), env `WHISPER_API_URL`
- [ ] **7.2.2** UI в `/topics/[id]`: крупная кнопка 🎤 рядом с полем ввода (T1D — крупные элементы)
- [ ] **7.2.3** Recording-индикатор: явный пульсирующий круг + таймер, отмена одним тапом
- [ ] **7.2.4** MediaRecorder API → blob → POST /voice/transcribe → текст вставляется в поле ввода (можно редактировать)
- [ ] **7.2.5** Rate-limit на /voice/transcribe (20/мин/user, иначе можно заддосить)
- [ ] **7.2.6** Audit log при transcribe (action="voice.transcribe", entity="user", details={duration_sec, lang_detected})
- [ ] **7.2.7** Тесты backend: transcribe успех/ошибка/таймаут, превышение rate-limit → 429
- [ ] **7.2.8** Playwright E2E: запрос доступа к микрофону, запись → текст → отправка

## 7.3 Автосохранение состояния урока (critical при T1D)

- [ ] **7.3.1** Прочитать текущий `lesson state` в Zustand/store или useState
- [ ] **7.3.2** localStorage: каждые 5 сек (debounce) писать `{topic_id, current_block, draft_answer, last_saved_at}`
- [ ] **7.3.3** Серверный черновик: при первом автосохранении — POST на новый endpoint `POST /student/topics/{id}/draft` (миграция 0011?)
- [ ] **7.3.4** При загрузке `/topics/[id]` — восстанавливать из localStorage ИЛИ серверного черновика (последний выигрывает)
- [ ] **7.3.5** Кнопка «продолжить с прошлого раза» — если был черновик
- [ ] **7.3.6** Тесты: прерывание в середине → перезагрузка → состояние восстановлено
- [ ] **7.3.7** Cleanup: при `published_at` материала меняется — старые черновики помечаются `stale=true`

## 7.4 Улучшенный практический цикл

- [ ] **7.4.1** Прочитать текущий UI практики в `apps/web/app/topics/[id]/page.tsx`
- [ ] **7.4.2** Серия задач (≥5) с прогресс-баром БЕЗ таймера
- [ ] **7.4.3** Hint по нарастающей: 1) наводящий вопрос → 2) подсказка к решению → 3) полный разбор (только если студент нажал 2 раза «не знаю»)
- [ ] **7.4.4** Backend: `POST /tasks/{id}/hint?level=1|2|3` — выдаёт подсказку указанного уровня (без выдачи ответа!)
- [ ] **7.4.5** Моментальная авто-проверка: `POST /tasks/{id}/check` с ответом ученика → возвращает `{correct, expected_pattern, diff}`
- [ ] **7.4.6** Эталонные решения в `learning_materials.practice_tasks` (JSONB) — обязательное поле при AI-генерации (Sprint 8)
- [ ] **7.4.7** При завершении всех задач — фиксация темы + автоматическая постановка в SM-2 очередь (есть endpoint из Sprint 2)
- [ ] **7.4.8** Тесты: hint 3 уровня, авто-проверка numeric/keyword/semantic, постановка в SM-2

## 7.5 Мягкая геймификация (без давления!)

- [ ] **7.5.1** Баджи за **усилие** (НЕ за streak): «Начал тему», «Вернулся к сложному», «Объяснил своими словами»
- [ ] **7.5.2** Backend: `app/gamification/badges.py` — таблица `badges` (миграция 0012), `user_badges`
- [ ] **7.5.3** Endpoint `GET /api/v1/student/badges` — список полученных + доступных (locked/unlocked)
- [ ] **7.5.4** UI в `/student`: «Мои достижения» — карточки баджей с описанием, дата получения
- [ ] **7.5.5** **НИКАКИХ «сгорающих» стриков, обратных таймеров, штрафов за паузу.** Это критично для T1D.
- [ ] **7.5.6** Тесты: событие триггерит badge → пользователь видит; пауза не штрафует

## 7.6 E2E полного цикла ученика (Playwright)

- [ ] **7.6.1** Сценарий A: вход → тема → объяснение → практика → проверка → повторение
- [ ] **7.6.2** Сценарий B: прерывание → перезагрузка → восстановление черновика → завершение
- [ ] **7.6.3** Сценарий C: голосовой ввод (с моком микрофона) → текст вставляется → отправка
- [ ] **7.6.4** Сценарий D: подсказки 3 уровня → разбор → фиксация
- [ ] **7.6.5** Все новые E2E — зелёные на CI

## 7.7 Документация Sprint 7

- [ ] **7.7.1** `docs/api.md` — новые endpoints (`/voice/transcribe` rate-limit, `/tasks/{id}/hint`, `/tasks/{id}/check`, `/student/topics/{id}/draft`, `/student/badges`)
- [ ] **7.7.2** `docs/architecture.md` — цикл обучения (диаграмма), T1D-ограничения в UX
- [ ] **7.7.3** `CHANGELOG.md` — запись Sprint 7
- [ ] **7.7.4** `SKILL.md` — pitfalls (Typewriter и WS backpressure, MediaRecorder в headless E2E, localStorage quota)

## 7.8 Gate Sprint 7

- [ ] **7.8.1** `pytest tests/ -q` → +N новых
- [ ] **7.8.2** `next build` → ✅
- [ ] **7.8.3** Playwright E2E — все 4 сценария зелёные
- [ ] **7.8.4** Manual UX review Кириллом (необязательно, но желательно) — нет «тормозящих» элементов

---

# 🟨 СПРИНТ 8 — Качество AI и контента (ядро ценности)

**Цель:** AI-генерация → структурированный JSON по schema → авто-проверка практики
→ RAG поверх учебника → полная картина AI-расходов в Prometheus.
**Выходной gate:** все teacher-эндпоинты возвращают schema-валидный JSON, нет
fallback-заглушек, RAG возвращает top-k чанков с цитатами.

---

## 8.1 Structured output для teacher-генерации

- [ ] **8.1.1** Прочитать `app/teacher/generator.py`, текущий парсинг ответа AI
- [ ] **8.1.2** Определить Pydantic-модель `GeneratedMaterial` (все 9 блоков шаблона, включая `practice_tasks[]` с `reference_solution`, `difficulty: easy|medium|hard`)
- [ ] **8.1.3** Перевести `AIProvider.generate()` в режим JSON-schema / function calling (если MiniMax поддерживает — проверить)
- [ ] **8.1.4** Если MiniMax НЕ поддерживает structured output: добавить `strict_json=True` флаг, пост-валидация через Pydantic, retry до 3 раз с другим промптом при ошибке
- [ ] **8.1.5** Убрать fallback-заглушку «не удалось разобрать» — при провале возвращать 502/422 с детальной ошибкой
- [ ] **8.1.6** MockProvider обновить: возвращать валидный по GeneratedMaterial JSON (для тестов)
- [ ] **8.1.7** Тесты: schema-валидный JSON, невалидный → retry → fallback на детальную ошибку, проверка меток сложности

## 8.2 Практические задачи с эталонными решениями

- [ ] **8.2.1** Расширить `learning_materials.practice_tasks` (JSONB) — обязательные поля: `prompt`, `reference_solution`, `difficulty`, `keywords[]`, `checker_type` (numeric|keyword|semantic)
- [ ] **8.2.2** Чекер `numeric`: regex/range (например, ответ = `42` или `40-44`)
- [ ] **8.2.3** Чекер `keyword`: обязательные ключевые слова (case-insensitive), min-match score
- [ ] **8.2.4** Чекер `semantic`: через AI-judge (отдельный мини-промпт: «Ответ ученика эквивалентен эталону? yes/no/reasoning»). Используется только при неоднозначности — экономия токенов
- [ ] **8.2.5** Audit-log для AI-judge (отдельная метрика `ai_judge_requests_total`)
- [ ] **8.2.6** Тесты: 3 типа чекеров, edge cases (числовой ответ с погрешностью, keyword в синонимах)

## 8.3 RAG: pgvector + индекс чанков

- [ ] **8.3.1** Прочитать `app/rag.py`, текущий hash-based fallback
- [ ] **8.3.2** **RAM-оценка ДО старта:** pgvector + sentence-transformers локально = ~500MB-1GB (модель all-MiniLM-L6 = ~90MB, hnsw index = зависит). При 4 GB RAM — риск OOM. Решить: API embeddings + cache (рекомендация по умолчанию) vs local (отложить).
- [ ] **8.3.3-A** **Если API:** использовать MiniMax `/embeddings` если доступен; иначе fallback на hash (как сейчас). Кэш Redis `embedding:{text_hash}` TTL 7d
- [ ] **8.3.3-B** **Если local:** sentence-transformers CPU-only (Intel optimizations), вынести в отдельный сервис с memory limit 1GB
- [ ] **8.3.4** Миграция 0010: таблица `chunks` (id, material_id, text, embedding vector(384), metadata JSONB), индекс hnsw (если pgvector extension доступен)
- [ ] **8.3.5** Backend: `/api/v1/rag/index` принимает учебник → chunker (по абзацам/заголовкам, max 500 токенов) → embedding → insert в `chunks`
- [ ] **8.3.6** Backend: `/api/v1/rag/search` → embed query → top-k=5 cosine similarity → вернуть чанки с `material_id` и цитатой
- [ ] **8.3.7** Интеграция с `app/ai/explain.py`: top-3 чанка → в контекст промпта
- [ ] **8.3.8** Тесты: index/search happy path, cache hit, no-results
- [ ] **8.3.9** Документация: `docs/architecture.md` — RAG flow, `SKILL.md` — RAM pitfalls

## 8.4 Полная картина AI-расходов (record_ai_request везде)

- [ ] **8.4.1** Прочитать `app/observability.py` (Sprint 5.1), найти ВСЕ вызовы AIProvider
- [ ] **8.4.2** Добавить `record_ai_request(mode, status, tokens_input, tokens_output, latency_ms)` во ВСЕ точки:
  - `app/ai/explain.py`, `app/ai/chat.py`, `app/teacher/generator.py`, `app/ai/judge.py` (новое)
- [ ] **8.4.3** Метрика `ai_cost_usd_total{mode}` (с тарифами MiniMax в env)
- [ ] **8.4.4** Тесты: каждое AI-flow инкрементит счётчик
- [ ] **8.4.5** Документация: список всех метрик в `docs/api.md` (раздел Prometheus)

## 8.5 Диагностика v2 (адаптивный CAT)

- [ ] **8.5.1** Прочитать `app/ai/diagnostic.py` (Sprint 1)
- [ ] **8.5.2** Адаптивный выбор следующего вопроса: после каждого ответа выбирать задачу по IRT-подобной логике (target = 0.7 success rate)
- [ ] **8.5.3** Привязка результатов к SM-2: после завершения диагностики — обновить `easiness_factor`, `next_review_at` для каждой затронутой темы
- [ ] **8.5.4** Тесты: адаптивный выбор (после лёгкого → сложнее), SM-2 обновление

## 8.6 Документация Sprint 8

- [ ] **8.6.1** `docs/api.md` — structured output schemas, RAG endpoints
- [ ] **8.6.2** `docs/architecture.md` — RAG flow, AI-judge
- [ ] **8.6.3** `CHANGELOG.md` — Sprint 8
- [ ] **8.6.4** `SKILL.md` — RAM pitfalls (embeddings, hnsw index size), JSON-schema provider compatibility

## 8.7 Gate Sprint 8

- [ ] **8.7.1** Все teacher-эндпоинты возвращают schema-валидный JSON (zero fallback stubs)
- [ ] **8.7.2** `pytest` +N зелёных
- [ ] **8.7.3** RAG возвращает top-5 чанков за <500ms (median)
- [ ] **8.7.4** Prometheus показывает все AI-режимы

---

# 🟦 СПРИНТ 9 — Родитель + Админ (наблюдаемость и связь)

**Цель:** weekly summary в email/Telegram, multi-child для родителя, real-time /admin
через WS (после Sprint 6.3), Grafana дашборд, AI-бюджет контроль.
**Выходной gate:** weekly email приходит, real-time дашборд обновляется, лимит алертит.

---

## 9.1 Weekly summary email + Telegram родителю

- [ ] **9.1.1** Прочитать `app/parents/email_template.py` (если есть), SMTP infra (Sprint X.Y)
- [ ] **9.1.2** Jinja2 HTML-шаблон: KPI за неделю (пройдено уроков, средний балл, время, streak, top mistakes, recommendations)
- [ ] **9.1.3** Backend-скрипт `app/parents/weekly_report.py` — формирует данные, рендерит HTML, отправляет через SMTP-очередь (dry-run если SMTP недоступен)
- [ ] **9.1.4** Telegram-вариант: текстовое summary ≤ 4096 символов, кнопка-ссылка на полный PDF
- [ ] **9.1.5** Cron: `0 18 * * 0` (воскресенье 18:00 МСК) → запускает для всех родителей с детьми
- [ ] **9.1.6** Тесты: шаблон рендерится, mock SMTP получает письмо, multi-parent (2 ребёнка) — 2 письма

## 9.2 Multi-child для родителя

- [ ] **9.2.1** Миграция 0013: таблица `parent_children` (parent_id, child_id) — many-to-many, заменяет current `students.parent_id` (deprecated, NOT NULL → nullable)
- [ ] **9.2.2** Backend: переписать доступы через эту таблицу (был JOIN `students.parent_id`, теперь `EXISTS (SELECT 1 FROM parent_children ...)`)
- [ ] **9.2.3** UI: `/parent` → селектор ребёнка (если несколько), сохранение выбора в cookie
- [ ] **9.2.4** Existing routes обновить: `/parents/students/{id}/dashboard` — проверить, что `id` это child_id, родитель имеет доступ через `parent_children`
- [ ] **9.2.5** **Privacy:** 404 (не 403) для не-привязанного ребёнка — сохранить
- [ ] **9.2.6** Тесты: 1 родитель ↔ 2 ребёнка → оба дашборда доступны; не-привязанный → 404; был-привязан-но-удалён → 404
- [ ] **9.2.7** Migration script (batch_alter_table): добавить таблицу, перенести данные, потом дропнуть старую колонку в следующей миграции (2-step для безопасности)

## 9.3 Real-time /admin через WebSocket

- [ ] **9.3.1** Зависимость: Sprint 6.3 (Redis pub/sub WS) — без него real-time невозможен на multi-worker
- [ ] **9.3.2** Endpoint `WS /api/v1/admin/ws` (требует role=admin) — стримит live-метрики
- [ ] **9.3.3** События: активные сессии, AI req/min, latency p50/p95/p99, 5xx rate, статусы Redis/SMTP/DB, свежесть backup, размер email-очереди
- [ ] **9.3.4** UI `/admin/dashboard`: recharts / chart.js для графиков (оценить bundle-size)
- [ ] **9.3.5** Тесты: WS подключение, события приходят, отписка при disconnect

## 9.4 AI-бюджет контроль в /admin

- [ ] **9.4.1** Прочитать `app/observability.py` (Sprint 8.4 метрики)
- [ ] **9.4.2** Backend: `app/admin/budget.py` — таблица `ai_budget` (mode, daily_limit_tokens, alert_threshold_pct)
- [ ] **9.4.3** Middleware/checker: при превышении `alert_threshold_pct` → return 429 с retry-after для AI endpoints
- [ ] **9.4.4** UI `/admin/budget`: настройка лимитов по mode (explain, chat, teacher-generator, judge), просмотр графика «потрачено / лимит»
- [ ] **9.4.5** TG-алерт при превышении лимита (через infra из Sprint 6.2)
- [ ] **9.4.6** Тесты: under-limit → 200, over-limit → 429, reset в начале суток

## 9.5 Grafana dashboard

- [ ] **9.5.1** Docker Compose: добавить `grafana` сервис (6-й контейнер, рассчитать RAM: ~100MB)
- [ ] **9.5.2** Prometheus internal scrape: `/metrics` бэкенда на localhost (не через self-signed HTTPS наружу)
- [ ] **9.5.3** Grafana provisioned datasource: `prometheus:9090` (если добавлять prometheus) ИЛИ nginx `location /internal-prom/` с IP whitelist
- [ ] **9.5.4** Dashboard JSON: панели для http_requests_total, ai_tokens_total, active_sessions, latency histograms
- [ ] **9.5.5** Smoke: открыть Grafana UI → дашборд рендерится, метрики обновляются
- [ ] **9.5.6** Доступ: admin-only (HTTP BasicAuth через nginx)

## 9.6 Документация Sprint 9

- [ ] **9.6.1** `docs/api.md` — new endpoints (weekly_report, multi-child, /admin/ws, /admin/budget)
- [ ] **9.6.2** `docs/security.md` — privacy родителя остаётся (PII aggregation only)
- [ ] **9.6.3** `CHANGELOG.md` — Sprint 9

## 9.7 Gate Sprint 9

- [ ] **9.7.1** `pytest` +N зелёных
- [ ] **9.7.2** Cron weekly отрабатывает, родитель получает email (на тест-аккаунте)
- [ ] **9.7.3** Real-time WS показывает обновления <1s
- [ ] **9.7.4** Grafana доступен admin-у

---

## 🏁 ИТОГИ (2026-07-13, автономная работа 2)

### Sprint 7 — UX ученика (полностью завершён)
- [x] **7.1** Markdown-рендер + typewriter (завершён в первой итерации)
- [x] **7.2** Кнопка микрофона с MediaRecorder API + rate-limit 20/мин на пользователя
- [x] **7.3** Автосохранение урока (завершён в первой итерации)
- [x] **7.4** Hint endpoint с 3 уровнями (наводящий / подсказка / разбор)
- [x] **7.5** Баджи за усилие (10 баджей + миграция 0011 + UI `/student/badges`)
- [x] **7.6** E2E полный цикл ученика (4 теста в `student.spec.ts`)

### Sprint 8 — Качество AI (полностью завершён)
- [x] **8.1** Structured output + retry (завершён в первой итерации)
- [x] **8.2** Чекеры: numeric/keyword/exact + dispatcher (32 теста)
- [x] **8.3** RAG embedding cache в БД (миграция 0012_rag_chunks, 12 тестов)
- [x] **8.4** record_ai_request() во всех режимах (завершён в первой итерации)
- [x] **8.5** CAT адаптивная диагностика v2 (20 тестов)

### Sprint 9 — Родитель+Админ (полностью завершён)
- [x] **9.1** Weekly summary email (завершён в первой итерации)
- [x] **9.2** Multi-child UI (завершён в первой итерации)
- [x] **9.3** Real-time /admin через WS (Sprint 9.3 backend ранее + UI real-time dashboard)
- [x] **9.4** AI-бюджет контроль (завершён в первой итерации)
- [x] **9.5** Grafana + Prometheus (завершён в первой итерации)

### Sprint 10 — Техдолг (полностью завершён в первой итерации)

### 7.1 ✅ Markdown + typewriter — РАЗВЕРНУТО НА ПРОДЕ
- Backend `app/ai/markdown_render.py` (markdown-it-py, html=False, sanitization attrs)
- `_ai_response()` helper в `app/ai/router.py` — все 3 AI-endpoint (explain/chat/hint)
  возвращают `content` + `content_html` обратно совместимо
- Frontend `lib/markdown.ts` (минимальный парсер, 7КБ) — для WS-стрима в реальном времени
- Frontend `components/SafeMarkdown.tsx` — рендер с typewriter-курсором во время стрима
- Заменён `whitespace-pre-wrap` → `SafeMarkdown` в `app/topics/[id]/page.tsx`

### 7.3 ✅ Автосохранение урока — РАЗВЕРНУТО НА ПРОДЕ
- Миграция `0010_topic_drafts` (новая таблица с UNIQUE (user_id, topic_id))
- Backend `app/student/models.py` (TopicDraft), 3 endpoint: PUT/GET/DELETE
- Frontend `lib/api.ts` (topicDraftLoad/Save/Clear)
- `app/topics/[id]/page.tsx` автосохранение: localStorage каждые 5 сек, сервер каждые 15 сек,
  авто-восстановление при загрузке страницы (приоритет: localStorage — свежее, сервер — резерв)

### 7.5 / 7.4 / 7.2 / 7.6 — отложены в Sprint 7.2

### Файлы:
- Backend: `app/ai/markdown_render.py`, `app/ai/router.py`, `app/student/{models,router}.py`,
  `app/main.py`, `apps/backend/alembic/versions/0010_topic_drafts.py`,
  `apps/backend/requirements.txt` (+markdown-it-py==3.0.0)
- Frontend: `apps/frontend/lib/markdown.ts`, `apps/frontend/components/SafeMarkdown.tsx`,
  `apps/frontend/lib/api.ts`, `apps/frontend/app/topics/[id]/page.tsx`
- Tests: `apps/backend/tests/test_sprint7.py` (+22 теста)

### Тесты / smoke:
- `pytest tests/ -q` → **269 passed** (было 247, +22 Sprint 7.1+7.3)
- Smoke на проде (после rebuild): PUT/GET draft вернули то же payload;
  POST /ai/explain вернул content_html с Markdown-разметкой
- 5/5 контейнеров healthy

# 🟩 СПРИНТ 10 — Техдолг и масштабируемость

**Цель:** закрыть XSS-вектор (JWT в httpOnly cookie), упорядочить frontend state,
заложить каркас `/api/v2`, довести backup до автоматической верификации, расширить E2E.

---

## 10.1 JWT в httpOnly + Secure cookie (закрыть XSS-вектор)

- [ ] **10.1.1** Прочитать `app/auth/security.py`, текущий flow (login → response с token в JSON → localStorage)
- [ ] **10.1.2** Решение для владельца: перевести на httpOnly + Secure + SameSite=Lax cookie. **Если localStorage принципиально — обосновать** (например, мобильное PWA требует)
- [ ] **10.1.3-A** **Если cookie:** Set-Cookie с httpOnly, Secure (только HTTPS), SameSite=Lax, Path=/; access (24h), refresh (30d, отдельный path /auth/refresh)
- [ ] **10.1.4** Refresh rotation: при использовании refresh выдаётся новый access + refresh (старый refresh инвалидируется)
- [ ] **10.1.5** CSRF: double-submit cookie или SameSite=Strict (зависит от решения)
- [ ] **10.1.6** Logout: очистка cookie + Redis blacklist для refresh token
- [ ] **10.1.7** Frontend: убрать `localStorage.getItem('token')` — теперь cookie отправляется автоматически
- [ ] **10.1.8** Тесты: XSS payload не может украсть токен (нет в JS-accessible storage), refresh rotation работает

## 10.2 Frontend state — Zustand/Jotai для сложных страниц

- [ ] **10.2.1** Audit текущего state: lesson view, /admin/dashboard, /parent/dashboard — где useState > 3 штук на странице
- [ ] **10.2.2** Только если есть реальная боль (re-renders, prop drilling) — ввести Zustand (минимум boilerplate)
- [ ] **10.2.3** НЕ тащить ради тащить — для простых страниц useState + Context остаётся
- [ ] **10.2.4** Тесты: store actions работают, нет re-renders при unrelated state changes

## 10.3 API versioning каркас /api/v2

- [ ] **10.3.1** FastAPI: создать `app/v2/` структуру (зеркало `app/v1/` по необходимости)
- [ ] **10.3.2** Маршрутизация: главное приложение подключает `/api/v1` (legacy) + `/api/v2` (новое)
- [ ] **10.3.3** НЕ ломать v1 — добавить v2-маршруты только если требуется breaking change
- [ ] **10.3.4** OpenAPI docs: `/docs` показывает обе версии

## 10.4 Backup offsite verification автоматизировать

- [ ] **10.4.1** Зависимость: Sprint 6.6 (test-restore)
- [ ] **10.4.2** Cron: еженедельно — запускать test-restore в изолированном docker-контейнере, проверять `pg_dump --schema-only` + count critical tables
- [ ] **10.4.3** TG-алерт если verify fail
- [ ] **10.4.4** Retention: 7 daily / 4 weekly / 3 monthly (ротация с проверкой целостности старых backup'ов)

## 10.5 E2E покрытие

- [ ] **10.5.1** Teacher-flow полный: регистрация teacher → AI-генерация → правка → approve → publish → ученик видит
- [ ] **10.5.2** Parent dashboard.pdf: запрос HTML-отчёта, проверка что содержит KPI / не содержит PII / 404 для чужого ребёнка
- [ ] **10.5.3** Review-цикл (SM-2): ученик завершает тему → через N дней возвращается → видит «к повторению» → отвечает → EF обновляется
- [ ] **10.5.4** Все E2E зелёные на CI

## 10.6 Документация Sprint 10

- [ ] **10.6.1** `docs/security.md` — JWT cookie policy + обоснование, если localStorage
- [ ] **10.6.2** `docs/api.md` — /api/v2 (если внедрено), изменения cookie flow
- [ ] **10.6.3** `docs/architecture.md` — state management, backup verify
- [ ] **10.6.4** `CHANGELOG.md` — Sprint 10

## 10.7 Gate Sprint 10

- [ ] **10.7.1** `pytest` + E2E всё зелёное
- [ ] **10.7.2** Security scan (semgrep / bandit) без новых HIGH-issues
- [ ] **10.7.3** Backup verify автоматически проходит

---

# 🌐 СКВОЗНЫЕ ТРЕБОВАНИЯ (на все спринты 6+)

> Из AI-DEEP-AUDIT-PROMPT.md / внешнего аудита.

## Безопасность (AppSec)

- [ ] **S.1** RBAC на КАЖДОМ новом endpoint через `app/common/deps.py` (`require_role/owner`). Тесты 401/403.
- [ ] **S.2** Все пользовательские входы через `sanitize_user_input + detect_injection` (расширить на новые flow, **включая teacher-генерацию**).
- [ ] **S.3** PII ученика (ФИО, адрес, T1D-медданные) **НИКОГДА** не попадает в AI-промпты, логи, метрики-labels, audit details. Это чувствительные медданные — строже GDPR.
- [ ] **S.4** X-Forwarded-For — только от TRUSTED_PROXIES (есть `_client_ip`). Новые endpoint с IP-логикой — через хелпер.
- [ ] **S.5** Каждое защищённое действие → `audit_logs(action, entity, entity_id, details, ip)`.
- [ ] **S.6** Rate-limit на любой новый дорогой/публичный endpoint. Redis-backed для multi-worker.

## Производительность (при 4 GB RAM)

- [ ] **P.1** N+1 — `selectinload/joinedload` на read-heavy (parent dashboard, teacher-списки).
- [ ] **P.2** AI-таймаут 30с; долгое (TTS, batch generation) — в background worker, **не в HTTP**.
- [ ] **P.3** Prometheus labels — контроль cardinality (path normalization уже есть).
- [ ] **P.4** Любая память-ёмкая фича (pgvector, embeddings, TTS) — **расчёт RAM ДО внедрения**.

## Надёжность

- [ ] **R.1** Best-effort для вторичных операций (audit, метрики, email) — не ронять основной запрос (паттерн Sprint 5.2).
- [ ] **R.2** Idempotency для операций, которые могут повториться (approve/publish, review-result).
- [ ] **R.3** Graceful degradation: нет Redis → in-memory fallback; нет SMTP → dry_run; нет AI-ключа → MockProvider.

## Тестируемость

- [ ] **T.1** SQLite-in-memory + StaticPool. Новый глобальный state → `_reset_state` в `conftest.py`.
- [ ] **T.2** MockProvider — schema-валидный JSON для новых AI-flow (после Sprint 8).

---

# 🚧 Открытые вопросы (≤5) — задать владельцу ДО тяжёлых решений

> Эти вопросы вынесены из промта аудита. Лучше уточнить один раз, чем потом переделывать.

1. **Let's Encrypt** (Sprint 6.5): есть валидный домен с A-записью на 192.168.1.86,
   или прод остаётся LAN-only self-signed навсегда?
2. **Embeddings для RAG** (Sprint 8.3): API (платно, экономит RAM) или локально
   (бесплатно, риск OOM при 4 GB)? **Рекомендация по умолчанию:** API + cache.
3. **Проект остаётся личным** (влияет на security/multi-tenancy) или пойдёт к
   другим семьям? Если публичный — потребуется tenant isolation, JWT rotation,
   CSP ужесточение, etc.
4. **TTS (голос AI) для ученика** — делать или overkill? **По умолчанию — отложить**
   (микрофон из Sprint 7 покрывает voice-input, TTS-out менее критичен).
5. **Multi-child для родителя** (Sprint 9.2) — реальная нужда сейчас или позже?
   Внедрение требует миграции данных + UI-селектора.

---

# 📂 Связанные документы

| Файл                                          | Назначение                                                |
|-----------------------------------------------|-----------------------------------------------------------|
| `../ROADMAP.md`                                | Долгосрочный план (Sprint 1-5, baseline)                  |
| `../architecture.md`                           | Архитектура (обновляется каждый спринт)                   |
| `../api.md`                                    | API reference (обновляется каждый спринт)                 |
| `../security.md`                               | Политика безопасности                                     |
| `../deployment.md`                             | Deploy runbook (особенно CI/CD после Sprint 6)            |
| `../../CHANGELOG.md`                           | История спринтов (Sprint 6+ записи сюда)                   |
| `~/.hermes/skills/devops/ai-tutor-deploy/SKILL.md` | Production runbook + pitfalls (обязателен к прочтению при работе с продом) |
| `../../AI-DEEP-AUDIT-PROMPT.md`                | Глубокий промт для будущих аудитов                        |
| `../../AI-DEEP-AUDIT-PROMPT.md`                | Глубокий аудит (990 строк)                            |
| `../../docs/MASTER-HANDOVER-PROMPT.md`          | Полный handover (Pilot Core, ~742 строки)             |

---

# 📝 История изменений этого плана

- **2026-07-13** — Создан файл `docs/plans/SPRINT-6-PLAN.md` на основе внешнего AI-аудита.
  Разбит на 5 спринтов (6–10) с задачами/подзадачами/чекбоксами. Вынесены 5 открытых вопросов.
  Все оценки и приоритеты — из источника аудита. Сохранены сквозные требования (AppSec, perf,
  надёжность, тестируемость).
