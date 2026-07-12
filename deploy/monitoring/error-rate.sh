#!/bin/bash
# Error rate monitor: считает ERROR/500/Traceback в логах backend за последние 5 минут.
# Алерт если > 5 ошибок (порог настраиваемый).

set -uo pipefail

BACKEND_CONTAINER="${BACKEND_CONTAINER:-deploy-backend-1}"
WINDOW_MIN="${WINDOW_MIN:-5}"
ERROR_THRESHOLD="${ERROR_THRESHOLD:-5}"

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
STATE_DIR="/var/lib/ai-tutor-monitor"
ERROR_STATE="$STATE_DIR/last_error_alert"

mkdir -p "$STATE_DIR"

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
    local cooldown="${2:-900}"  # 15 мин между алертами

    if [ -f "$state_file" ]; then
        local last=$(cat "$state_file")
        local now=$(date +%s)
        local diff=$((now - last))
        if [ "$diff" -lt "$cooldown" ]; then
            return 1
        fi
    fi
    echo "$(date +%s)" > "$state_file"
    return 0
}

# Получаем ошибки из backend logs за последние N минут
ERROR_COUNT=$(docker logs --since="${WINDOW_MIN}m" "$BACKEND_CONTAINER" 2>&1 | \
    grep -cE "ERROR|Traceback|HTTP/1.1\" 5[0-9][0-9]" 2>/dev/null | head -1)
ERROR_COUNT=$(echo "$ERROR_COUNT" | tr -d '[:space:]')
ERROR_COUNT=${ERROR_COUNT:-0}

if [ "$ERROR_COUNT" -gt "$ERROR_THRESHOLD" ]; then
    if should_alert "$ERROR_STATE" 900; then
        # Получаем последние 5 ошибок для контекста
        RECENT=$(docker logs --since="${WINDOW_MIN}m" "$BACKEND_CONTAINER" 2>&1 | \
            grep -E "ERROR|Traceback|HTTP/1.1\" 5[0-9][0-9]" | tail -5 | \
            head -c 500)
        send_telegram "🔥 *Backend errors spike*

Container: \`${BACKEND_CONTAINER}\`
Errors in last ${WINDOW_MIN}m: \`${ERROR_COUNT}\` (threshold: ${ERROR_THRESHOLD})

Recent errors:
\`\`\`
${RECENT}
\`\`\`
Time: \`$(date -u)\`"
    fi
fi

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) error_check: ${ERROR_COUNT} errors in ${WINDOW_MIN}m" >> /var/log/ai-tutor-monitor.log
