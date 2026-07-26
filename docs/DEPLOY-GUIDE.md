# AI-Tutor Production Deployment Guide

**Дата:** 2026-07-26
**Production:** 192.168.1.86 (LXC, 4GB RAM, Proxmox)
**Stack:** Docker Compose + self-hosted runner + SMB offsite backups

Это руководство описывает **production deployment** workflow для AI-Tutor.

---

## 🏗️ Architecture overview

```
Internet → Nginx Proxy Manager (Игорь)
  ↓
LAN: 192.168.1.86
  ↓
Proxmox LXC "Kirill-AI" (Ubuntu 24.04, 4GB RAM)
  ├── Docker Compose stack (deploy/)
  │   ├── backend (FastAPI, 4 workers, 230MiB)
  │   ├── frontend (Next.js, port 3000)
  │   ├── db (PostgreSQL 16, 120MiB)
  │   ├── redis (5.0, 10MiB)
  │   ├── proxy (Nginx, ports 80/443)
  │   ├── grafana (10.0, 80MiB)
  │   └── prometheus (15MiB)
  │
  ├── /opt/ai-tutor/ (git clone)
  ├── /etc/cron.d/ai-tutor-* (9 cron jobs)
  └── /var/log/ai-tutor/ (logs)
  ↓
SMB offsite backup: //192.168.1.91/Kirill-AI/ai-tutor/
```

---

## 🚀 Initial deployment

### 1. Server preparation (LXC)

```bash
# На Proxmox host:
# - Create LXC: Ubuntu 24.04, 4GB RAM, 20GB disk
# - Enable nesting, FUSE (для Docker)
# - Network: 192.168.1.86/24

# SSH to LXC
ssh root@192.168.1.86

# Update + Docker install
apt update && apt upgrade -y
apt install -y curl git docker.io docker-compose
systemctl enable docker
```

### 2. Create deploy user (non-root runner)

```bash
# Self-hosted runner user (Sprint 18)
useradd -m -s /bin/bash runner
usermod -aG docker runner
usermod -aG app-secrets runner

# Create secrets group (mode 640)
groupadd app-secrets
chown -R root:app-secrets /opt/ai-tutor
chmod 640 /opt/ai-tutor/.env
```

### 3. Clone repository

```bash
mkdir -p /opt/ai-tutor
cd /opt/ai-tutor
git clone https://github.com/Gavroid/ai-tutor.git .
chown -R runner:runner /opt/ai-tutor
```

### 4. Create .env file

```bash
cat > /opt/ai-tutor/.env << 'EOF'
# Secrets (mode 600, group app-secrets)
APP_SECRET_KEY=<random-32-chars>
AI_API_KEY=<sk-...>
TELEGRAM_BOT_TOKEN=<bot-token>
TELEGRAM_ALERT_CHAT_ID=432505767
DATABASE_URL=postgresql+psycopg2://tutor:password@db:5432/tutor
UPLOAD_DIR=/app/uploads
APP_ENV=production
APP_DEBUG=false
CORS_ORIGINS=https://school.431a.ru,http://localhost:3000
NEXT_PUBLIC_API_URL=https://school.431a.ru
EOF

chmod 640 /opt/ai-tutor/.env
chown root:app-secrets /opt/ai-tutor/.env
```

### 5. First deploy

```bash
cd /opt/ai-tutor/deploy
docker compose up -d db redis  # start dependencies first
sleep 10  # wait for db
docker compose up -d backend
docker compose run --rm backend alembic upgrade head  # run migrations
docker compose up -d frontend proxy grafana prometheus
sleep 30

# Verify
curl http://localhost/health
bash release/smoke.sh
```

### 6. Setup self-hosted runner

```bash
# На GitHub: Settings → Actions → Runners → New self-hosted runner
# Follow instructions for Linux x64

# Конфигурация:
# - Labels: self-hosted, ai-tutor, production
# - Work directory: /opt/actions-runner
# - User: runner (non-root)

su - runner
mkdir -p ~/actions-runner && cd ~/actions-runner
# Download + configure (from GitHub instructions)
./config.sh --url https://github.com/Gavroid/ai-tutor --token <TOKEN>
sudo ./svc.sh install runner
sudo ./svc.sh start
```

### 7. Setup cron jobs

```bash
# Backup cron (Sprint 6, daily 02:00)
cat > /etc/cron.d/ai-tutor-backup << 'EOF'
0 2 * * * root /opt/ai-tutor/deploy/release/backup.sh >> /var/log/ai-tutor-backup.log 2>&1
EOF

# Audit log retention (Sprint 4.2, daily 03:00)
cat > /etc/cron.d/ai-tutor-audit-cleanup << 'EOF'
0 3 * * * root cd /opt/ai-tutor/apps/backend && .venv/bin/python scripts/audit_cleanup.py >> /var/log/ai-tutor-audit.log 2>&1
EOF

# Alert worker (continuous)
cat > /etc/systemd/system/ai-tutor-alert-worker.service << 'EOF'
[Unit]
Description=AI Tutor Telegram Alert Worker
After=network.target redis.service

[Service]
Type=simple
User=runner
WorkingDirectory=/opt/ai-tutor/apps/backend
Environment="PATH=/opt/ai-tutor/apps/backend/.venv/bin"
ExecStart=/opt/ai-tutor/apps/backend/.venv/bin/python -m app.bot.alert_worker
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl enable ai-tutor-alert-worker
systemctl start ai-tutor-alert-worker
```

### 8. Setup SMB offsite backup

```bash
# Install cifs-utils
apt install -y cifs-utils

# Mount SMB share
cat > /etc/cifs-credentials << 'EOF'
username=backup-user
password=<password>
EOF
chmod 600 /etc/cifs-credentials

# /etc/fstab
//192.168.1.91/Kirill-AI /mnt/smb-offsite cifs credentials=/etc/cifs-credentials,uid=root,gid=root 0 0

mkdir -p /mnt/smb-offsite
mount /mnt/smb-offsite
```

---

## 🔄 Continuous deployment

### Option A: Manual (recommended for production)

```bash
# 1. Local development
cd /root/workspace/ai-tutor
git pull
.venv/bin/pytest tests/ -q
git add -A
git commit -m "Sprint X: feature"
git push origin main

# 2. Deploy to production
ssh root@192.168.1.86
cd /opt/ai-tutor
git pull
rsync -avz --delete --exclude='__pycache__' \
  /root/workspace/ai-tutor/apps/backend/ /opt/ai-tutor/apps/backend/
cd deploy
docker compose build backend
docker compose up -d backend
sleep 30

# 3. Verify
bash release/smoke.sh
bash release/smoke-extra.sh
```

### Option B: CI/CD via GitHub Actions

⚠️ **Manual approval required** (Sprint 17)

```yaml
# .github/workflows/deploy.yml (уже настроен)
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deploy to environment'
        required: true
        default: 'production'

jobs:
  deploy:
    runs-on: [self-hosted, ai-tutor]
    environment: production  # requires manual approval
    steps:
      - uses: actions/checkout@v4
      - name: rsync + rebuild
        run: ./deploy/release/deploy.sh
```

---

## 📊 Production monitoring

### Prometheus metrics

```bash
# All custom metrics
curl http://localhost:8000/metrics | grep -E "^parent_|^http_requests_|^ai_"
```

**Custom Sprint 49 metrics:**
- `parent_streak_current_streak_days{user_id}`
- `parent_streak_longest_streak_days{user_id}`
- `parent_attempts_total{user_id, day}`
- `parent_session_pauses_total{user_id, reason}`
- `parent_session_duration_seconds_bucket{le}`

### Grafana dashboards

- https://school.431a.ru/grafana (provisioned)
- 3 dashboards:
  - ai-tutor-overview (Sprint 9.2)
  - parent-dashboard (Sprint 39 + 49)
  - system-overview (Sprint 39)

### OpenTelemetry traces (Sprint 62)

Console exporter → `/var/log/ai-tutor-deploy.log` (Sprint 62)
OTLP exporter → `OTEL_EXPORTER_OTLP_ENDPOINT=...` (optional)

---

## 🔒 Security

### Secrets management
- `.env` mode 640, group `app-secrets`
- `runner` user в группе `app-secrets`
- ВСЕ commits проверяются: `git ls-files | grep -E '^\.env$'`

### SSH keys
- Self-hosted runner: ed25519 ключ
- Production: ed25519 ключ для root@192.168.1.86

### Firewall
- LXC: только 80/443 (Nginx Proxy Manager)
- Docker internal network: backend/frontend/db/redis/grafana/prometheus

### Audit
- 5xx → Telegram alerts (Sprint 16.0)
- Audit log hash chain (Sprint 45)
- Cookie auth (Sprint 27)

---

## 🗄️ Database

### Backups
- Daily 02:00 (cron)
- Pre-deploy backup (manual)
- 30-day retention (rotation script)
- SMB offsite (//192.168.1.91/Kirill-AI/)
- Hash verified (SHA-256)

### Migrations
- Alembic в `apps/backend/alembic/versions/`
- 21 миграций (Sprint 14-45)
- Применяются: `docker compose run --rm backend alembic upgrade head`

### Restore from backup
```bash
ssh root@192.168.1.86
ls /opt/ai-tutor/deploy/backup/_out/  # or /mnt/smb-offsite/

# Restore
gunzip < db-20260724T120000Z.sql.gz | \
  docker exec -i deploy-db-1 psql -U tutor -d tutor
```

---

## 🔧 Scaling

### Multi-worker uvicorn (Sprint 30)
```bash
# Current: 4 workers (--workers 4)
# Memory: ~230MiB / 4GiB (5.6%)
# p95 latency: 8.3ms (load test 50 concurrent)

# Scale up: 8 workers (need 8GB RAM)
docker compose up -d --scale backend=2  # 2 containers × 4 workers = 8
```

### Vertical scaling (если упёрлись в RAM)
```bash
# На Proxmox: LXC memory 4GB → 8GB
# Стоимость: ~$2-5/мес на Proxmox
# Позволит: real RAG embeddings (sentence-transformers)
```

---

## 📝 См. также

- [docs/ADMIN-GUIDE.md](ADMIN-GUIDE.md) — admin operations
- [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) — common issues
- [docs/ARCHITECTURE-ADDENDUM.md](ARCHITECTURE-ADDENDUM.md) — Sprint 54 architecture
- [docs/CHANGELOG-SPRINT-16-56.md](CHANGELOG-SPRINT-16-56.md) — full changelog
- [docs/security.md](security.md) — security model