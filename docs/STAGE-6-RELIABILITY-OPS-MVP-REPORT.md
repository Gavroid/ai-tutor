# Stage 6 Reliability / Ops Hardening MVP Report

Date: 2026-08-11
Branch: `mvp-rescue`
Current production marker: `8a14fac`

## Result

Stage 6 — **Reliability / Ops Hardening MVP** is complete for manual MVP testing.

The production app now has a working admin-only ops preflight endpoint, per-client auth rate limiting behind the proxy, validated backup/offsite visibility, reduced disk pressure, and a passing restore drill.

## Completed Scope

### Auth / Proxy Reliability

- Fixed production login/register rate-limit keying so trusted Docker proxy traffic uses the forwarded client IP instead of the proxy container IP.
- Deployed in commit `7f17646` (`fix: trust proxy network for auth rate limits`).
- Production backend env now uses `TRUSTED_PROXIES=172.19.0.0/16`.

### Ops Preflight Endpoint

Endpoint:

```text
GET /api/v1/admin/ops/status
```

Access:

- admin only;
- unauthenticated/non-admin users are rejected by existing RBAC.

The endpoint returns:

- overall `ok`;
- `checked_at` timestamp;
- `environment`;
- checks for database, Redis, uploads, teacher content registry, backup cron/script, and deployed commit marker.

Stage 6 fix:

- Fixed hardcoded host paths inside the backend container.
- Added env-configurable paths:
  - `OPS_COMMIT_MARKER_PATH=/app/.mvp-rescue-commit`
  - `OPS_BACKUP_SCRIPT_PATH=/app/ops/backup.sh`
  - `OPS_BACKUP_CRON_PATH=/app/ops/ai-tutor-backup`
- Mounted the production marker, backup script, and authoritative backup cron read-only into the backend container.
- Added auditable path fields in the endpoint response.
- Deployed in commit `6f74300` (`fix: align ops preflight with container-visible paths`).

Production verification outcome:

```json
{
  "ok": true,
  "database_ok": true,
  "redis_ok": true,
  "backup": {
    "cron_exists": true,
    "cron_path": "/app/ops/ai-tutor-backup",
    "script_exists": true,
    "script_path": "/app/ops/backup.sh"
  },
  "commit_marker": {
    "ok": true,
    "path": "/app/.mvp-rescue-commit",
    "commit": "6f74300"
  }
}
```

After the restore-drill fix, the production marker was advanced to `8a14fac`; the endpoint should now report that marker value.

### Disk Cleanup

Safe cleanup performed:

```bash
docker builder prune -f --filter until=24h
```

Observed production disk improvement:

- before cleanup: `/dev/loop2 49G 36G 11G 77% /`
- after cleanup: `/dev/loop2 49G 29G 19G 62% /`
- reclaimed build cache reported by Docker: `7.559GB`

No Docker volumes or runtime images were blindly removed.

### Backup / Offsite / Restore Drill

Backup/offsite status before fixes:

- authoritative backup cron exists at `/etc/cron.d/ai-tutor-backup`;
- backup verify cron exists at `/etc/cron.d/ai-tutor-backup-verify`;
- latest daily offsite backup was visible in prior logs;
- weekly verify had succeeded, but monthly restore drill had repeated failures.

Restore drill root causes found:

- cron line used `30 4 1-7 * 1`, which cron treats as DOM/DOW OR semantics, causing more runs than intended;
- restore script wrote to a shared `/tmp/restore_drill.log` and shared restore directory;
- script lacked a lock/trap, leaving a stale `restore_drill_486394` container running for 9 days;
- readiness used `pg_isready`, which raced against the Postgres image's init/restart window and produced `database system is shutting down` during restore.

Fix deployed in commit `8a14fac` (`fix: harden restore drill scheduling and readiness`):

- first-Monday cron guard: `30 4 * * 1 root test "$(date +\%d)" -le 07 && /opt/ai-tutor/scripts/restore_drill.sh >/dev/null 2>&1`;
- non-overlap guard via `flock -n`;
- per-run `mktemp` restore directory and per-run restore log;
- `trap cleanup EXIT` to remove temp Postgres container and temp files;
- readiness now waits for `psql -U tutor -d "$TEST_DB_NAME" -tA -c "SELECT 1"` against the target DB.

Manual restore drill verification on production:

```text
[2026-08-11T15:12:01+00:00] [restore-drill] ✓ restore SUCCEEDED
[2026-08-11T15:12:01+00:00] [restore-drill] table count: 32
[2026-08-11T15:12:01+00:00] [restore-drill] user count: 14
[2026-08-11T15:12:01+00:00] [restore-drill] ✓✓✓ RESTORE DRILL PASSED ✓✓✓
[2026-08-11T15:12:01+00:00] [restore-drill]   Backup: db-20260811T030001Z.sql.gz
[2026-08-11T15:12:01+00:00] [restore-drill]   Size: 12715463 bytes
```

No `restore_drill_*` containers remained after the passing run.

## Verification Commands And Outcomes

Local RED/GREEN evidence:

```bash
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest tests/test_stage6_ops_status.py::test_ops_status_uses_configurable_backup_and_marker_paths -q
# RED before fix: failed on checks["backup"]["cron_exists"] is False

.venv/bin/pytest tests/test_stage6_ops_status.py -q
# 3 passed

.venv/bin/pytest tests/test_techdebt.py::test_client_ip_trusted_proxy_uses_xff tests/test_techdebt.py::test_client_ip_untrusted_peer_ignores_xff -q
# 2 passed

bash -n scripts/restore_drill.sh
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest tests/test_sprint6_cron_env.py::test_restore_drill_cron_runs_first_monday_only tests/test_sprint6_cron_env.py::test_restore_drill_script_uses_lock_and_isolated_temp_files -q
# 2 passed
```

Production deploy/smoke evidence:

```bash
curl -sk -w '\nHTTP=%{http_code}\n' https://localhost/ready
# {"status":"ready"}
# HTTP=200

curl -sk -w '\nHTTP=%{http_code}\n' https://localhost/health
# {"status":"ok", ... "env":"production", ...}
# HTTP=200

docker compose ps
# backend, db, frontend, redis healthy; proxy/grafana running

Authenticated admin request to `/api/v1/admin/ops/status`
# ok=true, database_ok=true, redis_ok=true, backup cron/script true, commit_marker ok=true
```

## Known Limitations

- The ops endpoint is a one-shot preflight for manual MVP testing, not a full alerting system.
- Prometheus/Grafana remain the dedicated observability layer.
- Old duplicate restore-drill log entries remain in historical logs, but the current script no longer double-writes new lines.

## Recommended Manual Checks

- Login as admin and open the admin/ops status surface if exposed in UI.
- Confirm parent/student Stage 5 flows still load after the backend restart.
- Let the next scheduled backup verify and first-Monday restore drill run naturally, then compare logs against the manual passing run above.
