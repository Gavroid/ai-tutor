# CI/CD Setup

## Состояние на 2026-07-12

CI/CD workflow файлы готовы в `.github/workflows/`:
- `tests.yml` — backend tests + frontend build
- `deploy.yml` — SSH deploy на 192.168.1.86

## Опция 1: GitHub Actions (требует git remote)

### Требования
1. Создать репозиторий на GitHub: https://github.com/new
2. Push код: `git remote add origin git@github.com:YOUR_USER/ai-tutor.git && git push -u origin main`
3. Создать GitHub Secrets:
   - `PRODUCTION_HOST` = `192.168.1.86`
   - `PRODUCTION_SSH_KEY` = приватный SSH ключ с доступом к `root@192.168.1.86`
4. Push to main триггерит deploy

### Генерация SSH ключа для CI
```bash
ssh-keygen -t ed25519 -f ~/.ssh/ai-tutor-deploy -N "" -C "ai-tutor-ci"
# Добавить в /root/.ssh/authorized_keys на проде
ssh-copy-id -i ~/.ssh/ai-tutor-deploy.pub root@192.168.1.86
# Скопировать ПРИВАТНЫЙ ключ в GitHub Secrets:
cat ~/.ssh/ai-tutor-deploy | pbcopy  # или xclip, или просто скопировать вручную
```

## Опция 2: Webhook-based deploy (без git remote)

Если git remote не нужен, можно использовать webhook:

### Backend webhook endpoint
```python
# apps/backend/app/main.py — добавить endpoint:
@app.post("/internal/deploy", dependencies=[Depends(verify_deploy_token)])
async def webhook_deploy(request: Request):
    """Trigger deploy через webhook от внешнего сервиса."""
    # Запускаем deploy.sh в subprocess
    import subprocess
    result = subprocess.run(["/opt/ai-tutor/deploy/deploy.sh"], capture_output=True)
    return {"stdout": result.stdout.decode(), "returncode": result.returncode}
```

### deploy.sh (на проде)
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
- Polling в CI: `*/5 * * * * curl -X POST https://ai-tutor.example.com/internal/deploy?token=XXX`
- Manual: `curl -X POST -H "Authorization: Bearer XXX" ...`
- Frontend кнопка в `/admin`: "Force Deploy"

## Опция 3: Ручной deploy через SSH

```bash
# Из workspace:
scp -i ~/.ssh/id_ed25519_kirill_ai -r \
  apps/backend/app root@192.168.1.86:/opt/ai-tutor/apps/backend/
ssh -i ~/.ssh/id_ed25519_kirill_ai root@192.168.1.86 \
  "cd /opt/ai-tutor/deploy && docker compose build backend && docker compose up -d backend"
```

## Что готово

✅ `tests.yml` — тесты (backend + frontend build)
✅ `deploy.yml` — SSH deploy с healthcheck и E2E smoke
✅ `deploy/CICD.md` — этот файл с инструкциями
✅ Backup скрипт с md5 manifest
✅ Restore скрипт (с test-restore)
✅ Monitoring с healthcheck + error-rate

## Что нужно сделать для активации

- [ ] Создать репозиторий на GitHub
- [ ] Push код
- [ ] Создать GitHub Secrets
- [ ] Сделать test push для проверки workflow

**ИЛИ** (если без remote):

- [ ] Добавить webhook endpoint в backend
- [ ] Создать deploy.sh на проде
- [ ] Настроить cron или кнопку в /admin
