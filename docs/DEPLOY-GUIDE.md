# AI-Tutor Production Deployment Guide

_Last updated: 2026-08-18_

Production target:

```text
Public: https://school.431a.ru
LAN:    https://192.168.1.86
Path:   /opt/ai-tutor
Compose:/opt/ai-tutor/deploy
```

Do not print `.env`, private keys, SMB credentials, JWTs, or passwords.

## Current production stack

```text
Docker Compose
  ├── backend     FastAPI / uvicorn workers=1
  ├── frontend    Next.js 16
  ├── db          PostgreSQL 16
  ├── redis       Redis
  ├── proxy       Nginx
  ├── prometheus  internal metrics scrape
  └── grafana     dashboards
```

Backend is intentionally `workers=1` until Prometheus multiprocess mode is implemented.

## Preflight

Local repo:

```bash
cd /root/workspace/ai-tutor
git status --short --branch
git log --oneline -8
```

Production health:

```bash
curl -sk -w '\nHTTP=%{http_code}\n' https://192.168.1.86/ready
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
  'cat /opt/ai-tutor/.mvp-rescue-commit; cd /opt/ai-tutor/deploy && docker compose ps'
```

## Backup before deploy

Run from production server:

```bash
cd /opt/ai-tutor/deploy/backup
./backup.sh
./ai-tutor-backup-offsite.sh
```

Expected local artifacts:

```text
/opt/ai-tutor/deploy/backup/_out/db-YYYYMMDDTHHMMSSZ.sql.gz
/opt/ai-tutor/deploy/backup/_out/uploads-YYYYMMDDTHHMMSSZ.tar.gz
/opt/ai-tutor/deploy/backup/_out/manifest-YYYYMMDDTHHMMSSZ.md5
```

Offsite verification must report hash verified. Do not expose SMB credentials.

## Restore drill

Safe restore drill uses an offsite DB backup and a temporary PostgreSQL container. It does **not** touch the production database.

Run from production server:

```bash
cd /opt/ai-tutor
scripts/restore_drill.sh
```

Expected success markers:

```text
RESTORE DRILL PASSED
Backup: db-YYYYMMDDTHHMMSSZ.sql.gz
Tables: >10
Users: >0
```

For a local backup file already present under `/opt/ai-tutor/deploy/backup/_out`, the older compose-based test restore is also safe because it restores to `tutor_test` and drops that test DB at the end:

```bash
cd /opt/ai-tutor/deploy/backup
./test-restore.sh /opt/ai-tutor/deploy/backup/_out/db-YYYYMMDDTHHMMSSZ.sql.gz
```

Never run `backup.sh --restore` against production without explicit approval; that path drops/recreates the production public schema.

## Frontend gates

```bash
cd /root/workspace/ai-tutor/apps/frontend
npm run typecheck
npm run build
```

## Backend gates

Small health gate:

```bash
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest tests/test_health.py -q
```

Use targeted tests for changed modules. Examples:

```bash
.venv/bin/pytest tests/test_parent_dashboard.py tests/test_health.py -q
.venv/bin/pytest tests/test_teacher.py -q
.venv/bin/pytest tests/test_ai_output_contract.py -q
```

## Deploy targeted changes

Production tree/marker hygiene is still handled conservatively. Prefer targeted syncs over broad deploys unless the production tree has been explicitly cleaned and verified.

Rules:

1. Run backup/offsite first.
2. Sync only changed runtime files.
3. Rebuild/recreate only affected services.
4. Verify `/ready`, `/health`, service status, and targeted browser/API smoke.
5. Do not advance `.mvp-rescue-commit` for ad-hoc targeted deploys unless the full marker advancement runbook was intentionally executed.

Backend-only example:

```bash
cd /root/workspace/ai-tutor
rsync -av -e 'ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes' \
  apps/backend/app/path/to/file.py \
  root@192.168.1.86:/opt/ai-tutor/apps/backend/app/path/to/file.py

ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 '
  cd /opt/ai-tutor/deploy
  docker compose build backend
  docker compose up -d --no-deps backend
  curl -sk -w "\nREADY_HTTP=%{http_code}\n" https://localhost/ready
  curl -sk -w "\nHEALTH_HTTP=%{http_code}\n" https://localhost/health
  docker compose ps backend
'
```

Frontend-only example:

```bash
cd /root/workspace/ai-tutor
rsync -av -e 'ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes' \
  apps/frontend/app/path/to/file.tsx \
  root@192.168.1.86:/opt/ai-tutor/apps/frontend/app/path/to/file.tsx

ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 '
  cd /opt/ai-tutor/deploy
  docker compose build frontend
  docker compose up -d --no-deps frontend
  curl -sk -w "\nREADY_HTTP=%{http_code}\n" https://localhost/ready
  docker compose ps frontend
'
```

## Deploy frontend-only changes

```bash
cd /root/workspace/ai-tutor
COMMIT=$(git rev-parse --short HEAD)

tar -cf - apps/frontend/<changed-files> \
  | ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
    'tar -xf - -C /opt/ai-tutor/'

ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 "
  set -e
  cd /opt/ai-tutor
  echo $COMMIT > .mvp-rescue-commit
  cd deploy
  docker compose build frontend
  docker compose up -d frontend
  for i in \$(seq 1 30); do
    code=\$(curl -sk -o /tmp/ready.body -w '%{http_code}' https://localhost/ready || true)
    body=\$(cat /tmp/ready.body 2>/dev/null || true)
    echo ready_http=\$code body=\$body
    if [ \"\$code\" = 200 ] && echo \"\$body\" | grep -q ready; then break; fi
    sleep 3
  done
  docker compose ps frontend
"
```

## Deploy backend + frontend changes

```bash
cd /root/workspace/ai-tutor
COMMIT=$(git rev-parse --short HEAD)

tar -cf - apps/backend/<changed-files> apps/frontend/<changed-files> \
  | ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
    'tar -xf - -C /opt/ai-tutor/'

ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 "
  set -e
  cd /opt/ai-tutor
  echo $COMMIT > .mvp-rescue-commit
  cd deploy
  docker compose build backend frontend
  docker compose up -d backend frontend
  for i in \$(seq 1 40); do
    code=\$(curl -sk -o /tmp/ready.body -w '%{http_code}' https://localhost/ready || true)
    body=\$(cat /tmp/ready.body 2>/dev/null || true)
    echo ready_http=\$code body=\$body
    if [ \"\$code\" = 200 ] && echo \"\$body\" | grep -q ready; then break; fi
    sleep 3
  done
  docker compose ps backend frontend
"
```

A short `502` during backend restart is expected only while containers are starting. Final `/ready` must return `HTTP=200`.

## Production smoke

```bash
curl -sk -w '\nHTTP=%{http_code}\n' https://192.168.1.86/ready
curl -sk -w '\nHTTP=%{http_code}\n' https://192.168.1.86/health
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 \
  'cd /opt/ai-tutor/deploy && docker compose ps backend frontend db redis prometheus'
```

For UI changes, run browser smoke on public domain:

```text
https://school.431a.ru
```

Required surfaces:

- `/subjects`
- `/subjects/[id]`
- `/topics/[id]`
- `/admin`
- `/teacher`
- `/parents`

## Admin/Reatime notes

Admin visible UI is one route:

```text
/admin
```

`/admin/invites` and `/admin/realtime` are compatibility redirects to `/admin`.

Realtime is fixed snapshot + manual refresh. It is not a live WebSocket stream in the current MVP UI. HTTP counters are cumulative since backend start.

## Disk cleanup runbook

Only run after backup.

Stage 1 — Docker build cache:

```bash
docker builder prune -af
```

Stage 2 — unused volumes:

```bash
docker volume ls -qf dangling=true | xargs -r docker volume inspect --format '{{.Name}} {{.Mountpoint}}'
docker volume prune -f
```

Stage 3 — unused images:

```bash
docker image prune -af
```

Stage 4 — journald:

```bash
journalctl --vacuum-size=100M
```

Never manually delete active Docker volumes for DB/uploads/Grafana/Prometheus.

## Rollback

Preferred rollback path:

1. Identify previous good git commit/marker.
2. Restore code from git or backup artifact.
3. Rebuild affected containers.
4. If DB changed, restore DB only from a known backup after explicit approval.
5. Verify `/ready`, `/health`, and core browser surfaces.

## Current follow-up work

See:

```text
docs/FURTHER-DEVELOPMENT-PLAN-2026-08-13.md
```
