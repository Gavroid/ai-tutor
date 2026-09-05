# AI-Tutor — textbook license readiness evidence

Дата: 2026-08-23

## Проверенный источник

```text
data/textbooks/7-class/textbook-manifest.csv
```

В manifest обнаружено **20 записей**. Для всех 20:

```text
license_decision=needs_review
status=preview
import_status=not_started
rag_status=not_started
manual_smoke_status=not_started
```

## Добавленная policy-проверка

`apps/backend/app/subjects/textbook_manifest_policy.py` вычисляет readiness fail-closed:

- `needs_review` и `rejected` не являются разрешённой лицензией;
- unresolved rights запрещают import и RAG;
- даже разрешённая лицензия сама по себе не даёт pilot promotion;
- `production_mutation`, `db_write` и `rag_write` всегда false для audit;
- persisted ложные статусы не могут обойти policy.

## Evidence

```text
Textbook policy tests: 3 passed
Manifest/provenance suite: 22 passed
Source/RAG rehearsal suite: 46 passed
Math-6/evidence/content suite: 86 passed
Full backend suite: 1316 passed, 29 skipped, 2 warnings
Frontend typecheck: passed
Frontend production build: passed, 24 routes
Python compileall: passed
git diff --check: passed
```

## Фактический вывод

```text
row_count: 20
blocked_license_count: 20
pilot_allowed: false
```

Лицензионные решения не выдумывались и не изменялись. До юридического подтверждения источников учебники остаются preview и не могут быть использованы для pilot RAG.
