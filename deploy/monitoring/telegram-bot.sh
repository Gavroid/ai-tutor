#!/bin/bash
# Sprint 6.1 — запуск Telegram bot в фоне.
#
# Этот скрипт проверяет что бот работает и перезапускает если нет.
# Запускать через cron каждые 5 минут.

set -uo pipefail

LOG=/var/log/ai-tutor-telegram-bot.log
BOT_PID_FILE=/var/run/ai-tutor-telegram-bot.pid
CONTAINER="deploy-backend-1"

# Если уже запущен — выходим
if [ -f "$BOT_PID_FILE" ]; then
    PID=$(cat "$BOT_PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        # Уже работает
        exit 0
    fi
    rm -f "$BOT_PID_FILE"
fi

# Запускаем бот внутри контейнера в фоне
docker exec -u root -d "$CONTAINER" bash -c "nohup python3 -m app.bot.telegram_bot > /var/log/ai-tutor-telegram-bot.log 2>&1 & echo \$!" > "$BOT_PID_FILE"

echo "[$(date -u +%FT%TZ)] telegram bot started (pid=$(cat $BOT_PID_FILE))" >> "$LOG"