# Поднятие ресурсов LXC-контейнера 192.168.1.86 (Kirill-AI)
# для запуска AI-репетитора (PostgreSQL + FastAPI + Next.js + Nginx).
#
# ⚠️ Эти команды нужно выполнять **на хосте Proxmox** (НЕ внутри контейнера).
# Если у тебя нет shell-доступа к хосту — выполни их через веб-интерфейс
# Proxmox: Datacenter → Node → CT 100xxxx → Resources → Memory / CPUs / Swap.
#
# Перед выполнением:
#   1. Останови контейнер: pct stop <CTID>
#   2. Измени ресурсы:    pct set <CTID> --memory 4096 --swap 2048 --cores 2
#   3. Запусти:            pct start <CTID>
#
# Чтобы узнать CTID контейнера, на хосте Proxmox выполни:
#   pct list
# Найди строку с hostname = Kirill-AI. Ниже подставь реальный CTID вместо <CTID>.

pct stop <CTID>
pct set <CTID> --memory 4096 --swap 2048 --cores 2
pct start <CTID>

# После запуска внутри контейнера будет видно:
#   cat /proc/meminfo | grep MemTotal
#   → MemTotal: 4194304 kB   (4 ГБ)
#   free -h
#   → Swap: 2.0Gi

# Если контейнер с большим количеством памяти начнёт свопиться — это нормально,
# система спроектирована с запасом. Docker внутри LXC требует
# --features nesting=1 (если ещё не включено):
pct set <CTID> --features nesting=1,fuse=1