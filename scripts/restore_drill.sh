#!/usr/bin/env bash
# restore_drill.sh — Sprint 75: periodic test restore с OFFSITE backup.
#
# Использует SMB offsite/ directory (post-Sprint 75: validated backups
# с size-verification, no 0-byte db.sql.gz).
#
# Использование:
#   ./scripts/restore_drill.sh              # auto-detect latest offsite backup
#
# Запускается monthly через cron.
# НЕ ТРОГАЕТ production DB! Восстанавливает в test container.

set -euo pipefail

SMB_HOST="192.168.1.91"
SMB_SHARE="Kirill-AI"
SMB_CREDS="/root/.ai-tutor-secrets/smb.creds"
SMB_BASE="ai-tutor/offsite"  # Sprint 75: validated backups

TEST_DB_NAME="tutor_restore_drill"
RESULTS_LOG="/var/log/ai-tutor-restore-drill.log"
LOCK_FILE="/tmp/ai-tutor-restore-drill.lock"
TEST_RESTORE_DIR=""
RESTORE_LOG=""
TEMP_CONTAINER=""

# ---- logging helper (defined early) ----
log() {
  local msg="[$(date -Iseconds)] [restore-drill] $*"
  echo "$msg"
  echo "$msg" >> "${RESULTS_LOG}"
}

cleanup() {
  if [[ -n "${TEMP_CONTAINER}" ]]; then
    docker rm -f "${TEMP_CONTAINER}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${TEST_RESTORE_DIR}" ]]; then
    rm -rf "${TEST_RESTORE_DIR}"
  fi
}
trap cleanup EXIT

# Avoid overlapping monthly/manual runs corrupting shared temp state.
exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  log "another restore drill is already running; exiting"
  exit 0
fi

TEST_RESTORE_DIR=$(mktemp -d /tmp/ai-tutor-restore-drill.XXXXXX)
RESTORE_LOG="${TEST_RESTORE_DIR}/restore.log"

# ---- pick latest backup ----
log "Sprint 75: restore drill started"

# Auto-detect: latest db-* file in offsite/
LATEST_DB=$(smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
  -c "cd ${SMB_BASE}; ls" 2>/dev/null | \
  grep -oE 'db-[0-9]{8}T[0-9]{6}Z\.sql\.gz' | sort -r | head -1)

if [[ -z "$LATEST_DB" ]]; then
  log "ERROR: no db backups found in ${SMB_BASE}"
  exit 1
fi

log "latest backup: $LATEST_DB"

# ---- download db dump ----
log "downloading $LATEST_DB..."
smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
  -c "cd ${SMB_BASE}; lcd $TEST_RESTORE_DIR; get ${LATEST_DB}" >/dev/null 2>&1

if [[ ! -s "$TEST_RESTORE_DIR/$LATEST_DB" ]]; then
  log "ERROR: download failed or empty"
  exit 1
fi

LOCAL_SIZE=$(stat -c '%s' "$TEST_RESTORE_DIR/$LATEST_DB")
log "downloaded: $LOCAL_SIZE bytes"

# ---- size sanity check ----
MIN_SIZE=100000  # 100KB (Sprint 75)
if [[ "$LOCAL_SIZE" -lt "$MIN_SIZE" ]]; then
  log "ERROR: downloaded file too small ($LOCAL_SIZE < $MIN_SIZE)"
  exit 1
fi

# ---- restore to temp postgres ----
log "creating temp postgres container..."
TEMP_CONTAINER=$(docker run -d --rm --name "restore_drill_$$" \
  -e POSTGRES_DB="$TEST_DB_NAME" \
  -e POSTGRES_USER=tutor \
  -e POSTGRES_PASSWORD=test \
  postgres:16-alpine 2>/dev/null)

# Wait for postgres ready (max 60 сек)
log "waiting for postgres ready..."
READY=0
for i in $(seq 1 60); do
  if docker exec "$TEMP_CONTAINER" psql -U tutor -d "$TEST_DB_NAME" -tA -c "SELECT 1" >/dev/null 2>&1; then
    log "postgres ready after ${i}s"
    READY=1
    break
  fi
  sleep 1
done
if [[ "$READY" -ne 1 ]]; then
  log "ERROR: postgres not ready after 60s"
  exit 1
fi

log "restoring dump..."
# Sprint 75: capture stderr, но не fail на warnings.
# Backup-offsite пишет с --no-owner --no-privileges, поэтому restore
# в test DB может иметь warnings (no such role, etc) — это OK.
# Sprint 75: postgres:16-alpine по умолчанию имеет trust auth для Unix socket.
# Используем -U tutor без password (peer auth через Unix user).
# -e PGPASSWORD=test НЕ работает с stdin pipe (psql confused).
if gunzip -c "$TEST_RESTORE_DIR/$LATEST_DB" 2>/dev/null | \
  docker exec -i "$TEMP_CONTAINER" psql -U tutor -d "$TEST_DB_NAME" -v ON_ERROR_STOP=0 >"$RESTORE_LOG" 2>&1; then
  log "✓ restore SUCCEEDED"
else
  log "✗ restore FAILED (see $RESTORE_LOG)"
  while IFS= read -r line; do log "$line"; done < <(tail -20 "$RESTORE_LOG")
  exit 1
fi

# ---- sanity check ----
TABLE_COUNT=$(docker exec "$TEMP_CONTAINER" psql -U tutor -d "$TEST_DB_NAME" \
  -tA -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")
log "table count: $TABLE_COUNT"

USER_COUNT=$(docker exec "$TEMP_CONTAINER" psql -U tutor -d "$TEST_DB_NAME" \
  -tA -c "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
log "user count: $USER_COUNT"

# ---- cleanup is handled by trap ----

# ---- summary ----
if [[ "$TABLE_COUNT" -gt 10 ]] && [[ "$USER_COUNT" -gt 0 ]]; then
  log "✓✓✓ RESTORE DRILL PASSED ✓✓✓"
  log "  Backup: $LATEST_DB"
  log "  Size: $LOCAL_SIZE bytes"
  log "  Tables: $TABLE_COUNT"
  log "  Users: $USER_COUNT"
  exit 0
else
  log "✗✗✗ RESTORE DRILL FAILED ✗✗✗"
  log "  Tables: $TABLE_COUNT (expected >10)"
  log "  Users: $USER_COUNT (expected >0)"
  exit 1
fi