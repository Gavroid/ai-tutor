#!/bin/bash
# Init-скрипт для Postgres: устанавливает пароль пользователю при первом старте.
# Вызывается через /docker-entrypoint-initdb.d/ только если /var/lib/postgresql/data пуст.

set -e

# Устанавливаем пароль (POSTGRES_PASSWORD берётся из env)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    ALTER USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';
EOSQL

echo "[init-db] Пароль пользователю ${POSTGRES_USER} установлен."