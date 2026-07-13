# Proxmox — заметки по запуску (Этап 0+12).
#
# Рекомендация: запускать в Ubuntu 22.04/24.04 LXC с nesting=1 (для Docker),
# или в полноценной VM — последнее безопаснее для Docker.
#
# Важно: НЕ изменяйте /etc/pve, storage, bridge, firewall на хосте Proxmox
# без явного подтверждения пользователя. Все действия — внутри контейнера/VM.

## LXC (рекомендуется)
# На хосте Proxmox (НЕ выполнять без подтверждения):
#   pct create 200 local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst \
#     --hostname ai-tutor --cores 4 --memory 8192 --swap 2048 \
#     --rootfs local-lvm:32 --net0 name=eth0,bridge=vmbr0,ip=dhcp \
#     --features nesting=1 --unprivileged 1 --onboot 1 --start 1
#
# Внутри контейнера:
apt update && apt install -y docker.io docker-compose-plugin curl
systemctl enable --now docker
usermod -aG docker $USER
# Затем см. README → раздел "Локальный запуск".

## VM
# Создать VM с Ubuntu Server 24.04, установить docker, клонировать репозиторий,
# запустить `make up`. Это безопаснее и гибче, чем LXC+Docker.
#
# Firewall внутри VM/контейнера:
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
# PostgreSQL наружу НЕ открывать (и так не светится — публикуется только proxy).

## Известные ограничения unprivileged LXC (без Docker, наша среда)

**Если контейнер запущен в unprivileged mode** (как текущий prod, 4 GB RAM,
swap=0, capabilities включая CAP_SYS_ADMIN):

1. **Docker не работает** (по дизайну unprivileged LXC). Решения:
   - Использовать внешнюю VM/хост для запуска PostgreSQL + Redis.
   - `apt install postgresql-client` + `pg_dump -h <external-host>` для бэкапа.
   - Перейти на **restic** или **borgbackup** для инкрементальных бэкапов
     (вместо `docker exec pg_dump`).

2. **`mount -t cifs` возвращает "Operation not permitted"**, даже с правильными
   capabilities. Workaround — использовать **`smbclient`** напрямую:
   ```bash
   apt install -y cifs-utils smbclient
   smbclient //<server>/<share> -A /etc/samba/creds -c "put <local> <remote>"
   ```
   Пример: бэкап-скрипт `scripts/backup-full.sh` использует `smbclient put`
   вместо `mount.cifs`. Это работает в любом окружении (включая unprivileged LXC).

3. **Сетевые capabilities ограничены.** Если что-то требует raw-socket
   (tcpdump, nmap), запускать в privileged LXC или VM.

**Для production рекомендуется VM** (не LXC) — там этих ограничений нет.