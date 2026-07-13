#!/usr/bin/env bash
# backup-full.sh — полный бэкап ai-tutor на SMB-шару.
#
# Что бэкапим:
#   - код проекта (без .venv, node_modules, .next, __pycache__, .git, .hermes)
#   - PostgreSQL дамп (docker exec db pg_dump)
#   - загруженные пользователями файлы (data/uploads)
#   - конфиги (docker-compose, nginx, .env.example)
#   - manifest с sha256 и метаданными
#
# Куда: //192.168.1.91/Kirill-AI/ai-tutor/{full,db,manifests}/
#
# Использование:
#   ./scripts/backup-full.sh                # полный бэкап, ID = текущий timestamp
#   ./scripts/backup-full.sh --label v1.2   # с человекочитаемой меткой
#
# ВАЖНО: запускать от root (для docker exec). Пароль SMB в логах НЕ светится.

set -euo pipefail

# ---- конфигурация ----
SMB_HOST="192.168.1.91"
SMB_SHARE="Kirill-AI"
SMB_CREDS="/root/.ai-tutor-secrets/smb.creds"
SMB_BASE="ai-tutor"                    # корневой каталог на шаре

PROJECT_DIR="/root/workspace/ai-tutor"
COMPOSE_DIR="/root/workspace/ai-tutor/deploy"
DB_SERVICE="db"                         # имя контейнера postgres в compose
DB_USER="tutor"
DB_NAME="tutor"
DB_CONTAINER="${DB_SERVICE}"            # если в compose переименовал — поменяй

LOCAL_TMP="/tmp/ai-tutor-backup"
RETENTION_FULL=7                        # хранить последние N full бэкапов

LABEL=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --label) LABEL="$2"; shift 2;;
    *) echo "unknown arg: $1"; exit 1;;
  esac
done

# ---- ID бэкапа ----
TS=$(date -u +%Y-%m-%dT%H%M%SZ)
ID="full-${TS}${LABEL:+-${LABEL}}"
echo "[backup] ID=$ID"

# ---- локальная подготовка ----
rm -rf "$LOCAL_TMP" && mkdir -p "$LOCAL_TMP/code" "$LOCAL_TMP/db" "$LOCAL_TMP/conf"
trap 'rm -rf "$LOCAL_TMP"' EXIT

# 1) код (без мусора)
echo "[backup] tarring code..."
tar --exclude='.venv' \
    --exclude='node_modules' \
    --exclude='.next' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='.mypy_cache' \
    --exclude='.ruff_cache' \
    --exclude='test-results' \
    --exclude='playwright-report' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='.hermes' \
    --exclude='data/uploads' \
    -czf "$LOCAL_TMP/code/code.tar.gz" \
    -C "$(dirname "$PROJECT_DIR")" "$(basename "$PROJECT_DIR")"

# 2) uploads (отдельно, потому что exclude в 1-м)
if [[ -d "$PROJECT_DIR/data/uploads" ]]; then
  echo "[backup] tarring uploads..."
  tar -czf "$LOCAL_TMP/code/uploads.tar.gz" -C "$PROJECT_DIR/data" uploads
fi

# 3) Postgres дамп
echo "[backup] pg_dump..."
if docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
  docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --clean | gzip > "$LOCAL_TMP/db/db.sql.gz"
else
  echo "[backup] WARN: postgres container '$DB_CONTAINER' not running, skipping DB dump" >&2
  # всё равно создаём пустой файл, чтобы manifest был полным
  : > "$LOCAL_TMP/db/db.sql.gz"
fi

# 4) конфиги вне проекта
[[ -f "$PROJECT_DIR/.env.example" ]] && cp "$PROJECT_DIR/.env.example" "$LOCAL_TMP/conf/env.example"
[[ -f "$COMPOSE_DIR/docker-compose.yml" ]] && cp "$COMPOSE_DIR/docker-compose.yml" "$LOCAL_TMP/conf/docker-compose.yml"
[[ -d "$COMPOSE_DIR/nginx" ]] && tar -czf "$LOCAL_TMP/conf/nginx.tar.gz" -C "$COMPOSE_DIR" nginx

# 5) sha256 для всего
echo "[backup] computing sha256..."
find "$LOCAL_TMP" -type f -name '*.tar.gz' -o -name '*.sql.gz' -o -name '*.example' -o -name '*.yml' | \
  xargs -r sha256sum | sed "s|$LOCAL_TMP/||" > "$LOCAL_TMP/SHA256SUMS"

CODE_SIZE=$(stat -c '%s' "$LOCAL_TMP/code/code.tar.gz")
DB_SIZE=$(stat -c '%s' "$LOCAL_TMP/db/db.sql.gz")
TOTAL_SIZE=$(du -sb "$LOCAL_TMP" | awk '{print $1}')

# 6) manifest
cat > "$LOCAL_TMP/manifest.json" <<EOF
{
  "id": "$ID",
  "type": "full",
  "created_at": "$TS",
  "trigger": "manual",
  "label": "$LABEL",
  "host": "$(hostname)",
  "files": {
    "code": "code.tar.gz",
    "uploads": $([ -f "$LOCAL_TMP/code/uploads.tar.gz" ] && echo '"uploads.tar.gz"' || echo 'null'),
    "db_dump": "db.sql.gz",
    "configs": ["env.example", "docker-compose.yml"$( [ -f "$LOCAL_TMP/conf/nginx.tar.gz" ] && echo ', "nginx.tar.gz"' )]
  },
  "sizes": {
    "code_bytes": $CODE_SIZE,
    "db_bytes": $DB_SIZE,
    "total_bytes": $TOTAL_SIZE
  },
  "checksums_file": "SHA256SUMS",
  "retention": {
    "policy": "keep_last_n",
    "full_keep": $RETENTION_FULL
  }
}
EOF

# ---- загрузка на шару (smbclient, без mount — работает в unprivileged LXC) ----
echo "[backup] uploading to SMB..."

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

# корневой каталог бэкапа (создаём все уровни)
smb_mkdir_p "${SMB_BASE}/full/${ID}/code"
smb_mkdir_p "${SMB_BASE}/full/${ID}/db"
smb_mkdir_p "${SMB_BASE}/full/${ID}/conf"
smb_mkdir_p "${SMB_BASE}/manifests"

# загрузка: корень бэкапа — manifest + sha + код + db
smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
  -c "cd ${SMB_BASE}/full/${ID}; lcd $LOCAL_TMP; put code/code.tar.gz; put db/db.sql.gz; put manifest.json; put SHA256SUMS" 2>&1 | grep -v "^$" || true

# uploads в code/
if [[ -f "$LOCAL_TMP/code/uploads.tar.gz" ]]; then
  smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
    -c "cd ${SMB_BASE}/full/${ID}/code; lcd $LOCAL_TMP/code; put uploads.tar.gz" 2>&1 | grep -v "^$" || true
fi

# конфиги в conf/
for f in "$LOCAL_TMP/conf/"*; do
  [[ -f "$f" ]] && smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
    -c "cd ${SMB_BASE}/full/${ID}/conf; lcd $LOCAL_TMP/conf; put $(basename "$f")" 2>&1 | grep -v "^$" || true
done

# также сохраняем manifest в общую папку manifests/ для быстрого листинга
smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
  -c "cd ${SMB_BASE}/manifests; lcd $LOCAL_TMP; put manifest.json" 2>&1 | grep -v "^$" || true

# ---- retention: удаляем старые full ----
echo "[backup] retention: keep last $RETENTION_FULL full backups..."
ALL_FULLS=$(smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
  -c "cd ${SMB_BASE}/full; ls" 2>/dev/null | grep -E '^[[:space:]]*full-' | awk '{print $NF}' | sort)
COUNT=$(echo "$ALL_FULLS" | grep -c '^full-' || true)
if (( COUNT > RETENTION_FULL )); then
  REMOVE_COUNT=$((COUNT - RETENTION_FULL))
  echo "$ALL_FULLS" | head -n "$REMOVE_COUNT" | while read -r OLD_ID; do
    [[ -n "$OLD_ID" ]] && {
      echo "[backup] removing old: $OLD_ID"
      smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
        -c "cd ${SMB_BASE}/full; rmdir ${OLD_ID}/code; rmdir ${OLD_ID}/db; rmdir ${OLD_ID}/conf; rmdir ${OLD_ID}" 2>&1 | grep -v "^$" || true
    }
  done
fi

# ---- проверка свободного места (smbclient не умеет df напрямую, делаем эвристику) ----
USED_BYTES=$(smbclient "//${SMB_HOST}/${SMB_SHARE}" -A "$SMB_CREDS" \
  -c "du ${SMB_BASE}" 2>/dev/null | tail -1 | awk '{print $1}' || echo 0)
if (( USED_BYTES > 80000000 )); then  # > 80 ГБ
  echo "[backup] WARN: SMB usage high ($USED_BYTES bytes), consider raising retention" >&2
fi

echo "[backup] DONE: $ID (code=${CODE_SIZE}b db=${DB_SIZE}b total=${TOTAL_SIZE}b)"
echo "[backup] SMB: //${SMB_HOST}/${SMB_SHARE}/${SMB_BASE}/full/${ID}/"
