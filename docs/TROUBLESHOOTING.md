# Troubleshooting Guide

**Дата:** 2026-07-26
**Production:** 192.168.1.86 (LXC, 4GB RAM)

## 🔧 Common Issues

### Issue 1: Container unhealthy

**Symptoms:**
- `curl https://localhost/health` → 000
- Grafana: red panels
- Telegram alerts: 5xx spike

**Diagnosis:**
```bash
ssh root@192.168.1.86
docker ps -a --format "table {{.Names}}\t{{.Status}}"
docker logs deploy-backend-1 --tail 50
```

**Solutions:**
- If "Exited (1)": check logs, fix issue, `docker compose up -d backend`
- If "Restarting": check OOM (`dmesg | grep -i oom`)
- If "Health: starting" >60s: зависимость (PostgreSQL) не готова

---

### Issue 2: Database connection lost

**Symptoms:**
- 500 errors с "connection refused"
- Logs: "OperationalError: could not connect to server"

**Diagnosis:**
```bash
ssh root@192.168.1.86
docker exec deploy-db-1 pg_isready
docker logs deploy-db-1 --tail 30
```

**Solutions:**
```bash
# Restart DB
docker compose restart db

# If persistent, check disk
df -h /opt/ai-tutor

# Check PostgreSQL logs
docker exec deploy-db-1 tail -50 /var/log/postgresql/*.log
```

---

### Issue 3: Frontend build failed

**Symptoms:**
- `npm run build` failed в Docker
- Frontend container exited

**Diagnosis:**
```bash
ssh root@192.168.1.86
cd /opt/ai-tutor/deploy
docker compose build frontend 2>&1 | tail -30
```

**Common errors:**
- `useSearchParams() should be wrapped in a suspense boundary` — wrap in `<Suspense>` (Sprint 52 fix)
- `Module not found` — check if rsync скопировал все файлы
- `Turbopack panic` — clear `.next/` and rebuild

**Solutions:**
```bash
# Clear .next cache
docker exec deploy-frontend-1 rm -rf /app/.next

# Rebuild with no cache
docker compose build --no-cache frontend
docker compose up -d frontend
```

---

### Issue 4: Telegram alerts spam

**Symptoms:**
- Telegram: 10+ alerts в минуту
- Alert queue overflow в Redis

**Solutions:**
- Alert worker (Sprint 50) имеет dedupe (5 мин TTL)
- Если всё ещё spam — проверить rate limit (Sprint 16.1)
- Возможно Redis down — check `docker exec deploy-redis-1 redis-cli ping`

---

### Issue 5: High memory usage

**Symptoms:**
- Backend использует >800MiB
- OOM kills в `dmesg`

**Diagnosis:**
```bash
ssh root@192.168.1.86
free -h
docker stats --no-stream
```

**Solutions:**
- Restart backend (memory leak в uvicorn): `docker compose restart backend`
- Если persistent — Sprint 30 multi-worker настроен (4 workers, 230MiB)
- Если всё ещё >500MiB — есть memory leak, check recent commits

---

### Issue 6: WebSocket disconnects

**Symptoms:**
- Чат рвётся каждые 30 сек
- WS reconnect в Telegram alerts

**Diagnosis:**
```bash
ssh root@192.168.1.86
docker logs deploy-backend-1 | grep -i "websocket" | tail -20
```

**Solutions:**
- Check nginx WebSocket upgrade headers (Sprint 38)
- Check uvicorn timeout (default 60s для WS)
- WS heartbeat: 25s (Sprint 22)

---

### Issue 7: Audit log hash chain broken

**Symptoms:**
- GET /audit-log/verify → tampered > 0
- chain_broken_at != None

**Diagnosis:**
- Это CRITICAL — кто-то модифицировал audit log
- Проверить кто имеет DB access
- Восстановить из backup (`/opt/ai-tutor/deploy/backup/_out/`)

**Solutions:**
1. Stop backend (block writes)
2. Inspect modified records
3. Restore from backup OR mark tampered records
4. Re-deploy backend (start fresh hash chain)
5. Document incident в audit log

---

### Issue 8: Grafana dashboard empty

**Symptoms:**
- "No data" panels в Grafana
- Prometheus scrape failing

**Diagnosis:**
```bash
# Check Prometheus targets
ssh root@192.168.1.86
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[].health'
```

**Solutions:**
- `docker compose restart prometheus`
- `docker compose restart grafana`
- Re-import dashboard из `/var/lib/grafana/dashboards/`

---

### Issue 9: Slow response (>1s)

**Symptoms:**
- /metrics показывает high p95 latency
- User complaints о slow loading

**Diagnosis:**
```bash
# Check DB queries
ssh root@192.168.1.86
docker exec deploy-db-1 psql -U tutor -d tutor -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"
```

**Solutions:**
- Identify slow query → add index → re-test
- Sprint 64 запланирован для performance optimization
- Enable query log: `ALTER SYSTEM SET log_min_duration_statement = 100;`

---

### Issue 10: Pilot user can't login

**Symptoms:**
- "Invalid credentials" для known user
- Audit log: много failed login attempts

**Diagnosis:**
```bash
ssh root@192.168.1.86
docker exec deploy-db-1 psql -U tutor -d tutor -c "
SELECT id, email, is_active, role FROM users WHERE email = 'USER@EMAIL';
"
```

**Solutions:**
- `is_active = false` → admin должен `POST /admin/users/{id}/deactivate` (reverse)
- Pilot passwords ВСЕ `Kirill2026!` (Sprint 1)
- Если забыли — admin может reset через DB (НЕ реализовано)

---

## 🆘 Emergency contacts

- **Production down >5 мин**: Telegram @Ai_School_431a_bot (auto alert)
- **Security incident**: немедленно в Telegram chat
- **Data loss**: backup в `/opt/ai-tutor/deploy/backup/_out/manifest-*.md5` (SMB offsite)

## 📚 Logs

```bash
# Backend (Sprint 50+ graceful shutdown)
docker logs deploy-backend-1 --tail 100 -f

# Nginx access log
tail -f /var/log/nginx/access.log

# Alert JSONL
tail -f /var/log/ai-tutor/alerts.jsonl

# Deploy history
tail -f /var/log/ai-tutor-deploy.log
```

## 🔄 Maintenance procedures

### Database migration
```bash
ssh root@192.168.1.86
cd /opt/ai-tutor/deploy

# 1. Backup first
./release/backup.sh  # если exists

# 2. Apply migration (autouse через app startup)
docker compose restart backend

# 3. Verify
docker exec deploy-backend-1 alembic current
```

### Backend deploy
```bash
# 1. На local machine: pull + tests + commit
cd /root/workspace/ai-tutor
git pull
.venv/bin/pytest tests/ -q
git add -A && git commit -m "..." && git push

# 2. На production: rsync + build + restart
ssh root@192.168.1.86
cd /opt/ai-tutor
git pull
rsync -avz --delete --exclude='__pycache__' \
  /root/workspace/ai-tutor/apps/backend/ /opt/ai-tutor/apps/backend/
cd deploy
docker compose build backend
docker compose up -d backend

# 3. Verify
curl https://localhost/health
bash release/smoke.sh
bash release/smoke-extra.sh
```

### Rollback
```bash
ssh root@192.168.1.86
cd /opt/ai-tutor
git log --oneline | head -5
git reset --hard PREVIOUS_COMMIT
cd deploy
docker compose build backend
docker compose up -d backend
```

## 🔗 См. также

- [docs/ADMIN-GUIDE.md](ADMIN-GUIDE.md) — admin operations
- [docs/DEPLOY-GUIDE.md](DEPLOY-GUIDE.md) — production deployment
- [docs/ARCHITECTURE-ADDENDUM.md](ARCHITECTURE-ADDENDUM.md) — Sprint 54 architecture
- [docs/OPENTELEMETRY.md](OPENTELEMETRY.md) — Sprint 62 tracing
- [docs/CHANGELOG-SPRINT-16-56.md](CHANGELOG-SPRINT-16-56.md) — full changelog