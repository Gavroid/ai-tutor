#!/bin/bash
# Sprint 6.1 — supervisor для Telegram bot.
# Запускать через cron каждые 5 минут.
# Проверяет живой ли бот в контейнере (НЕ на хосте, потому что
# процесс живёт в namespace контейнера).

set -uo pipefail

# Загружаем env из /opt/ai-tutor/.env (НЕ /etc/ai-tutor/.env — нет на проде).
set -a
source /opt/ai-tutor/.env
set +a

LOG=/var/log/ai-tutor-telegram-bot.log
CONTAINER="deploy-backend-1"

# Проверяем что бот жив в контейнере.
ALIVE=$(docker exec "$CONTAINER" bash -c 'for pid in $(ls /proc/); do cmdline=$(cat /proc/$pid/cmdline 2>/dev/null); if [ -n "$cmdline" ] && echo "$cmdline" | grep -q app.bot.telegram_bot; then echo $pid; break; fi; done' 2>/dev/null)

if [ -n "$ALIVE" ]; then
    # Бот уже работает — выходим
    exit 0
fi

# Бот не найден в контейнере — запускаем
echo "[$(date -u +%FT%TZ)] telegram bot not running, starting..." >> "$LOG"
docker exec -u root -e TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" -e REDIS_URL="$REDIS_URL" "$CONTAINER" bash -c 'nohup python3 -m app.bot.telegram_bot > /tmp/ai-tutor-telegram-bot.log 2>&1 &'
echo "[$(date -u +%FT%TZ)] telegram bot started" >> "$LOG"
