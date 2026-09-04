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

# Sprint 2026-09-04 fix: был цикл "for pid in $(ls /proc/)" без фильтра [0-9]*.
# Это захватывал /proc/self, /proc/keys и т.д., bash -c падал с ошибкой,
# supervisor никогда не находил бот → постоянно спамил "started", создавая
# десятки nohup-процессов одновременно.
#
# Правильный fix: только числовые PID + match по полной cmdline через tr.
ALIVE=$(docker exec "$CONTAINER" bash -c '
  found=""
  for pid_dir in /proc/[0-9]*; do
    pid=$(basename "$pid_dir")
    cmdline=$(tr "\0" " " < "$pid_dir/cmdline" 2>/dev/null) || continue
    case "$cmdline" in
      "python3 -m app.bot.telegram_bot "*) found="$pid"; break ;;
    esac
  done
  echo "$found"
' 2>/dev/null)

if [ -n "$ALIVE" ]; then
    # Бот уже работает — выходим
    exit 0
fi

# Бот не найден в контейнере — запускаем
echo "[$(date -u +%FT%TZ)] telegram bot not running, starting..." >> "$LOG"
docker exec -u root -e TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" -e REDIS_URL="$REDIS_URL" "$CONTAINER" bash -c 'nohup python3 -m app.bot.telegram_bot >> /tmp/ai-tutor-telegram-bot.log 2>&1 &'
echo "[$(date -u +%FT%TZ)] telegram bot started (pid=$ALIVE was empty)" >> "$LOG"
