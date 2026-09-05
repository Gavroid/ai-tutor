# Next Stage 08 — Admin Monitoring Drill — 2026-08-17

## Scope

Stage 08 verified whether an operator can understand current AI-Tutor health from Prometheus and Admin Realtime without SSH. The stage used production read-only Prometheus/API probes first, then a targeted deploy for the Admin Realtime visibility gap found during the drill.

## Production Safety

Before production mutation, backup and offsite verification were run:

```text
cd /opt/ai-tutor/deploy/backup
./backup.sh
./ai-tutor-backup-offsite.sh
OFFSITE OK: hash verified manifest-20260817T122619Z.md5 (b163f4e50cc4535535bb37b1c946fa7c)
OFFSITE OK: 114 uploaded, 0 deleted, 199 total on SMB
```

Targeted deploy only:

- Synced `apps/backend/app/admin/realtime.py`.
- Synced `apps/frontend/app/admin/components.tsx`.
- Synced `apps/frontend/lib/admin-ws.ts`.
- Rebuilt/recreated only `backend` and `frontend` via Docker Compose.
- Did not run broad `rsync --delete`.
- Did not advance `.mvp-rescue-commit`; marker remains `6e698a0`.

## Prometheus Evidence

Production Prometheus is intentionally internal-only; host `127.0.0.1:9090` refused connection, so queries were executed read-only inside the Prometheus container.

### Rules API

```text
/api/v1/rules: status=success
rule group: ai_tutor_health
rules: 9
all rule health: ok
/api/v1/alerts: active_alerts=0
```

Rules reviewed:

- `AiTutorBackendDown`
- `AiTutorBackend5xx`
- `AiTutorUnexpected4xxSpike`
- `AiTutorLoginRateLimitSpike`
- `AiTutorReadyProbeFailing`
- `AiTutorDatabaseProbeDown`
- `AiTutorRedisProbeDown`
- `AiTutorUploadDiskHigh`
- `AiTutorBackupMissingOrStale`

### Query API

Post-deploy production query evidence:

```text
up{job="ai-tutor-backend"} = 1
max(ai_tutor_db_up) = 1
max(ai_tutor_redis_up) = 1
max(ai_tutor_upload_disk_used_percent) = 46.9151
min(ai_tutor_backup_latest_age_seconds) = 0
sum(rate(http_requests_total{status=~"5.."}[5m])) = no series
```

Earlier cumulative HTTP status counters showed no 5xx and only expected/manual 4xx noise:

```text
HTTP 200 = 439
HTTP 204 = 3
HTTP 401 = 5
HTTP 404 = 18
HTTP 5xx = 0
```

## Admin Realtime Finding And Fix

### Finding

Before the fix, Admin Realtime `_metrics_snapshot()` showed:

```json
"system": {
  "db": "unknown",
  "redis": "unknown",
  "backend": "unknown",
  "mem_used_mb": 689.3
}
```

Root cause: backend container cannot reliably inspect host Docker Compose state, so `_system_health()` returned `unknown` even while Prometheus app-level probes were healthy.

### Fix

Updated Admin Realtime to use app-level ops probes from `collect_ops_metrics()` instead of Docker Compose introspection:

- `db`: `ok/down` from `ai_tutor_db_up`.
- `redis`: `ok/down` from `ai_tutor_redis_up`.
- `backend`: `ok` if the snapshot endpoint itself is executing.
- `upload_disk_used_percent`: surfaced from backend `/metrics` probe.
- `backup_latest_age_seconds`: surfaced from backend `/metrics` probe.

Updated Admin Realtime UI to show dedicated KPI cards:

- `DB`
- `Redis`
- `Backup age`
- `Upload disk`

## Production Snapshot Evidence

Post-deploy backend internal snapshot:

```json
{
  "system": {
    "db": "ok",
    "redis": "ok",
    "backend": "ok",
    "upload_disk_used_percent": 46.9152,
    "backup_latest_age_seconds": 173.0785,
    "mem_used_mb": 596.3
  },
  "http_total": {
    "2xx": 0,
    "4xx": 0,
    "5xx": 0
  }
}
```

Production health after targeted deploy:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
backend/frontend/db/redis/prometheus healthy
grafana/proxy running
```

## 4xx Vs 5xx Operator Interpretation

- `5xx`: server-side defect or dependency failure. Treat as critical, check `/ready`, backend logs, DB/Redis probes, and recent deploys first.
- Expected `4xx`: normal product behavior, for example missing student draft `404` or unauthenticated admin snapshot probes.
- Unexpected `4xx`: investigate route/auth UX, broken frontend links, or stale client state. It is usually warning-level unless it blocks a pilot flow.
- `429`: login rate-limit spike; check whether manual QA/E2E runners are reusing accounts before treating as attack traffic.

## Local Verification

```text
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest tests/test_admin_realtime_stage08.py -q
2 passed, 3 warnings

.venv/bin/pytest tests/test_admin_realtime_stage08.py tests/test_ops_metrics.py tests/test_health.py -q
12 passed, 3 warnings
```

```text
cd /root/workspace/ai-tutor/apps/frontend
npx tsc --noEmit
exit 0

npx playwright test e2e/admin-realtime-stage08.spec.ts --project=chromium
1 passed

BASE_URL=https://192.168.1.86 npx playwright test e2e/admin-realtime-stage08.spec.ts --project=chromium
1 passed
```

## Done Criteria

- Prometheus rules API: complete.
- Prometheus query API for ops gauges: complete.
- Admin Realtime snapshot: complete and improved.
- Safe read-only alert checks: complete.
- Operator 4xx/5xx interpretation: documented.
- Backup/offsite before production mutation: complete.
- Targeted production deploy: complete.
- Report: complete.
- Commit: pending at report creation.
