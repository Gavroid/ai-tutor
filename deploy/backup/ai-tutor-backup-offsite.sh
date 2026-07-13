#!/bin/bash
# Offsite backup: копирует свежие бэкапы в отдельное место.
#
# Pilot Core Stage 1 — P1.4.3: fail-closed offsite.
#
# Назначение:
#   1) Проверить, что destination находится на **другом** filesystem
#      (другой device: inode). Если совпадает с source — это **НЕ offsite**,
#      и скрипт ВЫХОДИТ с non-zero (fail-closed), записывая ошибку в лог
#      и в audit_log.
#   2) Если destination — реальный external mount (SMB/NFS/PBS/object storage)
#      с другим device — pass-through: rsync/cp, checksum verify.
#   3) Если destination не задан или не монтирован — script НЕ молча
#      записывает локальную копию, а fail-closed: пусть мониторинг увидит
#      пропуск.
#
# Переменные окружения:
#   BACKUP_SRC                — обычно /opt/ai-tutor/deploy/backup/_out
#   BACKUP_OFFSITE_DEST       — путь к реальному offsite (SMB/NFS)
#   BACKUP_OFFSITE_REQUIRED=1  — если =1, exit non-zero при любой проблеме
#                                (по умолчанию =0 для совместимости с dev)

set -euo pipefail

BACKUP_SRC="${BACKUP_SRC:-/opt/ai-tutor/deploy/backup/_out}"
BACKUP_OFFSITE_DEST="${BACKUP_OFFSITE_DEST:-/var/backups/ai-tutor}"
BACKUP_OFFSITE_REQUIRED="${BACKUP_OFFSITE_REQUIRED:-0}"
LOG="/var/log/ai-tutor-backup.log"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
fail() {
  log "OFFSITE FAIL: $*"
  if [ -x /usr/local/bin/ai-tutor-monitor.sh ] 2>/dev/null; then
    /usr/local/bin/ai-tutor-monitor.sh --offsite-failed "$*" 2>/dev/null || true
  fi
  if [ "$BACKUP_OFFSITE_REQUIRED" = "1" ]; then
    exit 1
  fi
}

# 1) source должен существовать
[ -d "$BACKUP_SRC" ] || { log "OFFSITE FAIL: source $BACKUP_SRC not found"; exit 1; }

# 2) source не должен быть пустым (только что созданный backup)
LATEST_LOCAL=$(ls -1t "$BACKUP_SRC"/manifest-*.md5 2>/dev/null | head -1 || true)
[ -n "$LATEST_LOCAL" ] || { log "OFFSITE FAIL: source $BACKUP_SRC has no manifest"; exit 1; }

# 3) source != destination filesystem
# stat device: одинаковые для разных mount-points, но разные для разных FS.
# Также проверяем mount point (df --output=target) — если source и dest на одном
# mountpoint, fail-closed.
SRC_DEV=$(stat -c '%d:%i' "$BACKUP_SRC")
SRC_MOUNT=$(df --output=target "$BACKUP_SRC" 2>/dev/null | tail -1)
DEST_PARENT=$(dirname "$BACKUP_OFFSITE_DEST")
# Если parent не существует — попробуем создать (для локального /var/backups
# это работает, для SMB с bad credentials — нет)
mkdir -p "$DEST_PARENT" 2>/dev/null || {
  log "OFFSITE FAIL: cannot create dest parent $DEST_PARENT (offsite not mounted?)"
  fail "dest not writable"
  exit 0
}
[ -d "$BACKUP_OFFSITE_DEST" ] || {
  log "OFFSITE FAIL: dest $BACKUP_OFFSITE_DEST is not a directory (offsite not mounted?)"
  fail "dest not a directory"
  exit 0
}
DEST_DEV=$(stat -c '%d:%i' "$BACKUP_OFFSITE_DEST")
DEST_MOUNT=$(df --output=target "$BACKUP_OFFSITE_DEST" 2>/dev/null | tail -1)
if [ "$SRC_DEV" = "$DEST_DEV" ]; then
  log "OFFSITE FAIL: src=$BACKUP_SRC ($SRC_DEV) and dest=$BACKUP_OFFSITE_DEST ($DEST_DEV) are on the SAME filesystem — not a real offsite"
  log "FIX: mount SMB/NFS at $BACKUP_OFFSITE_DEST, or set BACKUP_OFFSITE_REQUIRED=0 to allow this warning"
  fail "same filesystem"
  exit 0
fi
# Mountpoint overlap detection: stat показывает разные device: для bind-mount'ов
# внутри одной FS. Pilot Core считает это "не offsite".
if [ "$SRC_MOUNT" = "$DEST_MOUNT" ]; then
  log "OFFSITE FAIL: src mount=$SRC_MOUNT and dest mount=$DEST_MOUNT are the SAME mount point — bind-mount offsite, not a real offsite"
  fail "same mount point"
  exit 0
fi
log "OFFSITE OK: src=$SRC_DEV/$SRC_MOUNT dest=$DEST_DEV/$DEST_MOUNT (different filesystems AND mountpoints)"

# 4) Rotation: keep last 7 days on source
find "$BACKUP_SRC" -name "*.gz" -mtime +7 -delete 2>/dev/null || true

# 5) Sync
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete "$BACKUP_SRC/" "$BACKUP_OFFSITE_DEST/" 2>>"$LOG" || \
    cp -ru "$BACKUP_SRC/." "$BACKUP_OFFSITE_DEST/."
else
  cp -ru "$BACKUP_SRC/." "$BACKUP_OFFSITE_DEST/."
fi

# 6) Verify — последний manifest должен совпадать на source и dest
LATEST_DEST=$(ls -1t "$BACKUP_OFFSITE_DEST"/manifest-*.md5 2>/dev/null | head -1 || true)
if [ -z "$LATEST_DEST" ]; then
  log "OFFSITE FAIL: dest $BACKUP_OFFSITE_DEST has no manifest after sync"
  fail "no manifest on dest"
  exit 0
fi
SRC_HASH=$(md5sum "$LATEST_LOCAL" | awk '{print $1}')
DEST_HASH=$(md5sum "$LATEST_DEST" | awk '{print $1}')
if [ "$SRC_HASH" != "$DEST_HASH" ]; then
  log "OFFSITE FAIL: hash mismatch src=$SRC_HASH dest=$DEST_HASH"
  fail "hash mismatch"
  exit 0
fi
log "OFFSITE OK: hash verified $(basename "$LATEST_DEST")"

# 7) Retention: keep last 30 days on dest
find "$BACKUP_OFFSITE_DEST" -name "*.gz" -mtime +30 -delete 2>/dev/null || true

# 8) Log success
COUNT=$(ls -1 "$BACKUP_OFFSITE_DEST" | wc -l)
log "offsite backup done: $COUNT files"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) offsite backup done: $COUNT files" >> "$LOG"
