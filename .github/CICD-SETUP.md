# CI/CD для AI-Tutor

Этот документ описывает, как активировать CI/CD для проекта ai-tutor.

## Архитектура

```
Push в main
   ↓
GitHub Actions (ci.yml)
   ├─ Backend pytest (ubuntu-latest, 10 мин)
   └─ Frontend tsc + build (ubuntu-latest, 10 мин)
   ↓
Manual trigger (deploy.yml)
   ↓
GitHub Environment: production
   ↓ (manual approval, если настроен reviewer)
Self-hosted runner (Kirill-AI 192.168.1.86)
   ├─ Pre-deploy alembic check
   ├─ Save current release (rollback backup)
   ├─ rsync staging → deploy
   ├─ Deploy via deploy-from-ci.sh
   ├─ Healthcheck /health + /ready
   ├─ Smoke test
   └─ Telegram notify
```

## ⚠️ Безопасность (Sprint 17 P1-7)

- **Manual trigger only** — push в main НЕ триггерит deploy автоматически
- **GitHub Environment "production"** — manual approval через GitHub UI (опционально)
- **Pre-deploy alembic check** — не даёт деплоить код с незавершёнными миграциями
- **Healthcheck после deploy** — если /health или /ready не 200, инициируется rollback
- **Rollback backup** — текущий release ID сохраняется в `/opt/ai-tutor/deploy/release/rollback_backup/`

## Настройка GitHub Secrets

Перейдите в **Settings → Secrets and variables → Actions → New repository secret**.

### Обязательные secrets

| Secret | Описание | Пример значения |
|---|---|---|
| `PRODUCTION_SSH_KEY` | Приватный SSH ключ для self-hosted runner | (см. ниже) |
| `PRODUCTION_DATABASE_URL` | PostgreSQL URL для pre-deploy check | `postgresql+psycopg2://tutor:***@db:5432/tutor` |

### Опциональные secrets (для Telegram notify)

| Secret | Описание |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token (без `@` если приватный chat) |
| `TELEGRAM_CHAT_ID` | Chat ID для уведомлений |

## Настройка GitHub Environment

1. **Settings → Environments → New environment**
2. Имя: `production`
3. **Deployment protection rules:**
   - ✅ Required reviewers: добавьте себя (gavroshka)
   - ✅ Wait timer: 0 минут (или 5 если хотите подумать)
4. **Deployment branches:** only `main`

## Активация CI

CI (`ci.yml`) уже активирован — срабатывает на push в main и PR.

**Проверка:**
- Откройте GitHub → Actions → должны видеть "CI" workflow
- После push в main — запускается автоматически
- Занимает ~3-5 мин (pytest ~4 мин, build ~2 мин)

## Использование Deploy

### Manual trigger через GitHub UI

1. **Actions → Deploy to production → Run workflow**
2. Branch: `main` (default)
3. (опционально) Override ref: введите SHA если хотите конкретный commit
4. **Run workflow**
5. Если environment `production` требует approval — появится "Waiting for approval"
6. Approve
7. Workflow начнётся на self-hosted runner

### Manual trigger через CLI (если установлен gh)

```bash
gh workflow run deploy.yml \
  --ref main \
  --repo Gavroid/ai-tutor
```

## Troubleshooting

### CI fails: pytest timeout

Проверьте что в `apps/backend/tests/conftest.py` установлены `APP_SECRET_KEY`, `APP_ENV`, `DATABASE_URL`. Если эти переменные есть в GitHub Secrets — они НЕ нужны в conftest.

### CI fails: tsc fails

Next.js 16 требует Node.js 22+. В `ci.yml`:
```yaml
node-version: "22"
```

### Deploy fails: alembic drift

Pre-deploy check обнаружил drift. Запустите миграцию вручную:
```bash
docker exec deploy-backend-1 alembic upgrade head
```

### Deploy fails: healthcheck

После 10 сек ожидания /health или /ready не 200. Возможные причины:
- Backend не перезапустился — проверьте `docker logs deploy-backend-1`
- Frontend не перезапустился — `docker logs deploy-frontend-1`
- SSL сертификат истёк — `bash /opt/ai-tutor/deploy/ssl/generate-self-signed.sh`

### Deploy fails: SSH key invalid

Проверьте что `PRODUCTION_SSH_KEY`:
- Начинается с `-----BEGIN OPENSSH PRIVATE KEY-----` (или RSA)
- Заканчивается на `-----END OPENSSH PRIVATE KEY-----`
- Не содержит `\r\n` (Windows line endings) — должен быть `\n`
- Соответствует public key на проде в `/root/.ssh/authorized_keys`

## Что НЕ покрыто Sprint 17

- **Auto-deploy на push** — отключено намеренно (manual approval обязательно для семейного MVP)
- **Rollback автоматический** — pre-deploy сохраняет backup, но rollback script не реализован (TODO)
- **Notifications в Slack** — только Telegram
- **Self-hosted runner под root** — Sprint 18 (security hardening)