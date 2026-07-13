#!/bin/bash
# Offsite backup: заливает свежие бэкапы на SMB-шару.
#
# Pilot Core Stage 2.5 — реальный offsite backup (Sprint 6.6 из SPRINT-6-PLAN.md).
#
# Что делает:
#   1) Берёт последние бэкапы из BACKUP_SRC (по умолчанию /opt/ai-tutor/deploy/backup/_out).
#   2) Заливает их на SMB-шару 192.168.1.91:Kirill-AI/ai-tutor/offsite/ через smbclient.
#   3) Верифицирует: md5 самого свежего manifest на source == md5 на SMB.
#   4) Retention на SMB: 30 дней (можно настроить через OFFSITE_RETENTION_DAYS).
#   5) Записывает в audit_log через прямой SQL INSERT.
#   6) Fail-closed: exit non-zero если SMB недоступен, hash mismatch, или source пуст.
#
# Переменные окружения:
#   BACKUP_SRC                     — обычно /opt/ai-tutor/deploy/backup/_out
#   SMB_HOST, SMB_SHARE, SMB_CREDS — параметры SMB (дефолты для 192.168.1.91)
#   SMB_OFFSITE_DIR                — путь внутри share (по умолчанию "ai-tutor/offsite")
#   OFFSITE_RETENTION_DAYS         — retention в днях (по умолчанию 30)
#   BACKUP_OFFSITE_REQUIRED        — если =0, exit 0 при ошибках (только для dev/test)
#                                    по умолчанию =1 (fail-closed для prod)
#
# Cron (на проде, /etc/cron.d/ai-tutor-backup):
#   0 3 * * * /opt/ai-tutor/deploy/backup/backup.sh && /opt/ai-tutor/deploy/backup/ai-tutor-backup-offsite.sh
#
# Требования:
#   - smbclient (пакет smbclient, Debian/Ubuntu)
#   - credentials файл в формате:
#         username=<user>
#         password=<pass>
#   - docker compose для записи в audit_log (контейнер deploy-db-1)

set -euo pipefail

BACKUP_SRC="${BACKUP_SRC:-/opt/ai-tutor/deploy/backup/_out}"
SMB_HOST="${SMB_HOST:-192.168.1.91}"
SMB_SHARE="${SMB_SHARE:-Kirill-AI}"
SMB_CREDS="${SMB_CREDS:-/root/.ai-tutor-secrets/smb.creds}"
SMB_OFFSITE_DIR="${SMB_OFFSITE_DIR:-ai-tutor/offsite}"
OFFSITE_RETENTION_DAYS="${OFFSITE_RETENTION_DAYS:-30}"
BACKUP_OFFSITE_REQUIRED="${BACKUP_OFFSITE_REQUIRED:-1}"
LOG="/var/log/ai-tutor-backup.log"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

# smbclient не умеет mkdir -p — создаём путь по уровням.
# SMB пути абсолютные от корня share, поэтому "mkdir foo" создаёт foo в текущей
# директории. Если smb внутри уже сделал "cd foo" и папка не существует — получим
# NOT_FOUND, поэтому сначала создаём все уровни от корня.
smb_mkdir_p() {
  local remote_dir="$1" cur=""
  IFS='/' read -ra PARTS <<< "$remote_dir"
  for p in "${PARTS[@]}"; do
    [ -z "$p" ] && continue
    cur="${cur}${p}"
    smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
      -c "mkdir ${cur}" 2>&1 | grep -E "(NT_STATUS|Error)" | grep -v "OBJECT_NAME_COLLISION" || true
    cur="${cur}/"
  done
}

# 1) prerequisites
command -v smbclient >/dev/null 2>&1 || {
  log "OFFSITE FAIL: smbclient not installed"
  exit 1
}
[ -r "$SMB_CREDS" ] || {
  log "OFFSITE FAIL: SMB credentials $SMB_CREDS not readable"
  exit 1
}
[ -d "$BACKUP_SRC" ] || {
  log "OFFSITE FAIL: source $BACKUP_SRC not found"
  exit 1
}

# 2) source должен иметь свежий manifest
LATEST_LOCAL=$(ls -1t "$BACKUP_SRC"/manifest-*.md5 2>/dev/null | head -1 || true)
[ -n "$LATEST_LOCAL" ] || {
  log "OFFSITE FAIL: source $BACKUP_SRC has no manifest"
  exit 1
}
LATEST_BASENAME=$(basename "$LATEST_LOCAL")

# 3) SMB connectivity test (lightweight — list parent)
log "OFFSITE: testing SMB connectivity to ${SMB_HOST}/${SMB_SHARE} ..."
SMB_TEST=$(smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" -c "ls" 2>&1 || true)
if echo "$SMB_TEST" | grep -qE "NT_STATUS_(ACCESS_DENIED|LOGON_FAILURE|NETWORK_NAME_DELETED)"; then
  log "OFFSITE FAIL: SMB auth/connectivity error: $(echo "$SMB_TEST" | head -1)"
  exit 1
fi

# Создаём цепочку папок ai-tutor/offsite (идемпотентно — OBJECT_NAME_COLLISION игнорируется)
smb_mkdir_p "$SMB_OFFSITE_DIR"
log "OFFSITE: ensured ${SMB_OFFSITE_DIR}/ exists on SMB"

# 4) Upload: put last 7 days of artifacts (manifest + db + uploads)
log "OFFSITE: uploading artifacts from $BACKUP_SRC"
FILES_TO_UPLOAD=$(find "$BACKUP_SRC" -maxdepth 1 -type f \( -name "manifest-*.md5" -o -name "db-*.sql.gz" -o -name "uploads-*.tar.gz" \) -mtime -7)
UPLOAD_COUNT=0
UPLOAD_FAILED=0
for f in $FILES_TO_UPLOAD; do
  bn=$(basename "$f")
  if smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
       -c "cd ${SMB_OFFSITE_DIR}; put ${f} ${bn}" >/dev/null 2>&1; then
    UPLOAD_COUNT=$((UPLOAD_COUNT + 1))
  else
    UPLOAD_FAILED=$((UPLOAD_FAILED + 1))
    log "OFFSITE WARN: failed to upload $bn"
  fi
done
[ "$UPLOAD_FAILED" -eq 0 ] || {
  log "OFFSITE FAIL: $UPLOAD_FAILED files failed to upload"
  exit 1
}
log "OFFSITE: uploaded $UPLOAD_COUNT files"

# 5) Verify: md5 свежего manifest на source должен совпасть с md5 на SMB
SRC_HASH=$(md5sum "$LATEST_LOCAL" | awk '{print $1}')
# SMB-side: download the same manifest to /tmp, compare hashes
TMP_DOWNLOAD="/tmp/offsite-verify-${LATEST_BASENAME}"
if ! smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
     -c "cd ${SMB_OFFSITE_DIR}; get ${LATEST_BASENAME} ${TMP_DOWNLOAD}" >/dev/null 2>&1; then
  log "OFFSITE FAIL: could not download $LATEST_BASENAME from SMB for verification"
  exit 1
fi
DEST_HASH=$(md5sum "$TMP_DOWNLOAD" | awk '{print $1}')
rm -f "$TMP_DOWNLOAD"
if [ "$SRC_HASH" != "$DEST_HASH" ]; then
  log "OFFSITE FAIL: hash mismatch src=$SRC_HASH dest=$DEST_HASH for $LATEST_BASENAME"
  exit 1
fi
log "OFFSITE OK: hash verified $LATEST_BASENAME ($SRC_HASH)"

# 6) Retention на SMB: удалить файлы старше N дней
log "OFFSITE: applying retention ($OFFSITE_RETENTION_DAYS days)"
ALL_REMOTE=$(smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
  -c "cd ${SMB_OFFSITE_DIR}; ls" 2>/dev/null | awk '/^[[:space:]]+[A-Z]+[[:space:]]+[0-9]+/ {print $NF}' | grep -E '^(manifest|db|uploads)-' || true)
DELETED=0
for f in $ALL_REMOTE; do
  # Извлечь timestamp из имени: manifest-20260713T191522Z.md5 → 2026-07-13 19:15:22
  TS_RAW=$(echo "$f" | sed -E 's/^(manifest|db|uploads)-([0-9]{8}T[0-9]{6}Z).*$/\2/')
  if [ -n "$TS_RAW" ]; then
    TS_HUMAN=$(echo "$TS_RAW" | sed -E 's/^([0-9]{4})([0-9]{2})([0-9]{2})T([0-9]{2})([0-9]{2})([0-9]{2})Z$/\1-\2-\3 \4:\5:\6/')
    FILE_AGE_DAYS=$(( ( $(date +%s) - $(date -d "$TS_HUMAN" +%s 2>/dev/null || echo 0) ) / 86400 ))
    if [ "$FILE_AGE_DAYS" -gt "$OFFSITE_RETENTION_DAYS" ]; then
      smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
        -c "cd ${SMB_OFFSITE_DIR}; del ${f}" >/dev/null 2>&1 && DELETED=$((DELETED + 1))
    fi
  fi
done
log "OFFSITE: retention deleted $DELETED files older than $OFFSITE_RETENTION_DAYS days"

# 7) Audit log запись
AUDIT_RESULT="success"
AUDIT_FILES="$UPLOAD_COUNT"
AUDIT_HASH="$SRC_HASH"
AUDIT_DETAILS="{\"files_uploaded\": $UPLOAD_COUNT, \"files_deleted\": $DELETED, \"hash\": \"$SRC_HASH\", \"retention_days\": $OFFSITE_RETENTION_DAYS, \"smb_host\": \"$SMB_HOST\"}"
# Защита от SQL injection: только цифры и SHA-like строки
AUDIT_DETAILS_SANITIZED=$(echo "$AUDIT_DETAILS" | sed "s/'/''/g")
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^deploy-db-1$'; then
  docker exec deploy-db-1 psql -U tutor -d tutor -c \
    "INSERT INTO audit_logs (action, entity, entity_id, details, created_at) VALUES ('backup.offsite', 'backup', NULL, '${AUDIT_DETAILS_SANITIZED}'::jsonb, NOW())" \
    >/dev/null 2>&1 || log "OFFSITE WARN: audit_log insert failed (non-critical)"
else
  log "OFFSITE WARN: deploy-db-1 not running, skipping audit_log"
fi

# 8) Log success
COUNT=$(smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
  -c "cd ${SMB_OFFSITE_DIR}; ls" 2>/dev/null | awk '/^[[:space:]]+[A-Z]+[[:space:]]+[0-9]+/ {print $NF}' | grep -E '^(manifest|db|uploads)-' | wc -l)
log "OFFSITE OK: $UPLOAD_COUNT uploaded, $DELETED deleted, $COUNT total on SMB"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) offsite backup done: uploaded=$UPLOAD_COUNT deleted=$DELETED total=$COUNT" >> "$LOG"

# Honor BACKUP_OFFSITE_REQUIRED=0 для dev
if [ "$BACKUP_OFFSITE_REQUIRED" = "0" ]; then
  exit 0
fi
exit 0