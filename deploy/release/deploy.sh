#!/usr/bin/env bash
# Pilot Core Stage 1 — Phase 3 (P1.3.2).
# Atomic deploy: tar-pipe нового кода, build, up, ждать healthcheck.
#
# Использование:
#   deploy.sh                  # использует текущий HEAD
#   deploy.sh <commit-sha>     # деплоит указанный commit (проверяется в preflight)
#
# Возвращает non-zero exit, если что-то пошло не так; rollback.sh
# восстанавливает предыдущий tar.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SSH_KEY="${SSH_KEY:-/root/.ssh/id_ed25519_kirill_ai}"
PROD_HOST="${PROD_HOST:-192.168.1.86}"
RELEASE_DIR="/opt/ai-tutor"
COMPOSE_DIR="$RELEASE_DIR/deploy"

log() { printf '\033[1;34m[deploy]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[deploy FAIL]\033[0m %s\n' "$*"; exit 1; }

TARGET_SHA="${1:-}"
if [ -n "$TARGET_SHA" ]; then
  ACT=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD)
  if [ "$ACT" != "${TARGET_SHA:0:7}" ]; then
    fail "локальный HEAD=$ACT, а в deploy.sh передан ${TARGET_SHA:0:7}; checkout в нужный commit или не передавай аргумент"
  fi
fi

# 1) pre-flight
log "1) preflight"
bash "$SCRIPT_DIR/preflight.sh" ${TARGET_SHA:+"$TARGET_SHA"}

# 2) Backup
log "2) backup"
ssh -i "$SSH_KEY" root@"$PROD_HOST" "cd $COMPOSE_DIR && POSTGRES_USER=tutor POSTGRES_PASSWORD=\$(grep ^POSTGRES_PASSWORD= $RELEASE_DIR/.env | cut -d= -f2-) POSTGRES_DB=tutor bash ./backup/backup.sh" 2>&1 | tail -3

# 3) Save current release metadata
log "3) snapshot prev release"
PREV_SHA=$(ssh -i "$SSH_KEY" root@"$PROD_HOST" \
  "cd $RELEASE_DIR && (test -d .git && git rev-parse --short HEAD) || echo unknown" 2>/dev/null || echo unknown)
echo "$PREV_SHA" > /tmp/ai-tutor-prev-sha.txt
log "  prev=$PREV_SHA"

# 4) tar-pipe
log "4) tar-pipe code"
cd "$PROJECT_ROOT"
tar -cf - --exclude=node_modules --exclude=.next --exclude=.venv --exclude=__pycache__ \
  --exclude=.git --exclude=.hermes --exclude=deploy/backup/_out \
  --exclude='*.pyc' \
  apps/backend/app apps/backend/alembic/versions apps/backend/tests \
  apps/frontend/app apps/frontend/lib apps/frontend/components \
  deploy/release deploy/backup/backup.sh deploy/backup/test-restore.sh \
  deploy/backup/ai-tutor-backup-offsite.sh \
  deploy/docker-compose.yml deploy/nginx/nginx.conf \
  deploy/monitoring deploy/smtp \
  docs/security.md docs/pilot-baseline.md docs/deployment.md .env.example 2>/dev/null | \
  ssh -i "$SSH_KEY" root@"$PROD_HOST" "tar -xf - -C $RELEASE_DIR/"

# 5) build
log "5) docker compose build"
ssh -i "$SSH_KEY" root@"$PROD_HOST" "cd $COMPOSE_DIR && docker compose build backend frontend" 2>&1 | tail -3

# 6) up
log "6) docker compose up -d"
ssh -i "$SSH_KEY" root@"$PROD_HOST" "cd $COMPOSE_DIR && docker compose up -d" 2>&1 | tail -5

# 7) Wait for health
log "7) ждём /health (до 90 сек)..."
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18; do
  sleep 5
  HEALTH=$(ssh -i "$SSH_KEY" root@"$PROD_HOST" 'curl -sk -o /dev/null -w "%{http_code}" https://localhost/health' 2>/dev/null || echo 000)
  if [ "$HEALTH" = "200" ]; then
    log "  /health=200 после ${i}*5 сек"
    break
  fi
  log "  /health=$HEALTH (попытка $i)"
  if [ "$i" = "18" ]; then fail "/health не поднялся за 90 сек"; fi
done

# 8) Apply migrations (only if there are pending heads)
log "8) alembic upgrade head (если есть pending)"
APP_SECRET_KEY=$(ssh -i "$SSH_KEY" root@"$PROD_HOST" "grep ^APP_SECRET_KEY= $RELEASE_DIR/.env | cut -d= -f2-")
DATABASE_URL="postgresql+psycopg2://tutor:$(ssh -i "$SSH_KEY" root@"$PROD_HOST" "grep ^POSTGRES_PASSWORD= $RELEASE_DIR/.env | cut -d= -f2-")@db:5432/tutor"
ssh -i "$SSH_KEY" root@"$PROD_HOST" "cd $RELEASE_DIR && docker exec -u root deploy-backend-1 bash -c \"
  APP_SECRET_KEY='$APP_SECRET_KEY' \
  DATABASE_URL='$DATABASE_URL' \
  python3 -m alembic upgrade head\"" 2>&1 | tail -3

log "OK: deploy завершён (prev=$PREV_SHA)"
