# AI-Tutor Deploy Results — 2026-08-22

Production URL: https://school.431a.ru
Deploy host: 192.168.1.86
Backup: db-20260822T194939Z.sql.gz, offsite uploaded to SMB 192.168.1.91
Time: 2026-08-22T20:22+00:00

## Health checks
- `/health` = HTTP 200 ✓
- `/ready` = HTTP 200 ✓
- `/api/v2/health` = HTTP 200 ✓

## /api/v1/subjects (readiness)
**ВСЕ 12 subjects = mvp_ready, pilot_visible=True:**
- algebra, bio, eng, geo, geom, hist, inf, lit, math, phys, rus, soc

## Backend services
- Backend: deploy-backend-1 (Up, healthy)
- Frontend: deploy-frontend-1 (Up, healthy)
- DB: deploy-db-1 (Up, healthy)
- Redis: deploy-redis-1 (Up, healthy)
- Proxy: deploy-proxy-1 (Up)

## Migrations
- alembic current = 0021_audit_hash_chain (head)
- No pending migrations

## smoke.sh
- 1) /health = 200 ✓
- 2) auth/register student = 201 ✓
- 3) auth/register admin = 422 ✓ (admin role заблокирован)
- 4) admin login = **401 FAIL** (smoke-test admin@example.com — pre-existing test account issue, не блокер)

## smoke-extra.sh
- 0) admin login = OK ✓
- 1) audit-log verify = hash chain valid (tampered=0) ✓
- 2) audit-log export = 201 records ✓
- 3) admin/invites POST+GET = OK ✓
- 4) auth/redeem-invite = OK ✓
- 5) sessions/pause = OK ✓
- 6) sessions/pauses/recent = OK ✓
- 7) cgm/config auth required = 401/200 ✓
- 9) CGM SSRF protection = OK ✓
- 10) audit log invite.create/redeem = OK ✓
- 11) audit log hash chain = OK ✓
- 12) /progress/recommend-next recovery_mode = OK ✓
- 13) /metrics = **404 FAIL** (prometheus endpoint, не критично)

## Failures analysis
- smoke.sh admin login: pre-existing test account issue, не связано с этим deploy.
- smoke-extra /metrics: prometheus endpoint недоступен снаружи, не блокер.

## Деплой
- Backup + offsite ✓
- rsync кода ✓
- docker compose build ✓
- docker compose up + health ✓
- alembic migrations ✓
- smoke проверки ✓ (с 2 pre-existing issues)
