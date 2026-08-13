# AI-Tutor Ops and Disk Hygiene Runbook

_Last updated: 2026-08-13_

Use this runbook after a confirmed full backup. Never delete production data volumes by hand.

## Safety Rules

1. Run DB/uploads backup first.
2. Verify offsite backup hash.
3. Do not manually delete files under `/var/lib/docker/volumes`.
4. Use Docker commands for Docker cleanup.
5. Re-check services and `/ready` after cleanup.

## Current Safe Cleanup Stages

### Stage 1 — Docker Build Cache

```bash
docker builder prune -af
```

Risk: low.
Effect: removes rebuild cache only. Future builds are slower.

### Stage 2 — Dangling Docker Volumes

Inspect first:

```bash
docker volume ls -qf dangling=true | xargs -r docker volume inspect --format '{{.Name}} {{.Mountpoint}}'
```

Then prune:

```bash
docker volume prune -f
```

Risk: medium-low. Docker removes only unused volumes, but inspect the list first.

### Stage 3 — Unused Images

```bash
docker image prune -af
```

Risk: medium. Runtime containers stay up, but rollback via old image layers is no longer available.

### Stage 4 — Journald

```bash
journalctl --vacuum-size=100M
```

Risk: low. Keeps recent logs only.

### Stage 5 — Local Backup Retention

Keep at least:

- last 3 local DB backups;
- last 3 local uploads backups;
- matching manifests;
- latest known restore-drill backup;
- all offsite copies until retention confirms remote health.

Suggested inspect command:

```bash
cd /opt/ai-tutor/deploy/backup/_out
ls -1t manifest-*.md5 db-*.sql.gz uploads-*.tar.gz | sed -n '1,60p'
```

Do not automate deletion here until offsite status is confirmed.

## Never Delete Manually

- PostgreSQL active volume.
- Uploads active volume.
- Grafana/Prometheus active volumes.
- `/opt/ai-tutor/.env`.
- `/root/.ai-tutor-secrets/*`.
- `/opt/ai-tutor/deploy/backup/_out` wholesale.

## Post-Cleanup Verification

```bash
df -hT /
docker system df
cd /opt/ai-tutor/deploy && docker compose ps backend frontend db redis prometheus
curl -sk -w '\nHTTP=%{http_code}\n' https://localhost/ready
```

Expected:

- `/ready` returns `HTTP=200` and `{"status":"ready"}`.
- backend/frontend/db/redis/prometheus healthy.
- Docker build cache may be `0B` after Stage 1.
- Docker volumes/images reclaimable should be `0B` after Stages 2–3.

## Restore Boundary

If cleanup accidentally removes required runtime data, restore from the latest verified DB/uploads backup and matching code marker. Do not attempt manual reconstruction of Docker volumes.


## Read-Only Disk Report

Use this before cleanup to inspect disk state without deleting anything:

```bash
/opt/ai-tutor/deploy/ops/disk-report.sh
```

It reports:

- filesystem usage;
- Docker reclaimable space;
- largest `/opt` entries;
- local backup directory size and latest manifests;
- dangling Docker volumes to inspect before prune;
- journald usage;
- AI-Tutor service status.

This script is safe to run anytime: it performs no deletion and no service restart.
