#!/bin/bash
# Sprint 7.3 — установка self-signed CA в trust store клиентов.
#
# Проблема: self-signed сертификат показывает предупреждение в браузере
# каждый раз. Для production-ready UX без публичного домена — устанавливаем
# наш CA как trusted на клиентских устройствах.
#
# Использование:
#   1. На проде: bash deploy/ssl/install-ca-on-client.sh /path/to/cert.pem
#   2. Скопировать сертификат на клиент
#   3. Запустить на клиенте с sudo:
#      - macOS: sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain cert.pem
#      - Linux: sudo cp cert.pem /usr/local/share/ca-certificates/ai-tutor.crt && sudo update-ca-certificates
#      - Windows: mmc → Certificates → Trusted Root → Import
#      - iOS/Android: Settings → Profile → Install (для мобильных)
#
# Безопасность:
# - CA подписывает ТОЛЬКО наш сертификат 192.168.1.86
# - Если злоумышленник получит доступ к этому CA, он сможет MITM только LAN-сети

set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <path-to-ca-or-cert.pem>"
    exit 1
fi

CERT_PATH="$1"
if [ ! -f "$CERT_PATH" ]; then
    echo "Error: $CERT_PATH not found"
    exit 1
fi

# Detect OS
OS=$(uname -s)
case "$OS" in
    Darwin)
        # macOS
        echo "🔒 macOS detected. Adding certificate to System keychain..."
        sudo security add-trusted-cert -d -r trustRoot \
            -k /Library/Keychains/System.keychain "$CERT_PATH"
        echo "✅ Certificate added. Restart browser to apply."
        ;;
    Linux)
        # Linux (Debian/Ubuntu)
        echo "🔒 Linux detected. Adding certificate to system trust store..."
        sudo cp "$CERT_PATH" /usr/local/share/ca-certificates/ai-tutor.crt
        sudo update-ca-certificates
        echo "✅ Certificate added. Restart browser to apply."
        ;;
    MINGW*|CYGWIN*|MSYS*)
        # Windows (через Git Bash)
        echo "🔒 Windows detected."
        echo "Run in PowerShell as Administrator:"
        echo "  Import-Certificate -FilePath '$CERT_PATH' -CertStoreLocation Cert:\LocalMachine\Root"
        ;;
    *)
        echo "Unknown OS: $OS"
        echo "Manual install: copy to your OS trust store and mark as trusted."
        exit 1
        ;;
esac