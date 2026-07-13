#!/usr/bin/env bash
# restore.sh — восстановление ai-tutor из бэкапа на SMB-шаре.
#
# Использование:
#   ./scripts/restore.sh --list                              # показать все доступные бэкапы
#   ./scripts/restore.sh <id> --target /path/to/restore     # восстановить в указанный путь
#   ./scripts/restore.sh <id> --code-only --target /path    # только код, без БД
#   ./scripts/restore.sh <id> --db-only                     # только БД
#
# ID — это либо "full-2026-07-13T0300Z" либо "preedit-2026-07-13T1620Z".
# По умолчанию требует подтверждения перед destructive операциями.

set -euo pipefail

SMB_HOST="192.168.1.91"
SMB_SHARE="Kirill-AI"
SMB_CREDS="/root/.ai-tutor-secrets/smb.creds"
SMB_BASE="ai-tutor"

LOCAL_TMP="/tmp/ai-tutor-restore"
TARGET=""
CODE_ONLY=0
DB_ONLY=0
YES=0
ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list) LIST=1; shift;;
    --target) TARGET="$2"; shift 2;;
    --code-only) CODE_ONLY=1; shift;;
    --db-only) DB_ONLY=1; shift;;
    --yes) YES=1; shift;;
    -h|--help) sed -n '2,15p' "$0"; exit 0;;
    *) ID="$1"; shift;;
  esac
done

# ---- list ----
if [[ "${LIST:-0}" == "1" ]]; then
  echo "=== FULL backups ==="
  smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
    -c "cd ${SMB_BASE}/full; ls" 2>/dev/null | grep -E '^\s+(full|preedit)-' | awk '{print "  " $NF}'
  echo
  echo "=== PRE-EDIT backups ==="
  smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
    -c "cd ${SMB_BASE}/pre-edit; ls" 2>/dev/null | grep -E '^\s+preedit-' | awk '{print "  " $NF}'
  exit 0
fi

if [[ -z "$ID" ]]; then
  echo "ERROR: укажи ID бэкапа или --list" >&2
  echo "  ./scripts/restore.sh --list" >&2
  echo "  ./scripts/restore.sh full-2026-07-13T0300Z --target /tmp/restore --yes" >&2
  exit 1
fi

if [[ -z "$TARGET" && "$DB_ONLY" -eq 0 ]]; then
  echo "ERROR: нужно --target /path для восстановления кода" >&2
  exit 1
fi

# определяем тип
if [[ "$ID" == full-* ]]; then
  REMOTE_DIR="${SMB_BASE}/full/${ID}"
  TYPE="full"
elif [[ "$ID" == preedit-* ]]; then
  REMOTE_DIR="${SMB_BASE}/pre-edit/${ID}"
  TYPE="pre-edit"
else
  echo "ERROR: ID должен начинаться с full- или preedit-" >&2
  exit 1
fi

echo "[restore] type=$TYPE id=$ID remote=$REMOTE_DIR"

# ---- скачиваем manifest ----
rm -rf "$LOCAL_TMP" && mkdir -p "$LOCAL_TMP"
trap 'rm -rf "$LOCAL_TMP"' EXIT

echo "[restore] downloading manifest..."
smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
  -c "cd ${REMOTE_DIR}; lcd $LOCAL_TMP; get manifest.json" >/dev/null 2>&1
if [[ ! -f "$LOCAL_TMP/manifest.json" ]]; then
  echo "ERROR: manifest.json не найден на шаре, бэкап повреждён" >&2
  exit 1
fi

cat "$LOCAL_TMP/manifest.json"
echo

# ---- подтверждение ----
if [[ "$YES" -ne 1 ]]; then
  echo "Продолжить восстановление? (yes/no)"
  if [[ "$DB_ONLY" -eq 0 ]]; then
    echo "  Код: $TARGET"
  fi
  if [[ "$CODE_ONLY" -eq 0 && "$TYPE" == "full" ]]; then
    echo "  БД: postgres (текущая БД будет перезаписана)"
  fi
  read -r ANS
  [[ "$ANS" == "yes" ]] || { echo "aborted"; exit 1; }
fi

# ---- восстановление кода ----
if [[ "$DB_ONLY" -eq 0 ]]; then
  echo "[restore] downloading code.tar.gz..."
  smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
    -c "cd ${REMOTE_DIR}; lcd $LOCAL_TMP; get code.tar.gz" >/dev/null 2>&1

  if [[ ! -f "$LOCAL_TMP/code.tar.gz" ]]; then
    echo "ERROR: code.tar.gz не найден" >&2
    exit 1
  fi

  # verify sha256
  smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
    -c "cd ${REMOTE_DIR}; lcd $LOCAL_TMP; get SHA256SUMS" >/dev/null 2>&1
  (cd "$LOCAL_TMP" && sha256sum -c SHA256SUMS) || {
    echo "ERROR: sha256 mismatch" >&2; exit 1;
  }

  mkdir -p "$TARGET"
  echo "[restore] extracting to $TARGET..."
  tar -xzf "$LOCAL_TMP/code.tar.gz" -C "$TARGET" --strip-components=0

  # uploads отдельно, если был
  if [[ "$TYPE" == "full" ]] && smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
       -c "cd ${REMOTE_DIR}/code; ls uploads.tar.gz" 2>&1 | grep -q "uploads.tar.gz"; then
    echo "[restore] extracting uploads..."
    smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
      -c "cd ${REMOTE_DIR}/code; lcd $LOCAL_TMP; get uploads.tar.gz" >/dev/null
    mkdir -p "$TARGET/data"
    tar -xzf "$LOCAL_TMP/uploads.tar.gz" -C "$TARGET/data"
  fi
fi

# ---- восстановление БД (только для full) ----
if [[ "$CODE_ONLY" -eq 0 && "$TYPE" == "full" ]]; then
  echo "[restore] downloading db.sql.gz..."
  smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
    -c "cd ${REMOTE_DIR}/db; lcd $LOCAL_TMP; get db.sql.gz" >/dev/null 2>&1

  if [[ ! -s "$LOCAL_TMP/db.sql.gz" ]]; then
    echo "[restore] WARN: db dump пустой, пропускаю"
  else
    DB_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E '^(db|postgres)$' | head -1)
    if [[ -z "$DB_CONTAINER" ]]; then
      echo "ERROR: postgres container не запущен" >&2
      exit 1
    fi
    echo "[restore] restoring DB into $DB_CONTAINER..."
    gunzip -c "$LOCAL_TMP/db.sql.gz" | docker exec -i "$DB_CONTAINER" psql -U tutor -d tutor
  fi
fi

# ---- конфиги (только для full) ----
if [[ "$CODE_ONLY" -eq 0 && "$DB_ONLY" -eq 0 && "$TYPE" == "full" ]]; then
  if [[ -d "$TARGET/deploy" ]]; then
    echo "[restore] downloading configs..."
    for f in env.example docker-compose.yml; do
      smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
        -c "cd ${REMOTE_DIR}/conf; lcd $LOCAL_TMP/conf; get $f" 2>/dev/null || true
    done
    [[ -f "$LOCAL_TMP/conf/env.example" ]] && cp "$LOCAL_TMP/conf/env.example" "$TARGET/.env.example"
    [[ -f "$LOCAL_TMP/conf/docker-compose.yml" ]] && cp "$LOCAL_TMP/conf/docker-compose.yml" "$TARGET/deploy/docker-compose.yml"
  fi
fi

echo "[restore] DONE"
echo "  Код: $TARGET"
[[ "$TYPE" == "full" && "$CODE_ONLY" -eq 0 ]] && echo "  БД: восстановлена"
