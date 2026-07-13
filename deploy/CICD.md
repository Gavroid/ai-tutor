# CI/CD Setup

> **Обновлено 2026-07-13** после активации GitHub remote и CI.

## Состояние на 2026-07-13

CI/CD workflow активен в репозитории [Gavroid/ai-tutor](https://github.com/Gavroid/ai-tutor):

- ✅ **CI workflow** — `.github/workflows/ci.yml` (2 jobs: backend pytest + frontend tsc/lint/build, Playwright вынесен в nightly).
- ⏸ **Deploy workflow** — `.github/workflows/deploy.yml` готов, но не активирован (нужны GitHub Secrets `PRODUCTION_HOST` и `PRODUCTION_SSH_KEY` от владельца).
- ⏸ **Webhook-based deploy** — не сделан.
- ✅ **Backup + restore** — `deploy/backup/{backup.sh,ai-tutor-backup-offsite.sh,test-restore.sh}` + мои `scripts/backup-*.sh` (SMB через `smbclient`).

## Опция 1: GitHub Actions (рекомендуется)

### Что уже сделано (13.07.2026)

1. ✅ Создан приватный репозиторий [Gavroid/ai-tutor](https://github.com/Gavroid/ai-tutor).
2. ✅ Запушен весь код (`main` ветка, ~13 коммитов).
3. ✅ `ci.yml` объединил `tests.yml` + `frontend-build.yml` (двух-файловая структура удалена, избегаем дубля работы).
4. ✅ Badge в `README.md`.

### Что нужно сделать (от владельца)

1. **Создать GitHub Secrets** (https://github.com/Gavroid/ai-tutor/settings/secrets/actions):
   - `PRODUCTION_HOST` = `192.168.1.86`
   - `PRODUCTION_SSH_KEY` = **приватный** SSH-ключ с доступом к `root@192.168.1.86` (использовать `~/.ssh/id_ed25519_cicd`, НЕ основной `id_ed25519_kirill_ai`).
2. **Раскомментировать `deploy.yml`** (или создать заново — сейчас он disabled).
3. **Тестовый push** для проверки: `git commit --allow-empty -m "test CI" && git push origin main`.

### Генерация SSH-ключа для CI (если ещё нет)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_cicd -N "" -C "ai-tutor-ci"
# Добавить в /root/.ssh/authorized_keys на проде (192.168.1.86):
ssh-copy-id -i ~/.ssh/id_ed25519_cicd.pub root@192.168.1.86
# Скопировать ПРИВАТНЫЙ ключ в GitHub Secrets (Settings → Secrets):
cat ~/.ssh/id_ed25519_cicd | pbcopy  # или xclip, или скопировать вручную
```

### Что делает текущий `ci.yml`

```yaml
# .github/workflows/ci.yml
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  backend:    # Python 3.12, pip cache, pytest, AI_API_KEY=mock-key-for-ci
  frontend:   # Node 20, npm cache, tsc + lint + build
```

**Playwright E2E вынесен** из обязательного CI (требует 300MB+ для `playwright install`, не нужен на каждом PR). Будет в nightly.

## Опция 2: Webhook-based deploy (без git remote)

Актуально, если решишь отказаться от GitHub remote. Использует `deploy/release/deploy.sh` через HTTP-триггер.

### Backend webhook endpoint (если нужен)

```python
# apps/backend/app/main.py — добавить endpoint:
@app.post("/internal/deploy", dependencies=[Depends(verify_deploy_token)])
async def webhook_deploy(request: Request):
    """Trigger deploy через webhook от внешнего сервиса."""
    import subprocess
    result = subprocess.run(["/opt/ai-tutor/deploy/deploy.sh"], capture_output=True)
    return {"stdout": result.stdout.decode(), "returncode": result.returncode}
```

### `deploy.sh` (на проде)

```bash
#!/bin/bash
cd /opt/ai-tutor/deploy
docker compose build backend frontend
docker compose up -d
sleep 15
docker compose exec -T backend alembic upgrade head
curl -sk https://localhost/health
```

### Triggers

- Polling: `*/5 * * * * curl -X POST https://ai-tutor.example.com/internal/deploy?token=XXX`
- Manual: `curl -X POST -H "Authorization: Bearer ..." https://...`
- Frontend кнопка в `/admin`: "Force Deploy"

## Опция 3: Ручной deploy через SSH (используется сейчас)

```bash
# Из workspace (на LXC 192.168.1.86):
scp -i ~/.ssh/id_ed25519_kirill_ai -r \
  apps/backend/app root@192.168.1.86:/opt/ai-tutor/apps/backend/
ssh -i ~/.ssh/id_ed25519_kirill_ai root@192.168.1.86 \
  "cd /opt/ai-tutor/deploy && docker compose build backend && docker compose up -d backend"
```

Или полный atomic deploy через `deploy/release/deploy.sh` (см. `docs/deployment.md`):

```bash
# 1) preflight
bash deploy/release/preflight.sh

# 2) deploy
bash deploy/release/deploy.sh              # текущий HEAD
bash deploy/release/deploy.sh 72188f9      # явно с commit SHA

# 3) smoke
bash deploy/release/smoke.sh

# 4) rollback (если что-то пошло не так)
bash deploy/release/rollback.sh             # из marker-файла
bash deploy/release/rollback.sh 72188f9     # явно с known-good SHA
```

## Что готово

- ✅ `ci.yml` — backend pytest + frontend tsc/lint/build (2 jobs, кеш pip/npm, concurrency).
- ✅ `deploy.yml` — SSH deploy с healthcheck и E2E smoke (готов, но не активирован — нет secrets).
- ✅ `deploy/CICD.md` — этот файл.
- ✅ `deploy/backup/{backup.sh,ai-tutor-backup-offsite.sh,test-restore.sh}` — локальный backup.
- ✅ `scripts/backup-{full,pre-edit}.sh` + `scripts/restore.sh` — SMB-бэкап через `smbclient` (без mount.cifs — LXC unprivileged не поддерживает).
- ✅ Monitoring: `healthcheck.sh` + `error-rate.sh` пишут в `/var/log/ai-tutor-*.log`.
- ⏸ Telegram-алерты — отложены (нужен `TELEGRAM_BOT_TOKEN`).

## Что нужно сделать для полной активации

- [x] Создать репозиторий на GitHub — **сделано 13.07.2026**.
- [x] Push код — **сделано 13.07.2026**.
- [ ] Создать GitHub Secrets (`PRODUCTION_HOST`, `PRODUCTION_SSH_KEY`).
- [ ] Раскомментировать `deploy.yml` workflow.
- [ ] Сделать тестовый push для проверки.
- [ ] Опционально: подключить Telegram-алерты.

**ИЛИ** (если без remote — не рекомендуется):
- [ ] Добавить webhook endpoint в backend.
- [ ] Создать deploy.sh на проде.
- [ ] Настроить cron или кнопку в /admin.
