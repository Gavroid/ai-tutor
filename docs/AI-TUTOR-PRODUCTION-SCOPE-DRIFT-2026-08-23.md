# AI-Tutor — production scope drift evidence

Дата: 2026-08-23
Режим: read-only; production не изменялся.

## Проверка

```text
GET https://192.168.1.86/health       → 200, status=ok
GET https://192.168.1.86/ready        → 200, status=ready
GET https://192.168.1.86/api/v1/subjects → 200
```

## Фактический production response

Production возвращает 16 subjects, и у всех:

```text
pilot_visible=true
promotion_allowed=true
mvp_status=mvp_ready
```

В список входят Algebra, Geometry, Physics, OCR/image-only subjects и остальные предметы.

Ожидаемая локальная policy после коммита `f5fc083` и текущего scope plan:

```text
pilot_visible=["math"]
promotion_allowed=["math"]
```

## Вывод

Production runtime отстаёт от локального fail-closed policy и сейчас **не соответствует Math-6-only pilot scope**. Это release blocker.

Локальный код не публиковался, потому что отсутствуют одновременно подтверждённые:

- production backup + offsite verification;
- disposable staging/restore rehearsal;
- post-deploy Playwright/manual smoke;
- безопасная targeted deploy procedure.

Production намеренно не изменялся. Marker не записывался.

## Дополнительные ограничения

- Docker отсутствует на текущем хосте.
- Playwright MVP suite содержит 5 stateful student tests и требует работающий staging backend.
- `/api/v1/health` и `/api/v1/ready` не являются application routes; health/readiness проверены через proxy `/health` и `/ready`.
