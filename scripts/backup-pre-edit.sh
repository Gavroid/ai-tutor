#!/usr/bin/env bash
# backup-pre-edit.sh — инкрементальный бэкап ai-tutor ПЕРЕД изменениями в коде.
#
# Использование:
#   ./scripts/backup-pre-edit.sh
#
# Что делает:
#   1. Архивирует текущее состояние кода (без .venv/node_modules/etc).
#   2. Загружает на SMB-шару в /ai-tutor/pre-edit/<id>/.
#   3. Ничего не делает с БД (только код — перед git commit).
#
# Вызывается из .git/hooks/pre-commit автоматически.
# Можно вызвать руками перед любым risky изменением.

set -euo pipefail

SMB_HOST="192.168.1.91"
SMB_SHARE="Kirill-AI"
SMB_CREDS="/root/.ai-tutor-secrets/smb.creds"
SMB_BASE="ai-tutor"

PROJECT_DIR="/root/workspace/ai-tutor"
LOCAL_TMP="/tmp/ai-tutor-preedit"
RETENTION_PREEDIT=30

TS=$(date -u +%Y-%m-%dT%H%M%SZ)
ID="preedit-${TS}"
echo "[preedit] ID=$ID"

rm -rf "$LOCAL_TMP" && mkdir -p "$LOCAL_TMP"
trap 'rm -rf "$LOCAL_TMP"' EXIT

# код
tar --exclude='.venv' --exclude='node_modules' --exclude='.next' \
    --exclude='__pycache__' --exclude='.pytest_cache' --exclude='.mypy_cache' \
    --exclude='.ruff_cache' --exclude='test-results' --exclude='playwright-report' \
    --exclude='*.pyc' --exclude='.git' --exclude='.hermes' --exclude='data/uploads' \
    -czf "$LOCAL_TMP/code.tar.gz" \
    -C "$(dirname "$PROJECT_DIR")" "$(basename "$PROJECT_DIR")"

# sha256
(cd "$LOCAL_TMP" && sha256sum code.tar.gz > SHA256SUMS)

CODE_SIZE=$(stat -c '%s' "$LOCAL_TMP/code.tar.gz")

# manifest
cat > "$LOCAL_TMP/manifest.json" <<EOF
{
  "id": "$ID",
  "type": "pre-edit",
  "created_at": "$TS",
  "trigger": "git-hook",
  "host": "$(hostname)",
  "files": {"code": "code.tar.gz"},
  "sizes": {"code_bytes": $CODE_SIZE, "total_bytes": $CODE_SIZE},
  "checksums_file": "SHA256SUMS",
  "retention": {"policy": "keep_last_n", "preedit_keep": $RETENTION_PREEDIT}
}
EOF

# smbclient не умеет mkdir -p, делаем по уровням
smb_mkdir_p() {
  local remote_dir="$1" cur=""
  IFS='/' read -ra PARTS <<< "$remote_dir"
  for p in "${PARTS[@]}"; do
    cur="${cur}/${p}"
    smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
      -c "mkdir $cur" 2>&1 | grep -E "(NT_STATUS|Error)" | grep -v "OBJECT_NAME_COLLISION" || true
  done
}

# загрузка
smb_mkdir_p "${SMB_BASE}/pre-edit/${ID}"
smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
  -c "cd ${SMB_BASE}/pre-edit/${ID}; lcd $LOCAL_TMP; put code.tar.gz; put manifest.json; put SHA256SUMS" 2>&1 | grep -v "^$" || true
smb_mkdir_p "${SMB_BASE}/manifests"
smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
  -c "cd ${SMB_BASE}/manifests; lcd $LOCAL_TMP; put manifest.json" 2>&1 | grep -v "^$" || true

# retention
ALL_PRE=$(smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
  -c "cd ${SMB_BASE}/pre-edit; ls" 2>/dev/null | grep -E '^[[:space:]]*preedit-' | awk '{print $NF}' | sort)
COUNT=$(echo "$ALL_PRE" | grep -c '^preedit-' || true)
if (( COUNT > RETENTION_PREEDIT )); then
  REMOVE_COUNT=$((COUNT - RETENTION_PREEDIT))
  echo "$ALL_PRE" | head -n "$REMOVE_COUNT" | while read -r OLD; do
    [[ -n "$OLD" ]] && smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
      -c "cd ${SMB_BASE}/pre-edit; rmdir ${OLD}" 2>&1 | grep -v "^$" || true
  done
fi

echo "[preedit] DONE: $ID (code=${CODE_SIZE}b)"
echo "[preedit] SMB: //${SMB_HOST}/${SMB_SHARE}/${SMB_BASE}/pre-edit/${ID}/"
