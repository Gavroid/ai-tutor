# Sprint 18 P1-11 — Self-hosted runner под non-root

**Дата:** 2026-07-24
**Цель:** Уменьшить blast radius — если attacker получит контроль над workflow, он не сможет делать root-операции на production.

## Что сделано

### 1. Создана группа `app-secrets`
```bash
groupadd app-secrets
usermod -aG app-secrets runner
```

### 2. /opt/ai-tutor/.env доступ
```bash
chgrp app-secrets /opt/ai-tutor/.env
chmod 640 /opt/ai-tutor/.env
```

Runner читает `.env` (нужно для `source /opt/ai-tutor/.env` в deploy.sh), но НЕ может его модифицировать. **Best practice**.

### 3. Runner в группе `docker`
```bash
usermod -aG docker runner
```

Runner может `docker ps`, `docker exec`, `docker restart` без sudo.

### 4. Directories writable для runner
```bash
chown -R runner:runner /opt/ai-tutor/deploy/release/releases/
mkdir -p /opt/ai-tutor/deploy/release/rollback_backup/
chown -R runner:runner /opt/ai-tutor/deploy/release/rollback_backup/
touch /var/log/ai-tutor-deploy.log
chown runner:runner /var/log/ai-tutor-deploy.log
```

### 5. Systemd unit
```ini
[Service]
User=runner          # было: root
Group=runner         # было: (пусто)
WorkingDirectory=/opt/actions-runner
ExecStart=/opt/actions-runner/runsvc.sh
```

## Результат

```
$ systemctl show actions.runner... --property=User,Group
User=runner
Group=runner

$ ps aux | grep Runner.Listener
runner  117333  /opt/actions-runner/bin/Runner.Listener ...

$ id runner
uid=1000(runner) gid=1000(runner) groups=1000(runner),990(docker),1001(app-secrets)
```

## Что runner МОЖЕТ

- ✅ `docker ps`, `docker exec`, `docker restart`
- ✅ `docker exec deploy-backend-1 alembic upgrade head`
- ✅ `docker exec deploy-backend-1 curl http://localhost:8000/health`
- ✅ Запись в `/opt/ai-tutor/deploy/release/releases/`
- ✅ Запись в `/var/log/ai-tutor-deploy.log`
- ✅ Чтение `/opt/ai-tutor/.env`

## Что runner НЕ МОЖЕТ

- ❌ `sudo` (нет в sudoers)
- ❌ Редактирование `/etc/cron.d/`
- ❌ Редактирование `/etc/systemd/system/`
- ❌ Удаление `/opt/ai-tutor/deploy/release/deploy.sh`
- ❌ Изменение `/opt/ai-tutor/.env`
- ❌ Запись вне `/opt/ai-tutor/deploy/release/releases/` и `/var/log/ai-tutor-deploy.log`

## Что нужно для Sprint 19+

- **Systemd** services (proxy, backend, frontend) — root required для restart. Эти операции выполняются **внутри** deploy.sh через `docker restart` (runner может). ✅
- **Cron edit** — root only. deploy.sh **не трогает** cron. ✅
- **apt-get update/upgrade** — не делается в deploy (только image-based). ✅

## Rollback

Если что-то сломается, вернуть root:
```bash
cp /etc/systemd/system/actions.runner.Gavroid-ai-tutor.kirill-ai-prod.service.bak \
   /etc/systemd/system/actions.runner.Gavroid-ai-tutor.kirill-ai-prod.service
systemctl daemon-reload
systemctl restart actions.runner.Gavroid-ai-tutor.kirill-ai-prod.service
```

Файл `.bak` сохранён на проде.