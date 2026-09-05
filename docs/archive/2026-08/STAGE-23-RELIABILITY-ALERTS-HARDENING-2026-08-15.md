# Stage 23 — Reliability And Alerts Hardening — 2026-08-15

## Scope

Stage 23 goal: ensure pilot failures are visible without SSH.

## Findings Before Fix

Prometheus was healthy and scraping backend, but alert coverage was incomplete for the stage requirements:

- Existing Prometheus alerts covered backend down, 5xx, unexpected 4xx, login 429, and readiness failures.
- DB and Redis were indirectly covered by `/ready`, but not exposed as standalone Prometheus probes.
- Backup age was only visible through host files/backup logs, not backend metrics.
- Disk alert existed in Grafana provisioning using `node_filesystem_*`, but no node-exporter target was configured, so it was not reliable.
- Admin Realtime snapshot worked, but system health returned `unknown` for DB/Redis because backend container cannot run host Docker Compose.

## Completed

- Added backend ops gauges exposed through `/metrics`:
  - `ai_tutor_db_up`;
  - `ai_tutor_redis_up`;
  - `ai_tutor_upload_disk_used_percent`;
  - `ai_tutor_backup_latest_age_seconds`.
- Mounted production backup output read-only into backend:
  - `./backup/_out:/app/ops/backup_out:ro`.
- Added `OPS_BACKUP_OUT_PATH=/app/ops/backup_out` to backend environment.
- Added Prometheus alerts:
  - `AiTutorDatabaseProbeDown`;
  - `AiTutorRedisProbeDown`;
  - `AiTutorUploadDiskHigh`;
  - `AiTutorBackupMissingOrStale`.
- Used `max(...)` in alert expressions to avoid false positives from stale multiprocess worker pid files.

## Files Changed

- `apps/backend/app/observability.py`
- `apps/backend/tests/test_ops_metrics.py`
- `deploy/docker-compose.yml`
- `deploy/prometheus/alerts.yml`

## TDD Evidence

RED before implementation:

```text
AttributeError: app.observability has no attribute '_probe_db'
AttributeError: app.observability has no attribute 'collect_ops_metrics'
```

GREEN after implementation:

```text
cd apps/backend
.venv/bin/pytest tests/test_ops_metrics.py tests/test_health.py -q
10 passed, 3 warnings
```

## Production Backup / Offsite

Required backup was run before production deploy:

```text
backup manifest: /opt/ai-tutor/deploy/backup/_out/manifest-20260815T094904Z.md5
OFFSITE OK: hash verified manifest-20260815T094904Z.md5
SMB total after upload: 226 files
```

## Production Deploy

Targeted deploy:

```text
docker compose build backend
docker compose up -d --no-deps backend prometheus
backend_health=healthy
prometheus_health=healthy
/ready HTTP=200
```

Prometheus was explicitly recreated after alert rule changes:

```text
docker compose up -d --force-recreate --no-deps prometheus
prometheus_health=healthy
```

## Production Verification

Prometheus rules API:

```text
rules_status success
AiTutorBackendDown inactive
AiTutorBackend5xx inactive
AiTutorUnexpected4xxSpike inactive
AiTutorLoginRateLimitSpike inactive
AiTutorReadyProbeFailing inactive
AiTutorDatabaseProbeDown inactive
AiTutorRedisProbeDown inactive
AiTutorUploadDiskHigh inactive
AiTutorBackupMissingOrStale inactive
missing []
```

Prometheus targets API:

```text
targets_status success
ai-tutor-backend up
prometheus up
```

Ops metrics from Prometheus query API:

```text
max(ai_tutor_db_up) = 1
max(ai_tutor_redis_up) = 1
max(ai_tutor_upload_disk_used_percent) = 46.4939
max(ai_tutor_backup_latest_age_seconds) = 397.4
```

Admin Realtime snapshot smoke:

```text
REALTIME_HTTP=200
http_total {'2xx': 27, '4xx': 1, '5xx': 0}
breakdown_len 1
```

Service health:

```text
backend healthy
prometheus healthy
db healthy
redis healthy
grafana running
/ready HTTP=200
```

## Alert Interpretation

| Alert | Meaning | First operator action |
|---|---|---|
| `AiTutorBackendDown` | Prometheus cannot scrape backend metrics | Check backend container and `/ready` |
| `AiTutorBackend5xx` | Backend emitted HTTP 5xx | Check backend logs and Admin Realtime breakdown |
| `AiTutorUnexpected4xxSpike` | Non-expected 4xx rate is high | Check login/auth/client paths in Realtime breakdown |
| `AiTutorReadyProbeFailing` | `/ready` returned non-200 | Check DB/Redis probes and backend startup |
| `AiTutorDatabaseProbeDown` | Backend cannot run DB `SELECT 1` | Check DB container/network and migrations |
| `AiTutorRedisProbeDown` | Backend cannot ping Redis | Check Redis container/network; rate limit/budget may be unsafe |
| `AiTutorUploadDiskHigh` | Upload filesystem >80% used | Clean old artifacts or expand storage |
| `AiTutorBackupMissingOrStale` | No visible backup or latest backup >26h | Check backup cron/offsite script immediately |

## Known Limitations

- Grafana is running and has provisioning, but some provisioning files are unreadable from inside the Grafana container shell due permissions; this did not block Prometheus/API verification.
- Admin Realtime system DB/Redis statuses may still show `unknown` because host Docker access is not available inside backend. Prometheus alerts are now the source of truth for DB/Redis visibility.

## Next Stage

Proceed to Stage 24 — Performance And Cost Review.
