#!/usr/bin/env bash
set -euo pipefail

echo "# AI-Tutor Disk Report"
date -Is

echo

echo "## Filesystems"
df -hT / /opt /var/lib/docker 2>/dev/null || df -hT /

echo

echo "## Docker system df"
docker system df || true

echo

echo "## Top /opt entries"
du -xhd1 /opt 2>/dev/null | sort -h | tail -30 || true

echo

echo "## AI-Tutor backup output"
if [ -d /opt/ai-tutor/deploy/backup/_out ]; then
  du -sh /opt/ai-tutor/deploy/backup/_out || true
  ls -1t /opt/ai-tutor/deploy/backup/_out/manifest-*.md5 2>/dev/null | head -10 || true
else
  echo "backup _out directory not found"
fi

echo

echo "## Docker dangling volumes (inspect before prune)"
docker volume ls -qf dangling=true | xargs -r docker volume inspect --format '{{.Name}} {{.Mountpoint}}' || true

echo

echo "## Journald usage"
journalctl --disk-usage || true

echo

echo "## AI-Tutor services"
if [ -d /opt/ai-tutor/deploy ]; then
  (cd /opt/ai-tutor/deploy && docker compose ps backend frontend db redis prometheus) || true
fi
