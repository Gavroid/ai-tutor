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