#!/bin/bash
# Резервное копирование PostgreSQL + uploads.
# Использование:
#   ./deploy/backup/backup.sh                # полный бэкап в ./deploy/backup/_out/
#   ./deploy/backup/backup.sh --restore FILE # восстановление
#
# Cron: 0 3 * * * /opt/ai-tutor/deploy/backup/backup.sh >> /var/log/ai-tutor-backup.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_ROOT="$SCRIPT_DIR/_out"
mkdir -p "$BACKUP_ROOT"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

# Параметры БД из env или дефолты
: "${POSTGRES_USER:=tutor}"
: "${POSTGRES_PASSWORD:=tutor}"
: "${POSTGRES_DB:=tutor}"
: "${POSTGRES_HOST:=localhost}"
: "${POSTGRES_PORT:=5432}"

# Если запущено на хосте рядом с docker-compose — используем docker exec
# Если БД локально — используем pg_dump напрямую
DOCKER_COMPOSE_DIR="$SCRIPT_DIR/.."
DOCKER_PG_SERVICE="db"
USE_DOCKER="false"
if command -v docker >/dev/null 2>&1 && [ -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" ]; then
    # Sprint 9.2 audit fix: явный детект через docker inspect (более robust)
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^deploy-${DOCKER_PG_SERVICE}-1$"; then
        USE_DOCKER="true"
    fi
fi

# Sprint 9.2 audit fix: если pg_dump не доступен на хосте — fallback на docker exec
# даже если предыдущий детект не сработал (например cron с другим PATH).
if [ "$USE_DOCKER" = "false" ] && ! command -v pg_dump >/dev/null 2>&1; then
    if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^deploy-${DOCKER_PG_SERVICE}-1$"; then
        echo "[$(date -Iseconds)] pg_dump не найден, fallback на docker exec"
        USE_DOCKER="true"
    fi
fi

DB_FILE="$BACKUP_ROOT/db-$TS.sql.gz"
UPLOAD_ARCHIVE="$BACKUP_ROOT/uploads-$TS.tar.gz"

restore() {
    local file="$1"
    if [[ ! -f "$file" ]]; then
        echo "Файл не найден: $file" >&2
        exit 1
    fi
    echo "Восстанавливаю $file в $POSTGRES_DB@$POSTGRES_HOST..."

    if [ "$USE_DOCKER" = "true" ]; then
        # Шаг 1: drop all public schema (атомарно)
        echo "  Шаг 1: drop схема public..."
        docker compose -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" \
            exec -T "$DOCKER_PG_SERVICE" \
            psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
            -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" 2>&1 | tail -3
        # Шаг 2: grant на схему
        docker compose -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" \
            exec -T "$DOCKER_PG_SERVICE" \
            psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
            -c "GRANT ALL ON SCHEMA public TO $POSTGRES_USER;" 2>&1 | tail -3
        # Шаг 3: загрузить данные
        echo "  Шаг 2: загрузка данных..."
        gunzip -c "$file" | docker compose -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" \
            exec -T "$DOCKER_PG_SERVICE" \
            psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 2>&1 | tail -10
    else
        PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
            -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
            -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO $POSTGRES_USER;"
        gunzip -c "$file" | PGPASSWORD="$POSTGRES_PASSWORD" psql \
            -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
            -v ON_ERROR_STOP=1 2>&1 | tail -10
    fi
    echo "  OK — восстановлено."
}

if [[ "${1:-}" == "--restore" ]]; then
    restore "$2"
    exit 0
fi

echo "[$(date -Iseconds)] Бэкап БД → $DB_FILE"
if [ "$USE_DOCKER" = "true" ]; then
    # Бэкап через docker exec — pg_dump доступен внутри контейнера
    docker compose -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" exec -T "$DOCKER_PG_SERVICE" \
        pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges \
        | gzip -9 > "$DB_FILE"
else
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        --no-owner --no-privileges | gzip -9 > "$DB_FILE"
fi

echo "[$(date -Iseconds)] Бэкап uploads → $UPLOAD_ARCHIVE"
# uploads volume смонтирован в /app/uploads внутри backend контейнера
# Бэкапим прямо из контейнера, чтобы не зависеть от хоста
if [ "$USE_DOCKER" = "true" ] && docker compose -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" \
        exec -T backend test -d /app/uploads 2>/dev/null; then
    docker compose -f "$DOCKER_COMPOSE_DIR/docker-compose.yml" exec -T backend \
        tar -czf - -C /app uploads 2>/dev/null > "$UPLOAD_ARCHIVE" || \
        echo "[$(date -Iseconds)] uploads пусты или нет доступа"
elif [ -d "$SCRIPT_DIR/../../apps/backend/uploads" ]; then
    tar -czf "$UPLOAD_ARCHIVE" -C "$SCRIPT_DIR/../../apps/backend" uploads 2>/dev/null || true
else
    echo "[$(date -Iseconds)] uploads не найдены, пропускаю"
fi

# Ротация — хранить последние 14 дней
find "$BACKUP_ROOT" -type f -mtime +14 -delete

# Создаём md5 manifest для верификации (если что-то backup corrupt — restore это поймает)
if [ -f "$DB_FILE" ] || [ -f "$UPLOAD_ARCHIVE" ]; then
    MANIFEST="$BACKUP_ROOT/manifest-$TS.md5"
    > "$MANIFEST"
    [ -f "$DB_FILE" ] && md5sum "$DB_FILE" >> "$MANIFEST"
    [ -f "$UPLOAD_ARCHIVE" ] && md5sum "$UPLOAD_ARCHIVE" >> "$MANIFEST"
    echo "[$(date -Iseconds)] Создан manifest: $MANIFEST"
fi

# Показать результат
echo
echo "[$(date -Iseconds)] Готово. Файлов в $BACKUP_ROOT:"
ls -lah "$BACKUP_ROOT"/ | tail -10