# Sprint 4 — Технический долг (АРХИВ)

> **Статус:** архивный документ. Подробности Sprint 4 покрыты в `CHANGELOG.md`.
> Сохранён для ссылки на конкретные значения конфигурации (rate-limits, trusted CIDR).
> **Новые материалы по техническому долгу — в `docs/ROADMAP.md` (Sprint 6+) и `docs/plans/SPRINT-6-PLAN.md`.**

## Выполненные подзадачи

### 4.1 Rate limit на /auth/register ✅
- `POST /api/v1/auth/register` — теперь **5 регистраций в час на IP** (настраивается через `RATE_LIMIT_REGISTER_PER_HOUR`).
- In-memory лог + Redis fallback (как для login/AI).
- Audit log запись `user.register` остаётся, новое событие `audit.purge` для retention.
- Сообщение на русском: «Слишком много регистраций с этого IP. Подождите 1 час.»

### 4.2 Audit log retention ✅
- `app/admin/service.py::purge_old_logs(db, ttl_days)` — удаляет записи старше TTL.
- `POST /api/v1/admin/audit-log/purge?ttl_days=90` — admin endpoint для ручной очистки.
- Скрипт `deploy/cron/audit_cleanup.py` — для cron-задачи (ежедневно в 3 AM):
  ```cron
  0 3 * * * cd /opt/ai-tutor && /usr/local/lib/hermes-agent/venv/bin/python3 deploy/cron/audit_cleanup.py >> /var/log/ai-tutor/audit-cleanup.log 2>&1
  ```
- Поддерживает `--dry-run` для проверки.

### 4.3 X-Forwarded-For trust ✅
- Новый параметр `TRUSTED_PROXIES` (CIDR-список) в `app/config.py`.
- По умолчанию: `127.0.0.1/32,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16` (приватные сети).
- Новый хелпер `app/main.py::_client_ip(request, trusted_proxies)`:
  - Доверяет XFF только если immediate peer (request.client.host) в trusted CIDR.
  - Если peer не доверенный — XFF игнорируется (защита от подмены IP в rate-limit).
  - Если trusted_proxies пуст — XFF не читается.

### 4.4 Multi-worker uvicorn (документация)
- Dockerfile уже использует `uvicorn`. Production можно увеличить workers:
  ```yaml
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
  ```
- Rate-limit уже Redis-ready (см. `app/main.py::_get_redis()`).
- WebSocket — пока in-memory broadcasting; для multi-worker нужно подключить
  Redis pub/sub (не реализовано в этом спринте).

### 4.5 RAG в контексте AI-промптов (отложено)
- Текущий RAG (`app/rag.py`) изолирован. В Sprint 2/3 не подключали его
  в промпты `explain/chat`, чтобы не ломать контракт.
- План на Sprint 6+: добавить `RAG_RETRIEVAL_TOP_K=3` параметр, передавать
  top-k чанков в `AIService.explain_topic`/`chat` как дополнительный system-контекст.

### 4.6 Тесты ✅
- `tests/test_techdebt.py` — **12 новых тестов**:
  - `_ip_in_cidrs`: loopback, private, public-rejected, invalid
  - `_client_ip`: no-proxy, trusted+xff, untrusted-ignores-xff, private-trusted, no-xff
  - Register rate limit: 5 succeed, 6-й → 429, сообщение на русском

## Статистика Sprint 4

| Метрика                 | После Sprint 3 | После Sprint 4 |
|-------------------------|----------------|----------------|
| Backend tests           | 220            | **232** (+12)  |
| Cron-скрипты             | 0              | **1** (audit_cleanup.py) |
| Новые API endpoints      | 0              | +1 (admin/audit-log/purge) |
| Настройки                | —              | +3 (rate_limit_register, rate_limit_login, trusted_proxies) |

**Сборка:** backend pytest ✅ 232/232, frontend `next build` ✅ (без изменений).
