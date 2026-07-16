#!/bin/bash
# Sprint 3.5 — единая команда для CI/CD: deploy.sh + smoke.sh.
# GitHub Actions runner делает:
#   rsync -avz ./ root@PROD:/tmp/ai-tutor-ci-staging/  (через ssh-agent)
#   ssh root@PROD "/opt/ai-tutor/deploy/release/deploy-from-ci.sh /tmp/ai-tutor-ci-staging"
# А этот скрипт делает всё остальное: rsync staging → release, deploy.sh, smoke.sh.

set -euo pipefail

STAGING="${1:-/tmp/ai-tutor-ci-staging}"
RELEASE_DIR="/opt/ai-tutor"

log() { printf "%s %s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

if [ ! -d "$STAGING" ]; then
  echo "ERROR: staging dir $STAGING not found" >&2
  exit 1
fi

log "CI-DEPLOY: rsync $STAGING → $RELEASE_DIR ..."
# Используем rsync уже установленный (есть на проде из deploy.sh).
# Исключаем то что не должно попадать в release dir.
rsync -a --delete \
  --exclude=/deploy/release/releases \
  --exclude=/deploy/release/snapshots \
  --exclude=/.venv --exclude=__pycache__ --exclude=.next \
  --exclude=node_modules --exclude=uploads --exclude=.git \
  --exclude=.pytest_cache --exclude=.ssh --exclude=*.log \
  "$STAGING/" "$RELEASE_DIR/"

log "CI-DEPLOY: запускаю deploy.sh ..."
bash /opt/ai-tutor/deploy/release/deploy.sh 2>&1 | tee /var/log/ai-tutor-ci-deploy.log

log "CI-DEPLOY: запускаю smoke.sh ..."
bash /opt/ai-tutor/deploy/release/smoke.sh 2>&1 | tee /var/log/ai-tutor-ci-smoke.log

log "CI-DEPLOY: готово."
