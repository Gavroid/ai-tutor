#!/bin/bash
# Мониторинг AI-репетитора: uptime + ресурсы + backup freshness.
# Запускается через cron каждые 5 минут.
# Алерты в Telegram (если TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID заданы).
#
# Cron: */5 * * * * /etc/cron.d/ai-tutor-monitor (source'ит /etc/ai-tutor/.env для TELEGRAM_*)
#
# Sprint 3.5.1: BACKUP_DIR по умолчанию = /opt/ai-tutor/deploy/backup/_out
# (где backup.sh пишет). Старое значение /var/backups/ai-tutor было offsite-dest
# из старой версии backup.sh — там бэкапы не появляются, всегда stale.

set -uo pipefail

# === Конфигурация ===
PROD_HOST="${PROD_HOST:-192.168.1.86}"  # можно мониторить другой хост
PROD_URL="https://${PROD_HOST}/health"
PROD_API="https://${PROD_HOST}/api/v1/subjects"

STATE_DIR="${STATE_DIR:-/var/lib/ai-tutor-monitor}"
STATE_FILE="$STATE_DIR/last_state"
BACKUP_STATE_FILE="$STATE_DIR/last_backup_alert"
ALERT_COOLDOWN="${ALERT_COOLDOWN:-300}"  # секунд между алертами
BACKUP_STALE_HOURS="${BACKUP_STALE_HOURS:-26}"  # бэкап daily, алерт если > 26ч

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"  # опционально
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

BACKUP_DIR="${BACKUP_DIR:-/opt/ai-tutor/deploy/backup/_out}"  # Sprint 3.5.1: актуальный source (где backup.sh пишет)
BACKUP_LOG="${BACKUP_LOG:-/var/log/ai-tutor-backup.log}"

mkdir -p "$STATE_DIR"

# === Функции ===
send_telegram() {
    local msg="$1"
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
        curl -sf -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=${msg}" \
            -d "parse_mode=Markdown" \
            -o /dev/null
    fi
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) ALERT: $msg" >> /var/log/ai-tutor-monitor.log
}

should_alert() {
    local state_file="$1"
    local cooldown="${2:-3600}"  # по умолчанию 1 час между одинаковыми алертами

    if [ -f "$state_file" ]; then
        local last=$(cat "$state_file")
        local now=$(date +%s)
        local diff=$((now - last))
        if [ "$diff" -lt "$cooldown" ]; then
            return 1  # слишком рано
        fi
    fi
    echo "$(date +%s)" > "$state_file"
    return 0
}

# === Проверка HTTP ===
HTTP_CODE=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 10 "$PROD_URL")
CURRENT_STATE="ok"

if [ "$HTTP_CODE" != "200" ]; then
    CURRENT_STATE="down"
    send_telegram "🚨 *AI-репетитор DOWN*

Host: \`${PROD_HOST}\`
Health check: \`$PROD_URL\`
HTTP code: \`${HTTP_CODE}\` (expected 200)
Time: \`$(date -u)\`"
fi

# === Проверка backup freshness ===
if [ -d "$BACKUP_DIR" ]; then
    LATEST_BACKUP=$(ls -1t "$BACKUP_DIR"/db-*.sql.gz 2>/dev/null | head -1)
    if [ -n "$LATEST_BACKUP" ] && [ -f "$LATEST_BACKUP" ]; then
        BACKUP_MTIME_EPOCH=$(stat -c %Y "$LATEST_BACKUP")
        NOW_EPOCH=$(date +%s)
        BACKUP_AGE_HOURS=$(( (NOW_EPOCH - BACKUP_MTIME_EPOCH) / 3600 ))

        if [ "$BACKUP_AGE_HOURS" -gt "$BACKUP_STALE_HOURS" ]; then
            if should_alert "$BACKUP_STATE_FILE" 86400; then  # алерт 1 раз в сутки
                send_telegram "⚠️ *Backup stale*

Host: \`${PROD_HOST}\`
Last backup: \`${BACKUP_AGE_HOURS}h ago\`
File: \`$(basename "$LATEST_BACKUP")\`
Threshold: ${BACKUP_STALE_HOURS}h
Time: \`$(date -u)\`"
            fi
        fi
    else
        # Нет ни одного backup
        if should_alert "$BACKUP_STATE_FILE" 86400; then
            send_telegram "❌ *No backups found*

Host: \`${PROD_HOST}\`
Dir: \`${BACKUP_DIR}\`
Time: \`$(date -u)\`"
        fi
    fi
fi

# === Проверка ресурсов (если запущено локально на prod) ===
if [ "$PROD_HOST" = "localhost" ] || [ "$PROD_HOST" = "127.0.0.1" ]; then
    DISK_USAGE=$(df / 2>/dev/null | awk 'NR==2 {gsub("%",""); print $5}')
    MEM_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3/$2*100}')

    if [ "${DISK_USAGE:-0}" -gt 80 ]; then
        send_telegram "💾 *Disk usage high*

Host: \`${PROD_HOST}\`
Disk: \`${DISK_USAGE}%\` (threshold 80%)
Time: \`$(date -u)\`"
    fi

    if [ "${MEM_USAGE:-0}" -gt 80 ]; then
        send_telegram "🧠 *Memory usage high*

Host: \`${PROD_HOST}\`
Memory: \`${MEM_USAGE}%\` (threshold 80%)
Time: \`$(date -u)\`"
    fi
fi

# === Сохраняем состояние ===
PREVIOUS_STATE="unknown"
if [ -f "$STATE_FILE" ]; then
    PREVIOUS_STATE=$(cat "$STATE_FILE")
fi

if [ "$CURRENT_STATE" != "$PREVIOUS_STATE" ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) state: $PREVIOUS_STATE -> $CURRENT_STATE (http=$HTTP_CODE)" >> /var/log/ai-tutor-monitor.log
fi
echo -n "$CURRENT_STATE" > "$STATE_FILE"

# === Recovery ===
if [ "$CURRENT_STATE" = "ok" ] && [ "$PREVIOUS_STATE" = "down" ]; then
    send_telegram "✅ *AI-репетитор RECOVERED*

Host: \`${PROD_HOST}\`
Health: OK (was down)
Time: \`$(date -u)\`"
fi

# === Логируем ===
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) healthcheck: http=$HTTP_CODE state=$CURRENT_STATE backup_age_h=${BACKUP_AGE_HOURS:-n/a}" >> /var/log/ai-tutor-monitor.log
