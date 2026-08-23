# AI-Tutor — актуальный dependency audit

Дата проверки: 2026-08-23
Режим: read-only; версии не изменялись.

## Frontend

Команда:

```text
cd apps/frontend && npm audit --omit=dev --audit-level=high
```

Результат: команда завершилась кодом `1`, найдено **4 high severity vulnerabilities**:

- `nanoid` — уязвимые версии генератора;
- `next 16.2.10` — несколько advisories для App Router/Server Actions/Proxy;
- `postcss` — XSS и чтение файлов через source maps;
- `sharp <0.35.0` — уязвимости libvips.

Автоматическое исправление предлагает `npm audit fix --force`, включая обновление до `next@16.3.2`, что выходит за текущий диапазон и требует отдельного regression. Команда не выполнялась.

## Backend

Исторический pip-audit snapshot находится в `docs/AI-TUTOR-DEPENDENCY-AUDIT-2026-08-23.md`, но его package versions требуют повторного запуска `pip-audit` в CI: локальная команда `pip-audit` сейчас не установлена. Snapshot нельзя считать свежим доказательством текущего окружения.

Из текущего `apps/backend/requirements.txt` подтверждено:

- `fastapi==0.115.5`;
- `python-jose[cryptography]==3.5.0`;
- `python-dotenv==1.2.2`;
- `python-multipart==0.0.20`;
- `pypdf==5.1.0`;
- `Pillow==11.0.0`;
- `starlette` приходит транзитивно через FastAPI и отдельно не закреплён.

## Решение

- Не запускать `npm audit fix --force` автоматически.
- Не обновлять Starlette 1.x в этом блоке: есть отдельный migration plan и API surface audit.
- Добавить полноценный pip-audit запуск в CI/staging после согласования policy по known vulnerabilities.
- Для каждого upgrade делать отдельный коммит и полный backend/frontend regression.

## Статус Sprint 7

Dependency/security audit: **выполнен как аудит и зафиксирован как blocker**.
Security upgrades: **не выполнены**, поскольку автоматическое массовое обновление небезопасно.
