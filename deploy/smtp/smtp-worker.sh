#!/bin/bash
# SMTP worker: периодически отправляет queued email-уведомления.
# Использование: каждые 5 минут через cron.
#
# Обрабатывает:
#   - status = "queued" (новые уведомления, созданные вне send_email)
#   - status = "failed" (повторно после transient ошибки)
#   - status = "dry_run" — только если SMTP_URL задан
#
# Cron: */5 * * * * /opt/ai-tutor/deploy/smtp/worker.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOCKER_DIR="$SCRIPT_DIR/../"
LOG="/var/log/ai-tutor-smtp-worker.log"

cd "$DOCKER_DIR" || exit 1

# Проверяем что SMTP_URL задан
if [ -z "${SMTP_URL:-}" ] && ! grep -q "^SMTP_URL=" .env 2>/dev/null; then
    echo "[$(date -Iseconds)] SMTP_URL не задан, worker спит" >> "$LOG"
    exit 0
fi

# Получаем queued/failed email-уведомления старше 1 минуты (даём время на retry)
RECORDS=$(docker compose exec -T db psql -U tutor -d tutor -tA -c "
SELECT id || '|' || user_id || '|' || to_email || '|' || subject || '|' || body
FROM email_notifications
WHERE status IN ('queued', 'failed')
  AND (created_at < NOW() - INTERVAL '1 minute')
ORDER BY created_at ASC
LIMIT 10;
" 2>/dev/null)

if [ -z "$RECORDS" ]; then
    exit 0
fi

SENT=0
FAILED=0
while IFS='|' read -r id uid email subj body; do
    [ -z "$id" ] && continue
    # Отправляем через backend (использует SMTP_URL из env backend'а)
    RESULT=$(docker compose exec -T backend python3 -c "
import asyncio
import sys
sys.path.insert(0, '/app')
from app.db.session import SessionLocal
from app.notifications import service, models

async def send():
    s = SessionLocal()
    try:
        rec = await service.send_email(
            s, user_id=$uid, to_email='$email',
            subject='$subj', body='$body'
        )
        print(f'OK|{rec.status}')
    except Exception as e:
        print(f'ERR|{type(e).__name__}: {e}')
    finally:
        s.close()

asyncio.run(send())
" 2>&1 | tail -1)

    if echo "$RESULT" | grep -q "^OK|sent"; then
        SENT=$((SENT + 1))
    else
        FAILED=$((FAILED + 1))
    fi
done <<< "$RECORDS"

echo "[$(date -Iseconds)] SMTP worker: sent=$SENT failed=$FAILED" >> "$LOG"
