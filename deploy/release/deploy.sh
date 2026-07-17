#!/usr/bin/env bash
# Pilot Core Stage 1 — Phase 3 (P1.3.2).
# Atomic deploy: tar-pipe нового кода, build, up, ждать healthcheck.
#
# Использование:
#   deploy.sh                  # использует текущий HEAD
#   deploy.sh <commit-sha>     # деплоит указанный commit (проверяется в preflight)
#
# Возвращает non-zero exit, если что-то пошло не так; rollback.sh
# восстанавливает предыдущий tar + image-snapshot.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
log() { printf '\033[1;34m[deploy]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[deploy FAIL]\033[0m %s\n' "$*"; exit 1; }

SSH_KEY="${SSH_KEY:-/root/.ssh/id_ed25519_kirill_ai}"
# Sprint 3.5.3: если deploy.sh запускается с самого прода (self-hosted runner),
# не нужен ssh — выполнение локальное. Детект по hostname или runner.
LOCAL_DEPLOY=false
if [ "$(hostname)" = "Kirill-AI" ] || [ -f /opt/actions-runner/.runner ]; then
  LOCAL_DEPLOY=true
  log "LOCAL DEPLOY mode (no ssh) — runner или hostname = prod"
fi
PROD_HOST="${PROD_HOST:-192.168.1.86}"
RELEASE_DIR="/opt/ai-tutor"
COMPOSE_DIR="$RELEASE_DIR/deploy"

# Sprint 3.5.3: helper для запуска команды на проде.
# Если LOCAL_DEPLOY=true (self-hosted runner) — выполняем локально.
# Иначе — через ssh с приватным ключом.
run_on_prod() {
  if [ "$LOCAL_DEPLOY" = "true" ]; then
    bash -c "$1"
  else
    ssh -i "$SSH_KEY" root@"$PROD_HOST" "$1"
  fi
}

ACT="$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo local)"
TARGET_SHA="${1:-}"
if [ -n "$TARGET_SHA" ]; then
  if [ "$ACT" != "${TARGET_SHA:0:7}" ]; then
    fail "локальный HEAD=$ACT, а в deploy.sh передан ${TARGET_SHA:0:7}"
  fi
fi

# 1) pre-flight
log "1) preflight"
bash "$SCRIPT_DIR/preflight.sh" ${TARGET_SHA:+"$TARGET_SHA"}

# 2) Backup
log "2) backup"
run_on_prod "cd $COMPOSE_DIR && POSTGRES_USER=tutor POSTGRES_PASSWORD=\$(grep ^POSTGRES_PASSWORD= $RELEASE_DIR/.env | cut -d= -f2-) POSTGRES_DB=tutor bash ./backup/backup.sh" 2>&1 | tail -3

# 3) Save current release metadata
log "3) snapshot prev release"
PREV_SHA=$(run_on_prod "cat /tmp/ai-tutor-current-release-id 2>/dev/null || echo unknown" 2>/dev/null || echo unknown)
echo "$PREV_SHA" > /tmp/ai-tutor-prev-sha.txt
log "  prev=$PREV_SHA"

# 4) tar-pipe
log "4) tar-pipe code"
cd "$PROJECT_ROOT"
tar -cf - --exclude=node_modules --exclude=.next --exclude=.venv --exclude=__pycache__ \
  --exclude=.git --exclude=.hermes --exclude=deploy/backup/_out \
  --exclude='*.pyc' \
  apps/backend/app apps/backend/alembic/versions apps/backend/tests apps/backend/scripts \
  apps/frontend/app apps/frontend/lib apps/frontend/components \
  deploy/release deploy/backup/backup.sh deploy/backup/test-restore.sh \
  deploy/backup/ai-tutor-backup-offsite.sh \
  deploy/cron \
  deploy/docker-compose.yml deploy/nginx/nginx.conf \
  deploy/monitoring deploy/smtp \
  docs/security.md docs/pilot-baseline.md docs/deployment.md .env.example 2>/dev/null | \
  run_on_prod "tar -xf - -C $RELEASE_DIR/"

# 5) build
log "5) docker compose build"
run_on_prod "cd $COMPOSE_DIR && docker compose build backend frontend" 2>&1 | tail -3

# 6) up
log "6) docker compose up -d"
run_on_prod "cd $COMPOSE_DIR && docker compose up -d" 2>&1 | tail -5

# 7) Wait for health
log "7) ждём /health (до 90 сек)..."
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18; do
  sleep 5
  HEALTH=$(run_on_prod 'curl -sk -o /dev/null -w "%{http_code}" https://localhost/health' 2>/dev/null || echo 000)
  if [ "$HEALTH" = "200" ]; then
    log "  /health=200 после ${i}*5 сек"
    break
  fi
  log "  /health=$HEALTH (попытка $i)"
  if [ "$i" = "18" ]; then fail "/health не поднялся за 90 сек"; fi
done

# 8) Apply migrations (no heredoc — single ssh with env-vars)
log "8) alembic upgrade head"
APP_SECRET_KEY=$(run_on_prod "grep ^APP_SECRET_KEY= $RELEASE_DIR/.env | cut -d= -f2-")
POSTGRES_PASSWORD=$(run_on_prod "grep ^POSTGRES_PASSWORD= $RELEASE_DIR/.env | cut -d= -f2-")
run_on_prod "docker exec -u root deploy-backend-1 env APP_SECRET_KEY='$APP_SECRET_KEY' DATABASE_URL='postgresql+psycopg2://tutor:$POSTGRES_PASSWORD@db:5432/tutor' python3 -m alembic upgrade head" 2>&1 | tail -3

# 9) Snapshot image-слой + code для rollback (post-impl review)
# ПЕРЕД созданием: удаляем ВСЕ старые snapshots (чтобы освободить диск).
# Без этого /opt/ai-tutor/deploy/release/releases/ + /var/lib/docker
# разрастаются бесконтрольно (9.8 ГБ на 11 snapshots → диск 100%) и приводят
# к "No space left on device" (замечено Sprint 3.0). Retention применяется
# ПОСЛЕ создания нового — иначе formula оставляет N+1 снапшотов.
RELEASE_ID="$(date -u +%Y%m%dT%H%M%SZ)-${ACT}"
SNAPSHOT_DIR="/opt/ai-tutor/deploy/release/releases/$RELEASE_ID"
log "9) snapshot image+code: $SNAPSHOT_DIR"
run_on_prod "set -eu; cd /opt/ai-tutor/deploy/release/releases/ && ls -t | tail -n +1 | xargs -r rm -rf {}; ls -la / | grep -E '^/' | head -3" 2>&1 | tail -3
run_on_prod "set -eu; mkdir -p $SNAPSHOT_DIR && cd $COMPOSE_DIR && docker save -o $SNAPSHOT_DIR/images.tar deploy-backend deploy-frontend && echo $RELEASE_ID > $SNAPSHOT_DIR/release-id && echo $RELEASE_ID > /tmp/ai-tutor-current-release-id && ls -la $SNAPSHOT_DIR" 2>&1 | tail -5

# Code snapshot (отдельной командой — pipe tar | zstd не работает в heredoc с bash -s)
run_on_prod "set -eu; cd $RELEASE_DIR; tar --exclude=node_modules --exclude=.next --exclude=.venv --exclude=__pycache__ --exclude=.git --exclude=.hermes --exclude=deploy/backup/_out -cf - apps deploy 2>/dev/null | zstd -3 > $SNAPSHOT_DIR/code.tar.zst; ls -la $SNAPSHOT_DIR/code.tar.zst" 2>&1 | tail -3

# После создания — retention (по умолчанию оставляем 1 для rollback)
RELEASE_RETENTION=${RELEASE_RETENTION:-1}
run_on_prod "set -eu; cd /opt/ai-tutor/deploy/release/releases/ && ls -t | tail -n +$((RELEASE_RETENTION + 1)) | xargs -r rm -rf {}; echo \"releases после retention ($RELEASE_RETENTION): \"; ls -1 | head -10" 2>&1 | tail -5

# После успешного snapshot — почистить старые docker layers
run_on_prod "docker image prune -f --filter 'until=24h' 2>&1 | tail -2" 2>&1 | tail -3

log "OK: deploy завершён (prev=$PREV_SHA, release=$RELEASE_ID)"
