# AI-Tutor — Math-6 pilot scope gate

Дата: 2026-08-23

## Найденная проблема

`data/textbooks/7-class/evidence.json` содержал `pilot_visible=true` и `promotion_allowed=true` для нескольких предметов. Loader `app/subjects/evidence.py` доверял этим persisted-флагам напрямую, хотя canonical policy уже требовала pilot scope только `{math}`.

В результате API мог показывать неподтверждённые предметы как готовые к pilot.

## Исправление

Loader теперь перед созданием публичного `SubjectEvidence` прогоняет persisted payload через `validate_evidence_payload()`.

Canonical правила:

- только код `math` может быть `promotion_allowed=true`;
- `pilot_visible` вычисляется из canonical promotion;
- persisted `true` для Algebra/Geometry/других предметов игнорируется;
- `blocked_ocr` не может стать pilot-visible.

## Проверки

```text
Targeted policy/evidence/subjects/math6 tests: 80 passed
Full backend suite: 1312 passed, 29 skipped, 15 warnings
Frontend typecheck: passed
Frontend build: passed, 24 routes
Python compileall: passed
```

## Фактический результат

```text
pilot_visible codes: ["math"]
promotion_allowed codes: ["math"]
Algebra: pilot_visible=false, promotion_allowed=false
```

Это закрывает доступную программную часть Math-6 scope gate. Ручной smoke ребёнком, юридическая проверка источников, backup/restore в Docker и production rollout по-прежнему не выполнены и не подменяются тестами.
