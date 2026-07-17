#!/bin/bash
# Sprint 3.6.1 — еженедельная верификация backup через test-restore.

set -e
set -o pipefail

ENV_FILE="/opt/ai-tutor/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE не найден"
  exit 1
fi
set -a
source "$ENV_FILE"
set +a

BACKUP_DIR_LOCAL="/opt/ai-tutor/deploy/backup/_out"
BACKUP_DIR_OLD="/var/backups/ai-tutor"
LOG="/var/log/ai-tutor-backup-verify.log"

BACKUP=""
if [ -d "$BACKUP_DIR_LOCAL" ] && ls "$BACKUP_DIR_LOCAL"/db-*.sql.gz >/dev/null 2>&1; then
  BACKUP=$(ls -1t "$BACKUP_DIR_LOCAL"/db-*.sql.gz | head -1)
fi
if [ -z "$BACKUP" ] && [ -d "$BACKUP_DIR_OLD" ] && ls "$BACKUP_DIR_OLD"/db-*.sql.gz >/dev/null 2>&1; then
  BACKUP=$(ls -1t "$BACKUP_DIR_OLD"/db-*.sql.gz | head -1)
fi

if [ -z "$BACKUP" ]; then
  MSG="Backup verify FAIL: backup не найден в $BACKUP_DIR_LOCAL или $BACKUP_DIR_OLD"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $MSG" | tee -a "$LOG"
  if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    curl -sf -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d "chat_id=${TELEGRAM_CHAT_ID}" -d "text=$MSG" -o /dev/null || true
  fi
  exit 1
fi

BACKUP_AGE_H=$(( ( $(date -u +%s) - $(stat -c %Y "$BACKUP") ) / 3600 ))
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Тестирую backup: $BACKUP (age: ${BACKUP_AGE_H}h)"

if ! bash /opt/ai-tutor/deploy/backup/test-restore.sh "$BACKUP" 2>&1 | tee -a "$LOG"; then
  MSG="Backup verify FAIL: test-restore не прошёл для $BACKUP. Лог: $LOG"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $MSG" | tee -a "$LOG"
  if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    curl -sf -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d "chat_id=${TELEGRAM_CHAT_ID}" -d "text=$MSG" -o /dev/null || true
  fi
  exit 1
fi

MSG="Backup verify OK: $BACKUP (age: ${BACKUP_AGE_H}h)"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $MSG" | tee -a "$LOG"
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
  curl -sf -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" -d "text=$MSG" -o /dev/null || true
fi
exit 0
