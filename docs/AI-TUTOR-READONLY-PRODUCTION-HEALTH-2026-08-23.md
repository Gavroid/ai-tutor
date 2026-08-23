# AI-Tutor — read-only production health evidence

Дата: 2026-08-23
Репозиторий: `/root/workspace/ai-tutor`
Последний локальный коммит: `f5fc083`

## Проверено без mutation

```text
GET https://192.168.1.86/health
HTTP 200
{"status":"ok","service":"AI Tutor 7","env":"production","version":"0.1.0-mvp"}

GET https://192.168.1.86/ready
HTTP 200
{"status":"ready"}
```

Оба ответа содержали security headers `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options` и уникальный `x-request-id`.

## Безопасность действий

- Выполнены только GET-запросы.
- Production-файлы, БД, marker, RAG и пользовательские данные не изменялись.
- Playwright E2E через production не запускался: сценарии создают login/AI-запросы и не являются read-only.
- Docker на текущей машине отсутствует, поэтому disposable staging и настоящий restore drill не выполнялись.

## Release marker

Offline dry-run с переданными aligned values (`local_head=f5fc083`, production marker/head=`f5fc083`, clean tree, branch=`mvp-rescue`) возвращает `already_current` и `can_advance_marker=false`.

Это проверка алгоритма dry-run, а не доказательство фактического состояния production marker: marker не читался и не записывался удалённо.

## Незакрытые внешние gates

1. Фактический backup + offsite verification.
2. Реальный restore в disposable PostgreSQL/Docker.
3. Playwright smoke на staging.
4. Ручная проверка ребёнком.
5. Отдельное решение владельца о production rollout.
