#!/usr/bin/env bash
# Pilot Core Stage 1 — Phase 3 (P1.3.2).
# Rollback: восстанавливает tar с предыдущего deploy'а И image-снимок.
#
# Использование:
#   rollback.sh                       # использует /tmp/ai-tutor-prev-sha.txt от deploy.sh
#   rollback.sh <known-good-sha>       # восстанавливает по известному commit
#
# На production-хосте нет git (Phase 4 deferred), поэтому rollback
# использует /tmp/ai-tutor-prev-sha.txt как marker. Если marker отсутствует — отказ.
#
# Post-impl review: rollback.sh теперь проверяет /opt/ai-tutor/deploy/release/releases/
# на наличие images.tar (снимок docker-образов, сохранённый deploy.sh
# через docker save). Если images.tar есть — загружаем его обратно через
# docker load, чтобы image-слой тоже откатился. Если images.tar нет —
# fallback на rebuild из текущего workspace tar.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SSH_KEY="${SSH_KEY:-/root/.ssh/id_ed25519_kirill_ai}"
PROD_HOST="${PROD_HOST:-192.168.1.86}"
RELEASE_DIR="/opt/ai-tutor"
COMPOSE_DIR="$RELEASE_DIR/deploy"
RELEASES_DIR="$RELEASE_DIR/deploy/release/releases"

log() { printf '\033[1;34m[rollback]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[rollback FAIL]\033[0m %s\n' "$*"; exit 1; }

PREV_SHA="${1:-$(cat /tmp/ai-tutor-prev-sha.txt 2>/dev/null || echo)}"
if [ -z "$PREV_SHA" ]; then
  fail "не указан known-good SHA и нет /tmp/ai-tutor-prev-sha.txt"
fi

# Snapshot dir для PREV_SHA
PREV_DIR="$RELEASES_DIR/$PREV_SHA"
log "PREV_SHA=$PREV_SHA"
log "Snapshot dir: $PREV_DIR"

# 1) Image snapshot — если есть
if ssh -i "$SSH_KEY" root@"$PROD_HOST" "test -f $PREV_DIR/images.tar"; then
  log "Найден images.tar — восстанавливаем image-слой"
  ssh -i "$SSH_KEY" root@"$PROD_HOST" "docker load -i $PREV_DIR/images.tar" 2>&1 | tail -5
else
  log "images.tar не найден в $PREV_DIR — fallback на rebuild из текущего workspace"
  log "  ВНИМАНИЕ: image-слой НЕ откатывается. Если в новом image сломан entrypoint,"
  log "  rollback.sh не поможет; нужен ручной rebuild."
fi

# 2) DB restore из свежего backup
log "Поиск свежего backup на ${PROD_HOST}..."
BACKUP_FILE=$(ssh -i "$SSH_KEY" root@"$PROD_HOST" "ls -1t $RELEASE_DIR/deploy/backup/_out/db-*.sql.gz 2>/dev/null | head -1")
if [ -z "$BACKUP_FILE" ]; then
  fail "не найден backup-файл в $RELEASE_DIR/deploy/backup/_out/"
fi
log "  свежий backup: $BACKUP_FILE"

log "Восстановление БД..."
ssh -i "$SSH_KEY" root@"$PROD_HOST" "cd $COMPOSE_DIR && POSTGRES_USER=tutor POSTGRES_PASSWORD=\$(grep ^POSTGRES_PASSWORD= $RELEASE_DIR/.env | cut -d= -f2-) POSTGRES_DB=tutor bash ./backup/backup.sh --restore $BACKUP_FILE" 2>&1 | tail -3

# 3) Code restore — если в PREV_DIR есть tar с кодом, восстанавливаем
if ssh -i "$SSH_KEY" root@"$PROD_HOST" "test -f $PREV_DIR/code.tar.zst"; then
  log "Найден code.tar.zst — восстанавливаем код"
  ssh -i "$SSH_KEY" root@"$PROD_HOST" "tar --use-compress-program='zstd -d' -xf $PREV_DIR/code.tar.zst -C $RELEASE_DIR/"
else
  log "code.tar.zst не найден в $PREV_DIR — fallback на текущий workspace tar"
fi

# 4) Restart backend/frontend с откаченным image
log "Restart backend/frontend"
ssh -i "$SSH_KEY" root@"$PROD_HOST" "cd $COMPOSE_DIR && docker compose restart backend frontend" 2>&1 | tail -3

# 5) Update marker
log "Rollback до PREV_SHA=$PREV_SHA завершён"
echo "$PREV_SHA" > /tmp/ai-tutor-prev-sha.txt
log "OK: rollback выполнен"
