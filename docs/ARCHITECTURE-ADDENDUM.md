# Architecture Addendum — Sprint 16-53

**Дата:** 2026-07-26
**Базовый документ:** [docs/architecture.md](architecture.md)

Этот документ — дополнение к основной архитектуре, описывающее изменения
внесённые в Sprint 16-53 (P0/P1/P2 security hardening + T1D UX + parent 2FA +
audit log 2.0 + Grafana dashboards + CGM + i18n + invites + parent metrics).

---

## 🔒 Authentication Evolution

### До Sprint 27 (legacy)
```
localStorage: "ai-tutor-token"  → Authorization: Bearer ...
```

### После Sprint 27 (cookie-based)
```
Set-Cookie: ai_tutor_access=...; HttpOnly; Secure; SameSite=lax
Set-Cookie: ai_tutor_refresh=...; HttpOnly; Secure; Path=/api/v1/auth/
```

**Преимущества:**
- XSS не уводит токен (httpOnly)
- CSRF защищён SameSite=lax
- Middleware автоматически шлёт cookie (credentials: 'include')

**Где живёт:**
- `apps/backend/app/auth/router.py` — `login()`, `logout()`, `refresh()`
- `apps/backend/app/auth/security.py` — `_create_token()`, `get_current_user()`
- `apps/backend/app/auth/websocket*.py` — WS также читает cookie
- `apps/frontend/lib/api.ts` — все fetch через `credentials: 'include'`

### Sprint 32: Parent 2FA (TOTP)
```
Step 1: email + password → POST /auth/login
        → если parent с 2FA enabled → intermediate token (5 мин TTL)
Step 2: TOTP код → POST /auth/login-2fa
        → access_token + refresh_token
```

**Где живёт:**
- `apps/backend/app/users/twofa.py` — pyotp.TOTP + Fernet encryption + bcrypt backup codes
- `apps/backend/app/users/models.py` — `Parent2FA` model (1-to-1 c users)
- `apps/backend/app/parents/router.py` — 4 endpoints (`/enable`, `/disable`, `/status`, `/verify`)

---

## 🛡️ Security Hardening (Sprint 16 P0/P1/P2)

### Sprint 16 P0 — 6 критичных фиксов
1. **PostgreSQL вместо SQLite** — `/tmp` → PostgreSQL `telegram_bindings` (migration 0014)
2. **WS JWT → cookie** — `websocket.cookies.get("ai_tutor_access")`
3. **5xx → Telegram** — middleware enqueue в Redis list `ai:alerts`, alert worker BLPOPs
4. **Production validator** — `mock-*` API key → ValueError
5. **silent except → logger.error** — все except с `exc_info=True`
6. **Query params validation** — `Annotated[int, Query(ge, le)]` для DoS protection

### Sprint 16 P1 — 9 улучшений
1. WS rate-limit через Redis (`ws_rl:{uid}:{window}`)
2. AI budget guard на WS handshake (cost control)
3. /metrics IP whitelist (172.19.0.5 + testclient)
4. Streak timezone (Europe/Moscow)

### Где живёт:
- `apps/backend/app/main.py` — middleware + WebSocket handlers
- `apps/backend/app/bot/alert_worker.py` — v2 с graceful drain (Sprint 50)

---

## 📊 Observability

### Prometheus metrics (Sprint 5 + Sprint 49)
**System metrics** (Sprint 5):
- `http_requests_total{method, path, status}`
- `http_request_duration_seconds_bucket{le}`
- `ai_tokens_total{role}`
- `ai_requests_total{mode, status}`
- `active_sessions_total`

**Parent metrics** (Sprint 49, NEW):
- `parent_streak_current_streak_days{user_id}` (Gauge)
- `parent_streak_longest_streak_days{user_id}` (Gauge)
- `parent_subject_mastery_avg{user_id, subject}` (Gauge)
- `parent_attempts_total{user_id, day}` (Counter)
- `parent_session_pauses_total{user_id, reason}` (Counter)
- `parent_session_duration_seconds_bucket{le}` (Histogram)

**Где живёт:**
- `apps/backend/app/observability.py` — system metrics + middleware
- `apps/backend/app/parent_metrics.py` — NEW Sprint 49 (parent dashboard data)

### Grafana dashboards
- `ai-tutor-overview.json` (Sprint 9.2) — system health
- `parent-dashboard.json` (Sprint 39) — parent-friendly view
- `system-overview.json` (Sprint 39) — 5xx/latency/AI/materials

**Provisioning:** `deploy/grafana/provisioning/dashboards/dashboards.yml`
автоматически импортирует при старте Grafana.

---

## 🤖 T1D-Friendly Architecture (Sprint 21-42)

### UX Components
- `PauseButton` — 4 причины (break/hypo/hyper/other), streak сохраняется
- `SessionTimer` — 3-tier эскалация (20/40/60 мин), aria-live=polite
- `audio-cue` — Web Audio API, respects prefers-reduced-motion
- `RecoveryBadge` — показывается если recent hypo/hyper pause (last 30 мин)
- `CGMStatus` — opt-in badge с Nightscout proxy

### Backend endpoints
- `/api/v1/sessions/pause` — записывает pause в БД
- `/api/v1/sessions/pauses/recent` — список
- `/api/v1/progress/recommend-next` — возвращает recovery_mode + recovery_reason
- `/api/v1/cgm/config` + `/api/v1/cgm/latest` + `/api/v1/cgm/status` — opt-in

### T1D safety дизайн (Luna Pro compliant)
- ❌ **НЕ используем AI** для medical decisions
- ❌ **НЕ интерпретируем** glucose data
- ❌ **НЕ сохраняем** glucose values в БД
- ✅ **Opt-in** для всех CGM/recovery features
- ✅ **HTTPS-only** + SSRF protection
- ✅ **Timing-based** эвристики (30 min window)
- ✅ **Calm UI** (sky/blue, aria-live=polite)
- ✅ **Streak preservation** при паузе

---

## 🔑 Audit Log 2.0 (Sprint 45)

### Schema
```sql
audit_logs:
  - id, user_id, action, entity, entity_id
  - details (JSON), ip_address
  - created_at
  - previous_hash  -- Sprint 45: SHA-256 предыдущей записи
  - record_hash    -- Sprint 45: SHA-256 этой записи
```

### Hash chain
```
record() {
  prev_hash = SELECT record_hash FROM audit_logs ORDER BY id DESC LIMIT 1
  payload = JSON.stringify({all_fields, prev_hash})
  hash = SHA-256(payload)
  UPDATE audit_logs SET record_hash = hash WHERE id = ...
}
```

### Endpoints
- `GET /api/v1/admin/audit-log` — list (filterable)
- `GET /api/v1/admin/audit-log/verify` — hash chain integrity
- `GET /api/v1/admin/audit-log/export?fmt=json|csv` — compliance
- `POST /api/v1/admin/audit-log/purge` — retention (90 days default)

### Audit log coverage (Sprint 47+)
- `user.register`, `audit.purge`, `audit.export`
- `auth.2fa.enable/disable/verify/success/fail`
- `invite.create/delete/redeem`
- Все админ/teacher операции

---

## 📧 Public Invite Flow (Sprint 44)

### Schema
```sql
invites:
  - code (PK, 8-char, no 0/O/1/I/L)
  - created_by (FK users)
  - role (student/parent/teacher)
  - note, expires_at, max_uses
  - used_by, used_at, uses_count
```

### Flow
```
admin/teacher → POST /api/v1/admin/invites → создаёт code
                                                    ↓
friend → /register?code=ABC123 → валидирует invite
        ↓
        role override (для teacher invites)
        ↓
        register_user + invite.uses_count++
        ↓
        audit log (Sprint 47)
```

### Frontend
- `/invite/[code]` — landing page с preview
- `/register?code=...` — registration form с banner
- `/admin/invites` (Sprint 52) — admin management UI

---

## 🌍 i18n (Sprint 41)

### Architecture
- Client-side only (`useLocale()` hook)
- localStorage `'ai-tutor:locale'` for persistence
- Default `'ru'`, fallback to browser language

### Files
- `messages/ru.json` — Russian (source of truth, 38 keys)
- `messages/en.json` — English
- `lib/i18n.ts` — `t()` + `setLocale()`
- `components/LanguageSwitcher.tsx` — RU ↔ EN toggle

### Coverage
- Header, login, CGM page, PauseButton, SessionTimer

---

## 🌐 Multi-worker uvicorn (Sprint 30)

### Configuration
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Memory profile (4GB LXC)
- Workers 2: 690 MiB used
- Workers 4: **231 MiB** (5.64%) — снижение благодаря shared imports

### Multi-worker safety
- ✅ Rate-limit через Redis (atomic INCR)
- ✅ Audit log через Postgres (atomic)
- ✅ Alert queue через Redis list

---

## 📁 File Structure (Sprint 53 current)

```
apps/backend/app/
├── admin/           # Sprint 9: stats, audit, users. Sprint 45: hash chain + export.
├── auth/            # Sprint 10: login/JWT. Sprint 27: cookie. Sprint 32: 2FA.
├── bot/             # Sprint 16: telegram_bot. Sprint 50: alert_worker v2.
├── cgm/             # Sprint 40: Nightscout proxy (HTTPS-only, opt-in).
├── common/          # deps.py (require_role)
├── db/              # session, Base
├── diagnostics/     # CAT-adaptive testing
├── invites/         # Sprint 44: CRUD. Sprint 47: audit.
├── notifications/   # in-app + email
├── parents/         # Sprint 3: dashboard. Sprint 32: 2FA endpoints.
├── sessions/        # Sprint 34: T1D session pauses
├── student/         # Sprint 8: streak. Sprint 49: parent metrics hook.
├── subjects/        # 12 subjects × 186 topics × 42 subtopics
├── teacher/         # Sprint 35: search + bulk-approve
├── users/           # Sprint 16: profile. Sprint 32: twofa.py
├── v2/              # Sprint 10: secure exercises. Sprint 19: checkers.
├── voice/           # Sprint 2: Whisper
├── ai/              # gateway, sanitize, budget, websocket
├── rag.py, rag_router.py, rag_models.py, rag_persist.py
├── parent_metrics.py        # Sprint 49: parent dashboard metrics
├── observability.py         # Sprint 5: Prometheus middleware
├── config.py, main.py
└── scripts/         # CLI (seed, audit_cleanup, rag_benchmark)

apps/frontend/
├── app/
│   ├── admin/      # Sprint 52: /admin/invites management
│   ├── invite/[code]/page.tsx   # Sprint 44: landing page
│   ├── register/page.tsx        # Sprint 44: +invite code
│   ├── cgm/page.tsx             # Sprint 40: opt-in UI
│   └── topics/[id]/page.tsx     # Sprint 21-49: T1D UI
├── components/
│   ├── PauseButton.tsx, SessionTimer.tsx, RecoveryBadge.tsx
│   ├── CGMStatus.tsx, audio-cue.ts
│   ├── LanguageSwitcher.tsx     # Sprint 41
│   └── Header.tsx, ThemeToggle.tsx
├── lib/
│   ├── i18n.ts                  # Sprint 41
│   └── api.ts                   # cookie auth (Sprint 27)
├── messages/
│   ├── ru.json, en.json        # Sprint 41
└── e2e/                         # 18 Playwright specs
```

---

## 🎯 Migration history

| Migration | Описание | Sprint |
|---|---|---|
| 0014 | telegram_bindings (PG) | 16.0 |
| 0015 | exercise_checker_type | 19 |
| 0016 | parent_2fa | 32 |
| 0017 | session_pauses | 34 |
| 0018 | source_type_pdf fix | 36.1 |
| 0019 | cgm_config | 40 |
| 0020 | invites | 44 |
| 0021 | audit_hash_chain | 45 |

---

## 🔗 См. также

- [docs/security.md](security.md) — security model
- [docs/api.md](api.md) — API reference
- [docs/deployment.md](deployment.md) — production deployment
- [docs/CHANGELOG-SPRINT-16-46.md](CHANGELOG-SPRINT-16-46.md) — full changelog
- [docs/COVERAGE-REPORT.md](COVERAGE-REPORT.md) — test coverage (78%)
- [docs/RAG-BENCHMARK.md](RAG-BENCHMARK.md) — RAG evaluation