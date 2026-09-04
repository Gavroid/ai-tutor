#!/usr/bin/env bash
# nas-retention.sh — еженедельная авточистка ai-tutor бэкапов на NAS (Sprint quality 2026-09-04, этап 1.2B).
#
# Зачем: 2026-09-04 обнаружено, что pre-edit снапшоты накопили 91 ГБ (566 шт)
# из-за сломанной retention в backup-pre-edit.sh + PDF в снапшотах.
# Скрипт — safety net ПОВЕРХ per-commit retention: если per-commit снова
# сломается, weekly-прогон не даст квоте переполниться.
#
# Режимы:
#   ./nas-retention.sh           # dry-run: только печатает, что будет удалено
#   ./nas-retention.sh --apply   # реальное удаление
#
# Cron (dev-машина, root): еженедельно, воскресенье 05:00
#   0 5 * * 0 /root/workspace/ai-tutor/scripts/nas-retention.sh --apply >> /var/log/nas-retention.log 2>&1
#
# Политика:
#   ai-tutor/pre-edit/*   — оставить последние 30 (по имени-дате, оно сортируемое)
#   ai-tutor/full/*       — оставить последние 30 (ежедневные DB-дампы ~1 МБ/шт,
#                           это самые ценные и самые маленькие бэкапы)
#   ai-tutor/offsite/*    — НЕ трогать никогда (ручной архив / git bundles)
#   ai-tutor/manifests/*  — НЕ трогать (копеечный размер)

set -uo pipefail

SMB_HOST="192.168.1.91"
SMB_SHARE="Kirill-AI"
SMB_CREDS="/root/.ai-tutor-secrets/smb.creds"
SMB_BASE="ai-tutor"

KEEP_PREEDIT=30
KEEP_FULL=30

APPLY=false
[[ "${1:-}" == "--apply" ]] && APPLY=true
$APPLY || echo "[nas-retention] DRY-RUN (передай --apply для реального удаления)"

smb() { smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" "$@" 2>/dev/null; }

list_dirs() { # $1 = remote subdir
  smb -c "cd \\${SMB_BASE}\\$1; ls" | grep -oE "$2" | sort -u
}

purge_dir() { # $1 = remote subdir, $2 = dir name to delete
  local sub="$1" d="$2"
  if $APPLY; then
    # deltree: recurse+del не удаляет вложенные ПУСТЫЕ директории (full/* содержат
    # code/, db/, conf/ подпапки) → rmdir падал с DIRECTORY_NOT_EMPTY. 2026-09-04.
    smb -c "deltree \\${SMB_BASE}\\${sub}\\${d}" \
      | grep -E "NT_STATUS" || true
    echo "[nas-retention] deleted ${sub}/${d}"
  else
    echo "[nas-retention] would delete ${sub}/${d}"
  fi
}

retain() { # $1 = subdir, $2 = regex for dir names, $3 = keep count
  local sub="$1" rx="$2" keep="$3"
  local all count remove_count
  all=$(list_dirs "$sub" "$rx")
  count=$(echo "$all" | grep -c . || true)
  if (( count > keep )); then
    remove_count=$((count - keep))
    echo "$all" | head -n "$remove_count" | while read -r d; do
      [[ -n "$d" ]] && purge_dir "$sub" "$d"
    done
  else
    echo "[nas-retention] ${sub}: ${count} <= ${keep}, чистить нечего"
  fi
}

echo "[nas-retention] $(date -u +%FT%TZ) start (apply=$APPLY)"
retain "pre-edit" 'preedit-[0-9T-]+Z' "$KEEP_PREEDIT"
retain "full" 'full-[0-9T-]+Z' "$KEEP_FULL"

# свободное место после чистки
AVAIL=$(smb -c "ls" | tail -1 | grep -oE '[0-9]+ blocks available' | grep -oE '^[0-9]+')
if [[ -n "$AVAIL" ]]; then
  GB=$((AVAIL * 1024 / 1073741824))
  echo "[nas-retention] свободно на шаре: ~${GB} ГБ из 150"
  if (( GB < 20 )); then
    echo "[nas-retention] WARN: свободно < 20 ГБ — проверь NAS вручную" >&2
  fi
fi
echo "[nas-retention] done"
