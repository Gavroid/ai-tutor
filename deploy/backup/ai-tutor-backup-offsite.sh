#!/bin/bash
# Offsite backup: копирует свежие бэкапы в отдельное место.
# По умолчанию — локальная папка /var/backups/ai-tutor/ (имитация удалённого хоста).
# Для реального offsite настройте BACKUP_OFFSITE_DEST="user@backup-host:/path/"

set -euo pipefail

BACKUP_SRC="/opt/ai-tutor/deploy/backup/_out"
BACKUP_OFFSITE_DEST="${BACKUP_OFFSITE_DEST:-/var/backups/ai-tutor}"

mkdir -p "$BACKUP_OFFSITE_DEST"

# Берём только последние 7 дней (weekly + daily rotation)
find "$BACKUP_SRC" -name "*.gz" -mtime +7 -delete 2>/dev/null || true

# Sync через rsync (если есть) или cp
if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "$BACKUP_SRC/" "$BACKUP_OFFSITE_DEST/" || cp -ru "$BACKUP_SRC/." "$BACKUP_OFFSITE_DEST/"
else
    cp -ru "$BACKUP_SRC/." "$BACKUP_OFFSITE_DEST/"
fi

# Логируем
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) offsite backup done: $(ls -1 "$BACKUP_OFFSITE_DEST" | wc -l) files" >> /var/log/ai-tutor-backup.log

# Удаляем offsite старше 30 дней
find "$BACKUP_OFFSITE_DEST" -name "*.gz" -mtime +30 -delete 2>/dev/null || true

echo "Offsite backup complete -> $BACKUP_OFFSITE_DEST"
