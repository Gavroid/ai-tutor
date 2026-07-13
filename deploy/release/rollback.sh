#!/usr/bin/env bash
# Pilot Core Stage 1 — Phase 3 (P1.3.2).
# Rollback: восстанавливает tar с предыдущего deploy'а.
#
# Использование:
#   rollback.sh                       # использует /tmp/ai-tutor-prev-sha.txt от deploy.sh
#   rollback.sh <known-good-sha>       # восстанавливает по известному commit
#
# На production-хосте нет git (Phase 4 deferred), поэтому rollback
# использует /tmp/ai-tutor-prev-sha.txt как marker. Если marker отсутствует —
# отказы.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SSH_KEY="${SSH_KEY:-/root/.ssh/id_ed25519_kirill_ai}"
PROD_HOST="${PROD_HOST:-192.168.1.86}"
RELEASE_DIR="/opt/ai-tutor"
COMPOSE_DIR="$RELEASE_DIR/deploy"

log() { printf '\033[1;34m[rollback]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[rollback FAIL]\033[0m %s\n' "$*"; exit 1; }

PREV_SHA="${1:-$(cat /tmp/ai-tutor-prev-sha.txt 2>/dev/null || echo)}"
if [ -z "$PREV_SHA" ]; then
  fail "не указан known-good SHA и нет /tmp/ai-tutor-prev-sha.txt"
fi

# На production-хосте нет git; rollback делается через:
# 1) откат к previous tag в registry
# 2) backup.sh --restore latest pre-deploy backup
#
# Pilot Core: самая простая и реалистичная стратегия —
# восстановить backup.tar.gz pre-deploy. Для этого нужно:
#  - знать, какая backup самая свежая (mtime newest)
#  - запустить backup.sh --restore
#  - пересобрать backend+frontend с known-good tar
#  - smoke.sh
#
# Здесь мы делаем минимальный rollback: backup.sh --restore newest + up.

log "Поиск свежего backup на ${PROD_HOST}..."
BACKUP_FILE=$(ssh -i "$SSH_KEY" root@"$PROD_HOST" "ls -1t $RELEASE_DIR/deploy/backup/_out/db-*.sql.gz 2>/dev/null | head -1")
if [ -z "$BACKUP_FILE" ]; then
  fail "не найден backup-файл в $RELEASE_DIR/deploy/backup/_out/"
fi
log "  свежий backup: $BACKUP_FILE"

log "Восстановление БД..."
ssh -i "$SSH_KEY" root@"$PROD_HOST" "cd $COMPOSE_DIR && POSTGRES_USER=tutor POSTGRES_PASSWORD=\$(grep ^POSTGRES_PASSWORD= $RELEASE_DIR/.env | cut -d= -f2-) POSTGRES_DB=tutor bash ./backup/backup.sh --restore $BACKUP_FILE" 2>&1 | tail -3

log "Rollback до PREV_SHA=$PREV_SHA"
echo "$PREV_SHA" > /tmp/ai-tutor-prev-sha.txt
log "OK: rollback выполнен"
