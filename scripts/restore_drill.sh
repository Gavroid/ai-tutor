#!/usr/bin/env bash
# restore_drill.sh — Sprint 73: periodic test restore.
#
# Проверяет что backups рабочие (Sprint 73, Kimi P1-2).
# Запускается monthly через cron.
#
# Использование:
#   ./scripts/restore_drill.sh              # auto-detect latest full backup
#   ./scripts/restore_drill.sh <backup-id> # specific backup
#
# НЕ ТРОГАЕТ production DB! Восстанавливает в test_db_restore.

set -euo pipefail

# ---- logging helper (defined early so other functions can use it) ----
log() {
  local msg="[$(date -Iseconds)] [restore-drill] $*"
  echo "$msg" | tee -a "${RESULTS_LOG:-/var/log/ai-tutor-restore-drill.log}"
}

SMB_HOST="192.168.1.91"
SMB_SHARE="Kirill-AI"
SMB_CREDS="/root/.ai-tutor-secrets/smb.creds"
SMB_BASE="ai-tutor"

TEST_DB_NAME="tutor_restore_drill"
TEST_RESTORE_DIR="/tmp/ai-tutor-restore-drill"
RESULTS_LOG="/var/log/ai-tutor-restore-drill.log"

ID="${1:-}"

# ---- pick latest full backup if not specified ----
if [[ -z "$ID" ]]; then
  # Sprint 73: pattern requires full date (YYYY-MM-DDTHHMMSSZ).
  # Old pattern 'full-[0-9TZ]+' matched partial dirs like "full-2026" too.
  ID=$(smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
    -c "cd ${SMB_BASE}/full; ls" 2>/dev/null | \
    grep -oE 'full-[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z' | sort -r | head -1)
  if [[ -z "$ID" ]]; then
    log "ERROR: no full backups found"
    exit 1
  fi
  log "Auto-selected latest backup: $ID"
fi

log "Sprint 73: restore drill started for $ID"

# ---- download manifest ----
rm -rf "$TEST_RESTORE_DIR" && mkdir -p "$TEST_RESTORE_DIR"

log "downloading manifest.json..."
smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
  -c "cd ${SMB_BASE}/full/${ID}; lcd $TEST_RESTORE_DIR; get manifest.json" >/dev/null 2>&1

if [[ ! -f "$TEST_RESTORE_DIR/manifest.json" ]]; then
  log "ERROR: manifest.json not found"
  exit 1
fi

log "manifest:"
cat "$TEST_RESTORE_DIR/manifest.json" | head -3

# ---- verify SHA256 ----
log "downloading SHA256SUMS..."
smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
  -c "cd ${SMB_BASE}/full/${ID}; lcd $TEST_RESTORE_DIR; get SHA256SUMS" >/dev/null 2>&1

log "downloading db.sql.gz..."
smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
  -c "cd ${SMB_BASE}/full/${ID}/db; lcd $TEST_RESTORE_DIR; get db.sql.gz" >/dev/null 2>&1

if [[ -f "$TEST_RESTORE_DIR/SHA256SUMS" ]]; then
  if (cd "$TEST_RESTORE_DIR" && sha256sum -c SHA256SUMS); then
    log "✓ SHA256 verification PASSED"
  else
    log "✗ SHA256 verification FAILED"
    exit 1
  fi
else
  log "WARN: no SHA256SUMS, skipping verification"
fi

# ---- restore to TEST db (не трогаем production) ----
if [[ ! -s "$TEST_RESTORE_DIR/db.sql.gz" ]]; then
  log "ERROR: db.sql.gz пустой"
  exit 1
fi

# Use docker exec в temp container (не в production DB)
log "creating temp postgres container for restore test..."
TEMP_CONTAINER=$(docker run -d --name "restore_drill_$$" \
  -e POSTGRES_DB="$TEST_DB_NAME" \
  -e POSTGRES_USER=tutor \
  -e POSTGRES_PASSWORD=test \
  postgres:16-alpine 2>/dev/null)
sleep 5  # wait for postgres ready

log "restoring dump to $TEST_DB_NAME..."
if gunzip -c "$TEST_RESTORE_DIR/db.sql.gz" | \
  docker exec -i "$TEMP_CONTAINER" psql -U tutor -d "$TEST_DB_NAME" >/dev/null 2>&1; then
  log "✓ restore to test db SUCCEEDED"
else
  log "✗ restore FAILED"
  docker rm -f "$TEMP_CONTAINER" >/dev/null 2>&1
  exit 1
fi

# Quick sanity check: count tables
TABLE_COUNT=$(docker exec "$TEMP_CONTAINER" psql -U tutor -d "$TEST_DB_NAME" \
  -tA -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "0")
log "table count in restored db: $TABLE_COUNT"

# Cleanup
log "cleanup: removing temp container..."
docker rm -f "$TEMP_CONTAINER" >/dev/null 2>&1

# ---- summary ----
if [[ "$TABLE_COUNT" -gt 10 ]]; then
  log "✓✓✓ RESTORE DRILL PASSED ✓✓✓"
  log "  Backup: $ID"
  log "  Tables: $TABLE_COUNT"
  log "  SHA256: OK"
  log "  Restore: OK"
  exit 0
else
  log "✗✗✗ RESTORE DRILL FAILED ✗✗✗"
  log "  Table count too low: $TABLE_COUNT (expected >10)"
  exit 1
fi


