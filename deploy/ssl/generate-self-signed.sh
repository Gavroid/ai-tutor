#!/bin/bash
# Генерация self-signed SSL для LXC (192.168.1.86).
# Для production с реальным доменом используйте Let's Encrypt (certbot).
#
# Использование:
#   bash deploy/ssl/generate-self-signed.sh
#
# Результат:
#   deploy/ssl/certs/fullchain.pem
#   deploy/ssl/certs/privkey.pem

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CERT_DIR="$SCRIPT_DIR/certs"
mkdir -p "$CERT_DIR"

CN="${1:-192.168.1.86}"
DAYS=825  # максимум для браузеров (Chrome >= 825 дней)

echo "Генерирую self-signed сертификат для CN=$CN (на $DAYS дней)..."

openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "$CERT_DIR/privkey.pem" \
    -out "$CERT_DIR/fullchain.pem" \
    -days "$DAYS" \
    -subj "/C=RU/ST=Moscow/L=Moscow/O=AI-Tutor/CN=$CN" \
    -addext "subjectAltName=IP:192.168.1.86,DNS:localhost,DNS:kirill-ai.local"

chmod 600 "$CERT_DIR/privkey.pem"
chmod 644 "$CERT_DIR/fullchain.pem"

echo "OK. Сертификаты:"
ls -la "$CERT_DIR"
echo
echo "Для клиентов без предупреждения браузера — установи CA на устройствах:"
echo "  bash $SCRIPT_DIR/install-ca-on-client.sh $CERT_DIR/fullchain.pem"
echo
echo "Подключи HTTPS в docker-compose (раскомментируй volume):"
echo "  ./ssl/certs:/etc/nginx/certs:ro"
echo
echo "И обнови nginx.conf для listen 443 ssl;"