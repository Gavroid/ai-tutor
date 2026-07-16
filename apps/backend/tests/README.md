# Backend Tests — Sprint 3.5.1

## TL;DR

- **362 теста проходят** (после чистки dead code)
- **71 тест skip'нут** (мёртвый код, RAG/semantic/voice/weekly/realtime/oauth)
- Прогон занимает ~3 минуты
- Запускать: `cd apps/backend && pytest tests/ -q`

## Категории тестов

### ✅ Активные (362 теста) — НЕ ТРОГАТЬ

| Файл | Тестов | Что покрывает | Критичность |
|---|---:|---|---|
| `test_pilot_secure_exercises*.py` | ~25 | v2 secure flow (Pilot Core) | 🔴 Критично |
| `test_auth.py`, `test_password_reset.py`, `test_login_rate_limit.py` | ~30 | JWT login/refresh/rate-limit | 🔴 Критично |
| `test_rbac.py` | 23 | 4 роли (admin/teacher/parent/student) | 🔴 Критично |
| `test_sprint10_auth_cookie.py`, `test_sprint10_v2.py` | ~20 | JWT httpOnly cookies, /api/v2 namespace | 🔴 Критично |
| `test_teacher.py` | 29 | teacher workflow (AI-генерация, approve, publish) | 🟡 Важно |
| `test_admin.py` | 11 | admin endpoints (audit, users, stats) | 🟡 Важно |
| `test_parent_dashboard.py` | 13 | parent кабинет (multi-child, privacy) | 🟡 Важно |
| `test_parents_materials.py`, `test_student_review.py` | ~20 | materials, SM-2 повторение | 🟡 Важно |
| `test_progress_diagnostics.py`, `test_diagnostic_expire.py` | ~30 | диагностика (CAT-адаптивная) | 🟡 Важно |
| `test_ai.py` | 12 | AI endpoints (explain, hint, chat, generate) | 🟡 Важно |
| `test_health.py`, `test_observability.py` | ~15 | /health, /ready, /metrics, Prometheus | 🟡 Важно |
| `test_email_retry.py`, `test_email_per_lesson.py` | ~10 | SMTP retry, email-уведомления | 🟢 Инфра |
| `test_ocr.py`, `test_subjects.py` | ~15 | OCR для сканов, школьная программа | 🟢 Инфра |
| `test_techdebt.py`, `test_ws_rate_limit.py`, `test_websocket.py` | ~25 | техдолг + WS | 🟡 Важно |
| `test_notifications.py` | ~10 | in-app уведомления | 🟡 Важно |
| `test_pilot_seed_users.py` | 8 | seed CLI + PILOT_SEED_TOKEN | 🟢 Инфра |
| `test_refresh.py` | ~5 | JWT refresh token rotation | 🟡 Важно |

### ⏸️ Skipped (71 тест) — DEAD CODE (Sprint 3.5.1)

| Файл | Skip причина | Реактивировать когда |
|---|---|---|
| `test_sprint8_checkers.py` (32) | `app.practice.checkers` не вызывается в v2 (Pilot Core заменил на exact match) | Подключишь semantic checkers к v2 hot path |
| `test_sprint8_rag.py` (12) | RAG код есть, но **не подключён** к `explain_topic` | **Sprint 3.5.2** — подключение RAG |
| `test_sprint9_weekly.py` (8) | Weekly email: код есть, **SMTP не настроен** | Настроишь SMTP |
| `test_sprint9_realtime.py` (10) | Real-time /admin WS: UI скрыт (Pilot Phase 5) | Покажешь UI или multi-worker |
| `test_sprint7_voice.py` (9) | Voice UI: кнопка микрофона скрыта (`NEXT_PUBLIC_VOICE_ENABLED=0`) | Включишь voice для Кирилла |
| `test_voice.py` (4) | Дублирует `test_sprint7_voice` | Включишь voice |
| `test_oauth.py` (4) | Google/Яндекс OAuth: **credentials не заданы** | Подключишь OAuth |

Каждый skip имеет `pytestmark` в начале файла с обоснованием и инструкцией.

## Как читать результат pytest

```bash
$ pytest tests/ -q
362 passed, 71 skipped, 289 warnings in 197.82s
```

- **362 passed** — рабочие тесты, всё OK
- **71 skipped** — dead code (см. таблицу выше), pytest их даже не запускает
- **0 failed** — если видишь failed → баг, чини немедленно
- **warnings** — pydantic/passlib deprecation warnings, не критично

## Какие тесты обязательные перед deploy

Перед `bash deploy/release/deploy.sh` запускай:

```bash
cd apps/backend && pytest tests/ -q --tb=line
cd apps/frontend && npm run build
bash deploy/release/smoke.sh
```

**Все три должны быть зелёные**. Если pytest падает — не деплоишь.

## Sprint 3.5.2 — что меняется

После подключения RAG (Sprint 3.5.2):

1. Снять skip с `test_sprint8_rag.py` (заменить `pytestmark` на `pytestmark = pytest.mark.integration`)
2. Добавить 10-15 новых тестов на RAG-сценарии (точность retrieval, fallback, скорость)
3. Запустить walkthrough, проверить с реальным PDF учебника

## Что НЕ тестируется (TODO)

| Что | Почему |
|---|---|
| UI-флоу (Playwright есть, но не все happy paths) | Pilot phase, manual testing |
| Нагрузочные тесты (100+ пользователей) | 1 user, не нужно |
| Безопасность (penetration testing) | Pilot phase, базовая защита есть |
| Mobile (нет приложения) | Out of scope |

---

*Создано в Sprint 3.5.1 (16 июля 2026). До этого было 433 теста без документации — стейкхолдер не мог понять что они проверяют и какие нужны. Теперь каждому тесту есть место в таблице.*
