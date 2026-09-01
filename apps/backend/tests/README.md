# Backend Tests — Sprint S0 (2026-08-31)

> **Свежие цифры** (Sprint S0, фикс регрессии test_all_subject_contracts module-level env):
> фактический прогон `pytest tests/ -q` в `apps/backend` с env из этого README —
> **1340 passed / 30 skipped / 0 failed** за ~516 сек (после фикса test pollution).
>
> **Было** (2026-08-31 audit): 1338 passed / 2 failed / 30 skipped — регрессия
> `test_sprint80_hourly_budget` (×2: `test_hourly_limit_constant_defined`,
> `test_hourly_limit_raises_budget_exceeded`) из-за module-level
> `os.environ["AI_BUDGET_REQUESTS_PER_HOUR"]="10000"` в новом файле
> `tests/test_all_subject_contracts.py`. Это мутировало env для всех тестов после
> `t` в алфавитном порядке и ломало budget-ассерты. Исправлено: `setdefault`
> вместо присваивания, per-test override остался через `ai_budget.reload_limits()`.
>
> **Корневая причина регрессии:** `test_all_subject_contracts.py` уже вызывал
> `ai_budget.reload_limits(...)` в fixture `_client()` для своих нужд, но дублировал
> это через module-level env — что задевало остальные тесты.

## Как читать результат pytest

```bash
$ pytest tests/ -q
1340 passed, 30 skipped in 516.43s (0:08:36)
```

- **1340 passed** — рабочие тесты, всё OK
- **30 skipped** — модульный skip (oauth/voice/smtp/realtime/weekly) + 1 skipif в flake-guard
- **0 failed** — если видишь failed → баг, чини немедленно
- **warnings** — pydantic/passlib deprecation warnings, не критично

## Категории тестов

### ✅ Активные (1340 теста на 2026-08-31, 174 файла) — НЕ ТРОГАТЬ без основания

| Файл / группа | Тестов (≈) | Что покрывает | Критичность |
|---|---:|---|---|
| `test_pilot_secure_exercises*.py` | ~25 | v2 secure flow (Pilot Core) | 🔴 Критично |
| `test_auth.py`, `test_password_reset.py`, `test_login_rate_limit.py` | ~30 | JWT login/refresh/rate-limit | 🔴 Критично |
| `test_rbac.py` | 23 | 4 роли (admin/teacher/parent/student) | 🔴 Критично |
| `test_sprint10_auth_cookie.py`, `test_sprint10_v2.py` | ~20 | JWT httpOnly cookies, /api/v2 namespace | 🔴 Критично |
| `test_sprint80_hourly_budget.py` | 6 | hourly AI budget (20/час) + BudgetExceeded | 🔴 Критично (S0 фикс) |
| `test_teacher.py` | 29 | teacher workflow (AI-генерация, approve, publish) | 🟡 Важно |
| `test_admin.py` + `test_admin_evidence.py` + `test_automated_release_gate.py` | 11+ | admin endpoints (audit, users, stats, evidence, release gate) | 🟡 Важно |
| `test_parent_dashboard.py` + `test_parent_dashboard_*.py` | ~20 | parent кабинет (multi-child, privacy, 2FA) | 🟡 Важно |
| `test_parents_materials.py`, `test_student_review.py` | ~20 | materials, SM-2 повторение | 🟡 Важно |
| `test_progress_diagnostics.py`, `test_diagnostic_expire.py` | ~30 | диагностика (CAT-адаптивная) | 🟡 Важно |
| `test_ai.py` + `test_ai_output_contract.py` + `test_ai_generate_*` | ~25 | AI endpoints (explain, hint, chat, generate, output contract) | 🟡 Важно |
| `test_health.py`, `test_observability.py`, `test_sprint82_healthcheck_redis.py` | ~20 | /health, /ready, /metrics, Prometheus, Redis health | 🟡 Важно |
| `test_email_retry.py`, `test_email_per_lesson.py` | ~10 | SMTP retry, email-уведомления | 🟢 Инфра |
| `test_ocr.py`, `test_subjects.py`, `test_all_subject_contracts.py` | ~20 | OCR для сканов, школьная программа, all-subject contract | 🟢 Инфра |
| `test_techdebt.py`, `test_ws_rate_limit.py`, `test_websocket.py` | ~25 | техдолг + WS | 🟡 Важно |
| `test_notifications.py` | ~10 | in-app уведомления | 🟡 Важно |
| `test_pilot_seed_users.py` | 8 | seed CLI + PILOT_SEED_TOKEN | 🟢 Инфра |
| `test_refresh.py` | ~5 | JWT refresh token rotation | 🟡 Важно |
| `test_math6_pilot.py`, `test_flake_guard_sprint32.py`, `test_progress_diagnostics.py` | ~80 | math6 pilot + flake guards | 🟡 Важно |
| `test_fallback_safety_contract.py`, `test_mapping_quality_audit.py`, `test_mapping_range_contract.py`, `test_ops_release_gate.py` | ~30 | audit/release scripts | 🟢 Инфра |
| `test_sprint*` (остальные sprint-маркеры) | ~640 | история спринтов 8–110 | 🟡 Важно |

### ⏸️ Skipped (30 тестов) — модульный skip с обоснованием в pytestmark

| Файл | Skip причина | Реактивировать когда |
|---|---|---|
| `test_oauth.py` (5) | Google/Яндекс OAuth: credentials не заданы | Подключишь OAuth |
| `test_voice.py` (4) + `test_sprint7_voice.py` (9) | Voice UI: кнопка микрофона скрыта (`NEXT_PUBLIC_VOICE_ENABLED=0`) | Включишь voice для Кирилла |
| `test_sprint9_weekly.py` (7) | Weekly email: код есть, SMTP не настроен | Настроишь SMTP |
| `test_sprint9_realtime.py` (7) | Real-time /admin WS: UI скрыт (Pilot Phase 5) | Покажешь UI или multi-worker |
| `test_flake_guard_sprint32.py` (1, `skipif`) | flake-guard запускается вручную через env | — |

**Не соответствует историческому "71 skip":** `test_sprint8_checkers.py` (32) и
`test_sprint8_rag.py` (12) **реактивированы** в Sprint 19 / 3.5.2 — это нормально.

## Запуск

```bash
cd apps/backend
APP_SECRET_KEY='test-secret-key-for-pytest-only-1234567890' \
APP_ENV=development \
DATABASE_URL='sqlite+pysqlite:///:memory:' \
CORS_ORIGINS='http://localhost:3000' \
AI_API_KEY='mock-key-for-tests' \
UPLOAD_DIR='/tmp/ai-tutor-test-uploads' \
PYTHONDONTWRITEBYTECODE=1 \
.venv/bin/pytest tests/ -q --tb=line -p no:cacheprovider
```

Ожидаемо (S0, 2026-08-31): **1340 passed / 30 skipped**, ~516 сек.

## Какие тесты обязательные перед deploy

Перед `bash deploy/release/deploy.sh` запускай:

```bash
cd apps/backend && pytest tests/ -q --tb=line
cd apps/frontend && npm run build
bash deploy/release/smoke.sh
```

**Все три должны быть зелёные**. Если pytest падает — не деплоишь.

## Sprint S0 — что поменялось

- Зафиксирована регрессия test_sprint80_hourly_budget ×2 (test pollution из test_all_subject_contracts).
- Полный suite green: 1340 passed / 30 skipped / 0 failed.
- Актуализированы цифры (362/71 → 1340/30), убрана устаревшая категоризация "dead code" для уже реактивированных sprint8_checkers/sprint8_rag.
- Добавлены новые активные тесты 2026-08-22/23/24: ai_output_contract, all_subject_contracts, automated_release_gate, fallback_safety_contract, mapping_quality_audit, mapping_range_contract, ops_release_gate.

## Что НЕ тестируется (TODO)

| Что | Почему |
|---|---|
| UI-флоу (Playwright есть, но не все happy paths) | Pilot phase, manual testing (S6 walkthrough) |
| Нагрузочные тесты (100+ пользователей) | 1 user, не нужно |
| Безопасность (penetration testing) | Pilot phase, базовая защита есть |
| Mobile (нет приложения) | Out of scope |

---

*Обновлено в Sprint S0 (2026-08-31). Предыдущая версия — Sprint 3.5.1 (16 июля 2026).*
