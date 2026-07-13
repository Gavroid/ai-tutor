# Развёртывание

## Вариант A: Proxmox LXC (быстро)

1. Создать Ubuntu 24.04 LXC с `nesting=1` (нужно для Docker).
2. Зайти внутрь, установить Docker.
3. Склонировать репозиторий.
4. Настроить `.env`.
5. `make up`.

⚠️ Docker внутри LXC требует небезопасных привилегий.
Для прод-варианта предпочтительнее VM.

## Вариант B: Proxmox VM (рекомендуется)

1. Создать VM Ubuntu Server 24.04.
2. Внутри: `apt update && apt install -y docker.io docker-compose-plugin`.
3. Склонировать репозиторий.
4. Настроить `.env`, `make up`.
5. Открыть наружу 80/443 через ufw:
   ```bash
   ufw allow OpenSSH
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw enable
   ```

## DNS и HTTPS (Этап 12)

- Домен → A-запись на внешний IP Proxmox-узла.
- Сертификат Let's Encrypt через certbot в отдельном контейнере
  или через Caddy как front-proxy.
- Nginx настраивается на 443 + редирект 80→443.

## Бэкап

Pilot Core Stage 1 — P1.3.1: backup paths согласованы.

- `BACKUP_ROOT` (canonical): `/opt/ai-tutor/deploy/backup/_out` — `backup.sh` пишет сюда.
- `BACKUP_OFFSITE_DEST` (default): `/var/backups/ai-tutor` — `ai-tutor-backup-offsite.sh` копирует сюда.
  ВАЖНО: в Pilot Core это **НЕ offsite** (тот же LXC, та же FS). Настоящий offsite (SMB/NAS) подключается в Phase 4.
- `test-restore.sh` (Sprint 10.4) читает backup из того же каталога `/opt/ai-tutor/deploy/backup/_out`.

```bash
# Ежедневно, по cron:
0 3 * * * /opt/ai-tutor/deploy/backup/backup.sh >> /var/log/ai-tutor-backup.log 2>&1
0 3 * * * /usr/local/bin/ai-tutor-backup-offsite.sh >> /var/log/ai-tutor-backup.log 2>&1
```

Восстановление после сбоя:
1. Поднять VM/LXC с нуля.
2. Установить Docker.
3. Склонировать репозиторий.
4. `make up` (без `--build` если образы сохранены локально).
5. `./deploy/backup/backup.sh --restore deploy/backup/_out/db-<ts>.sql.gz`.

## Atomic deploy / rollback / smoke (Pilot Core P1.3.2–P1.3.4)

Pilot Core Stage 1 release pipeline — `deploy/release/{preflight,deploy,rollback,smoke}.sh`.

```bash
# На локальной машине (workspace):

# 1) pre-flight: ssh + базовые health-check
bash deploy/release/preflight.sh

# 2) deploy (tar-pipe, build, up, wait for /health, migrate)
bash deploy/release/deploy.sh                  # текущий HEAD
bash deploy/release/deploy.sh 72188f9           # явно с commit SHA

# 3) smoke (health, auth, secure exercise, backup age)
bash deploy/release/smoke.sh

# 4) rollback (использует /tmp/ai-tutor-prev-sha.txt от deploy.sh)
bash deploy/release/rollback.sh                 # из marker-файла
bash deploy/release/rollback.sh 72188f9          # явно с known-good SHA
```

Особенности:
- `deploy.sh` сохраняет prev SHA в `/tmp/ai-tutor-prev-sha.txt` (на рабочей машине).
- `rollback.sh` использует latest backup из `deploy/backup/_out/` — restore через `backup.sh --restore` + rebuild + up.
- `smoke.sh` проверяет `/health`, `/ready`, `/api/v2/health`, `/auth/register` positive+negative, `/api/v2/exercises/{generate,answer}` без `correct_answer` в ответе, и backup age < 26ч.
- На production-хосте `git` НЕ установлен (Phase 4 — внешний Git remote). Поэтому `deploy.sh` копирует **код через tar**, а `rollback.sh` восстанавливает **БД из backup**. Точечный откат одного файла невозможен — только полный tar + DB restore.

RTO (цель): ≤ 60 минут (deploy ~ 10 мин + restore ~ 5 мин в типичном случае).
RPO (цель): ≤ 26 часов (backup предыдущей ночи).


## Мониторинг (Этап 12, TODO)

- Внутренний: `/health`, `/ready` для Proxmox/LXC watchdog.
- Prometheus + Grafana (опционально).
- Логи backend → Loki/journald.