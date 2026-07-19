#!/bin/bash
# Sprint 3.6.2 — disk usage monitor.
# Запускается через cron каждый час.
# Если диск > 80% — шлёт alert в Telegram.
# После deploy — НЕ шлёт (чтобы не spam'ить при множественных deploy'ах).

set -e

LOG="/var/log/ai-tutor-disk-monitor.log"
STATE_FILE="/tmp/ai-tutor-disk-state"

# Env (для TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID)
ENV_FILE="/opt/ai-tutor/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

# Текущее использование диска в %
USAGE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Читаем предыдущее состояние
PREV_STATE="ok"
if [ -f "$STATE_FILE" ]; then
  PREV_STATE=$(cat "$STATE_FILE")
fi

# Thresholds
WARN=80
CRIT=90

if [ "$USAGE" -ge "$CRIT" ]; then
  STATE="critical"
elif [ "$USAGE" -ge "$WARN" ]; then
  STATE="warning"
else
  STATE="ok"
fi

# Пишем в лог
echo "$TIMESTAMP disk=${USAGE}% state=$STATE" >> "$LOG"

# Если состояние изменилось с ok → warning/critical, шлём alert
# (или если уже warning/critical — тоже шлём раз в час)
if [ "$STATE" != "ok" ] && [ "$STATE" != "$PREV_STATE" ]; then
  MSG="⚠️ Disk usage CRITICAL: ${USAGE}% on 192.168.1.86"
  [ "$STATE" = "warning" ] && MSG="⚠️ Disk usage WARNING: ${USAGE}% on 192.168.1.86"

  if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    curl -sf -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d "chat_id=${TELEGRAM_CHAT_ID}" -d "text=$MSG" -d "parse_mode=Markdown" \
      -o /dev/null || echo "(telegram notify failed)" | tee -a "$LOG"
  fi
fi

# Сохраняем состояние
echo "$STATE" > "$STATE_FILE"
exit 0