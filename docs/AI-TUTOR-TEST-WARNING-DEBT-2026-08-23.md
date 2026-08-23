# AI-Tutor — test warning debt

Дата: 2026-08-23

## Наблюдения

Полный backend regression завершён:

```text
1316 passed, 29 skipped, 2 warnings
```

Warnings:

1. `test_email_per_lesson.py::test_notification_on_milestone_attempts` — `AsyncMock` вызывается из синхронного `record_attempt()` без await.
2. `test_notifications.py::test_email_dry_run_without_smtp` — тест создаёт coroutine `send_email()` и не await’ит первый вызов.

Отдельно воспроизводится pre-existing `passlib` deprecation warning.

## Решение

Dirty-тесты не изменялись и warnings не скрывались глобальным `filterwarnings`. Исправление тестовой async-гигиены — отдельный блок, чтобы не смешивать его с уже зафиксированными policy-коммитами.
