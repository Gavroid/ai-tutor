#!/bin/bash
# Sprint 4.1.4 — cron для авто-индексации новых PDF в RAG.
#
# Запуск: через cron /etc/cron.d/ai-tutor-index
# Сканирует learning_materials с file_path и status=published,
# для каждого без chunks (или с < chunks_expected) запускает
# index_materials.py в backend контейнере.
#
# Этот скрипт НАХОДИТСЯ НА ХОСТЕ (192.168.1.86), не в контейнере.

set -euo pipefail

LOG=/var/log/ai-tutor-index-cron.log
echo "[$(date -u +%FT%TZ)] === index-cron START ===" >> "$LOG"

# Backend контейнер
CONTAINER="deploy-backend-1"

# Проверяем что контейнер запущен
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "[$(date -u +%FT%TZ)] backend container not running, skip" >> "$LOG"
    exit 0
fi

# Получаем список material_id у которых есть file_path, status=published
# но либо нет chunks в rag_chunks либо chunks меньше threshold
MATERIALS=$(docker exec deploy-db-1 psql -U tutor -d tutor -tAc "
SELECT m.id
FROM learning_materials m
WHERE m.status = 'published'
  AND m.file_path IS NOT NULL
  AND (
    NOT EXISTS (SELECT 1 FROM rag_chunks c WHERE c.material_id = m.id)
    OR (SELECT COUNT(*) FROM rag_chunks c WHERE c.material_id = m.id) < 50
  )
ORDER BY m.id;
")

if [ -z "$MATERIALS" ]; then
    echo "[$(date -u +%FT%TZ)] nothing to index" >> "$LOG"
    exit 0
fi

COUNT=0
for MAT_ID in $MATERIALS; do
    echo "[$(date -u +%FT%TZ)] indexing material_id=$MAT_ID..." >> "$LOG"
    if docker exec "$CONTAINER" python3 /app/scripts/index_materials.py --material-id "$MAT_ID" >> "$LOG" 2>&1; then
        COUNT=$((COUNT + 1))
    fi
done

echo "[$(date -u +%FT%TZ)] === index-cron DONE (indexed $COUNT materials) ===" >> "$LOG"

# TG notification
if [ "$COUNT" -gt 0 ]; then
    TG_MSG="✅ RAG index cron: проиндексировано $COUNT материал(ов)"
    curl -s -X POST "https://api.telegram.org/bot8847089147:AAEjXuRL_G7hqu796HxMFz6glmbKq9Z-TSo/sendMessage" \
        -d "chat_id=432505767" \
        -d "text=$TG_MSG" \
        >/dev/null 2>&1 || true
fi