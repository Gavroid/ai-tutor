# AI-Tutor — доказательства автономного продолжения, 2026-08-23

## Новый блок Sprint 6–7

| Проверка | Результат |
|---|---|
| Backup artifact validator | 4 passed |
| Backup + Algebra/RAG + readiness subset | 17 passed |
| Explain + Math-6 + content/evidence subset | 81 passed |
| Release marker + targeted deploy manifests | 8 passed |
| Python compileall (`app scripts`) | passed |
| Frontend `npm audit --omit=dev --audit-level=high` | 4 high vulnerabilities; upgrade intentionally blocked |

## Backup preflight

Добавлены:

- `apps/backend/scripts/backup_artifact_validator.py`
- `apps/backend/tests/test_backup_artifact_validator.py`

Проверка локальная и read-only. Она подтверждает размер файла, gzip, SQL-признак и SHA-256 checksum. Она не выполняет restore, не подключается к SMB/Docker и не меняет production.

## Ограничения

Полный backup/restore gate не закрыт: для него нужен отдельный Docker/CI runner и фактический offsite backup. Production не изменялся.

Dependency audit обнаружил 4 high frontend vulnerability. `npm audit fix --force` не запускался, потому что требует Next.js `16.3.2` вне текущего диапазона и отдельного regression.
