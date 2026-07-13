# Pilot Core Stage 1 — baseline

**Снято:** 2026-07-13 16:26 MSK  
**Workspace:** `/root/workspace/ai-tutor`  
**Production:** `192.168.1.86`, `/opt/ai-tutor`

## Revision и рабочее дерево

- Ветка: `main`.
- Baseline revision: `676d6b3ef59a05648ed0bf05e3160c9c2e8b9025` (`676d6b3`).
- Git remote отсутствует.
- Production host не имеет исполняемого файла `git`; код развёрнут в `/opt/ai-tutor`.
- `.hermes/` содержит локальные планы и не входит в release artifact/commit.

## Локальные gates

### Backend

Команда:

```bash
cd apps/backend
APP_SECRET_KEY='test-secret-key-for-pytest-only-1234567890' \
APP_ENV=development \
DATABASE_URL='sqlite+pysqlite:///:memory:' \
CORS_ORIGINS='http://localhost:3000' \
AI_API_KEY='mock-key-for-tests' \
UPLOAD_DIR='/tmp/ai-tutor-test-uploads' \
PYTHONDONTWRITEBYTECODE=1 \
.venv/bin/pytest tests/ -q --tb=line -p no:cacheprovider
```

Результат: **405 passed, 305 warnings, 185.86 s**.

Подтверждённые application-owned warnings:

1. `test_notification_on_milestone_attempts` — coroutine `AsyncMock` не awaited.
2. `test_email_dry_run_without_smtp` — coroutine `send_email` не awaited.

Alembic: один head — `0012_rag_chunks`.

### Frontend

- `npm run build` — успешно.
- `npx playwright test --list` — **21 тест** в 4 spec-файлах.

## Production baseline

### Containers

| Service | Состояние |
|---|---|
| backend | Up, healthy |
| db | Up, healthy |
| frontend | Up, healthy |
| grafana | Up, healthcheck не задан |
| prometheus | Up, healthy |
| proxy | Up, healthcheck не задан |
| redis | Up, healthy |

Итого: **7/7 запущены**, из них **5/7 имеют Docker status `healthy`**. Для буквального
гейта `7/7 healthy` healthcheck ещё нужен для `grafana` и `proxy`.

### HTTP

| Endpoint | Baseline |
|---|---:|
| `/health` | 200 |
| `/ready` | **404** |
| `/api/v2/health` | 200 |

### Resources

- RAM: 4096 MiB total, 739 MiB used, 3356 MiB available.
- Swap: выключен.

### Audit

В `audit_logs` за последние 7 дней уже есть **3** записи `action=error.5xx`, все с
`created_at` около `2026-07-13 07:26:40 UTC`. Историю audit log не удаляем и не
переписываем ради прохождения гейта. Активную причину нужно устранить; исторический
семидневный счётчик обнулится естественно.

## Backup baseline

Фактические значения при текущем cron wiring:

- `BACKUP_ROOT=/opt/ai-tutor/deploy/backup/_out` (`backup.sh`, hard-coded canonical source).
- `BACKUP_OFFSITE_DEST=/var/backups/ai-tutor` (default в offsite wrapper).
- Последний manifest: `manifest-20260713T030001Z.md5`, 2026-07-13 03:00:02 UTC.
- `test-restore.sh` читает `/var/backups/ai-tutor`, а `backup.sh` пишет в
  `/opt/ai-tutor/deploy/backup/_out`.
- Оба пути находятся на одном filesystem (`stat -f` совпадает).
- CIFS/SMB mount отсутствует.

Следствие: текущая «offsite» копия не переживёт потерю production LXC.

## Pilot role policy

Самостоятельное создание privileged roles запрещено:

- `teacher` — только seed CLI;
- `admin` — только seed CLI.

Для совместимости первого release технический allowlist public schema ограничивается
`student` и `parent`; пилотные аккаунты создаются заранее через seed CLI. UI регистрации
не считается пилотным сценарием. OAuth2 не используется в пилоте.

## Внешние зависимости

На момент baseline:

- private GitHub remote не подключён;
- SMB/NAS destination не подключён и реквизиты в проекте отсутствуют;
- список семи реальных pilot users не зафиксирован.

Эти пункты не блокируют локальную реализацию фаз 1–3 и 5–6. Phase 4 должна fail closed
без внешнего destination и не имеет права изображать local path как offsite.
