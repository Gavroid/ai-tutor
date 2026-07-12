#!/bin/bash
# Тест SMTP подключения.
# Использование:
#   SMTP_URL="smtp://user:pass@smtp.example.com:587" bash test-smtp.sh

set -e

: "${SMTP_URL:?SMTP_URL не задан. Пример: smtp://user:pass@smtp.example.com:587}"

# Парсим URL
REGEX="^smtp://([^:]+):([^@]+)@([^:]+):([0-9]+)$"
if [[ "$SMTP_URL" =~ $REGEX ]]; then
    USER="${BASH_REMATCH[1]}"
    PASS="${BASH_REMATCH[2]}"
    HOST="${BASH_REMATCH[3]}"
    PORT="${BASH_REMATCH[4]}"
    echo "Parsed: user=$USER, host=$HOST, port=$PORT"
else
    echo "Невалидный формат SMTP_URL. Ожидается: smtp://user:pass@host:port"
    exit 1
fi

# Проверяем через docker exec backend (там уже установлены python и aiosmtplib)
echo "Тестируем подключение через backend контейнер..."
docker compose exec -T backend python3 << EOF
import asyncio
import os
import sys

SMTP_URL = "$SMTP_URL"

async def test():
    try:
        # Простая попытка подключения
        import smtplib
        from urllib.parse import urlparse

        parsed = urlparse(SMTP_URL)
        host = parsed.hostname
        port = parsed.port or 587
        user = parsed.username
        password = parsed.password

        with smtplib.SMTP(host=host, port=port, timeout=10) as s:
            s.starttls()
            s.login(user, password)
            print(f"OK: SMTP connection works to {host}:{port} as {user}")
            return 0
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

sys.exit(asyncio.run(test()))
EOF
