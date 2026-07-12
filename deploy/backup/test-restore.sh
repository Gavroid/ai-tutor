#!/bin/bash
set -e
cd /opt/ai-tutor/deploy

# Бэкап, который тестируем
BACKUP=$(ls -1t /var/backups/ai-tutor/db-*.sql.gz | head -1)
echo "=== Тестирую restore: $BACKUP ==="

# Проверяем md5 manifest если есть
echo "--- MD5 verification ---"
MANIFEST="${BACKUP%.sql.gz}.md5"
# Если manifest называется manifest-TIMESTAMP.md5 — найдём по timestamp
if [ ! -f "$MANIFEST" ]; then
    TS=$(basename "$BACKUP" | sed 's/db-//;s/\.sql\.gz//')
    MANIFEST="/var/backups/ai-tutor/manifest-$TS.md5"
fi
if [ -f "$MANIFEST" ]; then
    if md5sum -c "$MANIFEST" 2>&1 | grep -q "OK"; then
        echo "✓ MD5 manifest verified: $MANIFEST"
    else
        echo "✗ MD5 manifest FAILED — backup может быть corrupted"
        md5sum -c "$MANIFEST" 2>&1
        exit 1
    fi
else
    echo "⚠ Manifest не найден, пропускаем MD5 check"
fi

# Создаём test БД
echo "--- Создаём test DB ---"
docker compose exec -T db psql -U tutor -d postgres -c "DROP DATABASE IF EXISTS tutor_test;" 2>&1 | tail -1
docker compose exec -T db psql -U tutor -d postgres -c "CREATE DATABASE tutor_test;" 2>&1 | tail -1

# Restore
echo "--- Restore ---"
zcat "$BACKUP" | docker compose exec -T db psql -U tutor -d tutor_test 2>&1 | tail -5

# Проверка данных
echo "--- Проверка таблиц ---"
docker compose exec -T db psql -U tutor -d tutor_test -tA <<'EOF'
SELECT 'users: ' || (SELECT COUNT(*) FROM users)
UNION ALL SELECT 'subjects: ' || (SELECT COUNT(*) FROM subjects)
UNION ALL SELECT 'topics: ' || (SELECT COUNT(*) FROM topics)
UNION ALL SELECT 'audit_logs: ' || (SELECT COUNT(*) FROM audit_logs);
EOF

# Cleanup
echo "--- Cleanup ---"
docker compose exec -T db psql -U tutor -d postgres -c "DROP DATABASE tutor_test;" 2>&1 | tail -1

echo "=== Restore test DONE ==="
