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

```bash
# Ежедневно, по cron:
0 3 * * * /opt/ai-tutor/deploy/backup/backup.sh >> /var/log/ai-tutor-backup.log 2>&1
```

Восстановление после сбоя:
1. Поднять VM/LXC с нуля.
2. Установить Docker.
3. Склонировать репозиторий.
4. `make up` (без `--build` если образы сохранены локально).
5. `./deploy/backup/backup.sh --restore deploy/backup/_out/db-<ts>.sql.gz`.

## Мониторинг (Этап 12, TODO)

- Внутренний: `/health`, `/ready` для Proxmox/LXC watchdog.
- Prometheus + Grafana (опционально).
- Логи backend → Loki/journald.