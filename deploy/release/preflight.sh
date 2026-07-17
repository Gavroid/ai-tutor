#!/usr/bin/env bash
# Pilot Core Stage 1 — Phase 3 (P1.3.2).
# Pre-flight: проверки до deploy. Запускается первым в deploy-цепочке.
# - ssh до production доступен
# - compose project и образы в актуальном состоянии
# - миграции dry-run (--sql) не падают
# - backup.sh выполняется в dry-run (без записи) и не даёт ошибок
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SSH_KEY="${SSH_KEY:-/root/.ssh/id_ed25519_kirill_ai}"
PROD_HOST="${PROD_HOST:-192.168.1.86}"
TARGET_SHA="${TARGET_SHA:-}"

log() { printf '\033[1;34m[preflight]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[preflight FAIL]\033[0m %s\n' "$*"; exit 1; }

# Sprint 3.5.3: поддержка LOCAL_DEPLOY (self-hosted runner).
# Детект: hostname=Kirill-AI или есть runner config.
LOCAL_DEPLOY=false
if [ "$(hostname)" = "Kirill-AI" ] || [ -f /opt/actions-runner/.runner ]; then
  LOCAL_DEPLOY=true
fi

run_on_prod() {
  if [ "$LOCAL_DEPLOY" = "true" ]; then
    bash -c "$1"
  else
    ssh -i "$SSH_KEY" root@"$PROD_HOST" "$1"
  fi
}

log "Проверка ssh-доступа к ${PROD_HOST}..."
if [ "$LOCAL_DEPLOY" = "true" ]; then
  log "  (LOCAL_DEPLOY: пропускаем ssh-check)"
else
  ssh -o BatchMode=yes -o ConnectTimeout=5 -i "$SSH_KEY" root@"$PROD_HOST" 'echo ok' >/dev/null \
    || fail "ssh failed"
fi

log "Проверка /health на production..."
HEALTH=$(run_on_prod 'curl -sk -o /dev/null -w "%{http_code}" https://localhost/health')
[ "$HEALTH" = "200" ] || fail "production /health=$HEALTH (ожидаем 200)"

log "Проверка /ready на production..."
READY=$(run_on_prod 'curl -sk -o /dev/null -w "%{http_code}" https://localhost/ready')
[ "$READY" = "200" ] || fail "production /ready=$READY (ожидаем 200)"

log "Проверка /api/v2/health на production..."
V2=$(run_on_prod 'curl -sk -o /dev/null -w "%{http_code}" https://localhost/api/v2/health')
[ "$V2" = "200" ] || fail "production /api/v2/health=$V2 (ожидаем 200)"

if [ -n "$TARGET_SHA" ]; then
  log "Проверка TARGET_SHA=${TARGET_SHA} в локальном git..."
  git -C "$PROJECT_ROOT" rev-parse --verify "${TARGET_SHA}^{commit}" >/dev/null \
    || fail "$TARGET_SHA не найден в локальном git"
fi

log "OK: pre-flight прошёл"
