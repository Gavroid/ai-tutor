# AI-Tutor — текущий статус (после Sprint 1)

Дата: 2026-08-23
Связанные документы:

- `docs/AI-TUTOR-AUDIT-CURRENT-2026-08-23.md` — фактический аудит.
- `docs/AI-TUTOR-NEXT-SESSION-PROMPT-AUDIT-2026-08-23.md` — задание сессии.
- `docs/AI-TUTOR-DEVELOPMENT-ROADMAP-2026-08-23.md` — roadmap P0/P1/P2.
- `docs/AI-TUTOR-SPRINT-PLAN-2026-08-23.md` — подробный план спринтов.

Репозиторий: `/root/workspace/ai-tutor`
Ветка: `design-audit-2026-08-20-fixes`
HEAD на момент Sprint 1: `9ebeafe` (unchanged в этой сессии).
Рабочее дерево: модифицированы `apps/backend/app/admin/router.py`,
`apps/backend/pytest.ini` (новый файл), `apps/backend/scripts/run_backend_groups.sh` (новый).

## Sprint 1 — итог

Цель: вернуть зелёный тестовый контур для readiness/admin и выяснить причину
полного suite timeout.

### Изменения

1. `apps/backend/app/admin/router.py`:
   - восстановлен module-level override `_EVIDENCE_PATH: Path | None = None`;
   - добавлен `_resolve_active_evidence_path()` для разделения override от дефолта;
   - `_find_evidence_path()` сначала проверяет override (используется в
     `tests/test_admin_evidence.py` через `monkeypatch.setattr`).

2. `apps/backend/pytest.ini` (новый):
   - зафиксирован `asyncio_default_fixture_loop_scope = function`,
     чтобы убрать `PytestDeprecationWarning` от pytest-asyncio и
     стабилизировать async-fixtures.

3. `apps/backend/scripts/run_backend_groups.sh` (новый):
   - группирует suite по префиксам, запускает каждую группу с явным
     timeout/budget, чтобы полный timeout не маскировал неизвестный остаток.

### Проверка evidence API (RED → GREEN)

До:

```text
tests/test_admin_evidence.py: 1 passed, 9 errors in 1.63s
AttributeError: ...has no attribute '_EVIDENCE_PATH'
```

После:

```text
tests/test_admin_evidence.py: 10 passed, 31 warnings in 8.31s
```

### Полный backend suite по группам

Все группы запускались с бюджетом ≤ 360s, явным exit code и без silent timeout.
Сводка (актуальная на момент Sprint 1):

| Группа | exit | длительность | результат |
|---|---|---|---|
| test_subjects | 0 | 4s | 14 passed |
| test_chunker | 0 | 2s | 9 passed |
| test_health | 0 | 2s | 8 passed |
| test_admin | 0 | 19s | 27 passed |
| test_admin_evidence | 0 | 9s | 10 passed |
| test_ai | 0 | 5s | 69 passed |
| test_progress_diagnostics | 0 | 5s | 5 passed |
| test_rag | 0 | 3s | 26 passed |
| test_auth | 0 | 7s | 17 passed |
| test_websocket | 0 | 3s | 6 passed |
| test_voice | 0 | 2s | 4 skipped |
| test_teacher | 0 | 68s | 44 passed |
| test_algebra | 0 | 3s | 62 passed |
| test_geometry | 0 | 1s | 14 passed |
| test_pilot | 0 | 22s | 28 passed |
| test_p0_followup_seed | 0 | 2s | 1 passed |
| test_notifications | 0 | 6s | 5 passed |
| test_oauth | 0 | 1s | 5 skipped |
| test_ops_metrics | 0 | 2s | 2 passed |
| test_observability | 0 | 4s | 11 passed |
| test_login_rate_limit | 0 | 11s | 4 passed |
| test_diagnostic_expire | 0 | 7s | 6 passed |
| test_alert_worker | 0 | 2s | 6 passed |
| test_email | 0 | 4s | 9 passed |
| test_stage6 | 0 | 3s | 3 passed |
| test_techdebt | 0 | 7s | 16 passed |
| **test_sprint (69 файлов)** | **1** | **175s** | **636 passed, 20 skipped, 1 FAILED** |
| test_math | 0 | 3.4s | 25 passed |
| test_parent | 0 | 24.4s | 18 passed |
| test_rbac | 0 | 30s | 23 passed |
| test_refresh | 0 | 5s | 7 passed |
| test_password_reset | 0 | 5.8s | 10 passed |
| test_audit_retention | 0 | 1.6s | 1 passed |
| test_remaining_subjects | 0 | 2.6s | 8 passed |
| test_student_review | 0 | 16.6s | 19 passed |
| test_telegram_bot | 0 | 3.6s | 8 passed |
| test_ws_rate_limit | 0 | 4.6s | 5 passed |
| test_ocr | 0 | 4.2s | 4 passed |
| test_learning_analytics | 0 | 4.4s | 2 passed |
| test_content_quality | 0 | 2s | 6 passed |
| test_production_all_subjects | 0 | 2.4s | 2 passed |
| slow (`-m slow`) | 0 | 13.87s | 11 passed |

Итого: каждая группа завершается явным exit code в пределах бюджета.
Полный silent timeout (124 от `pytest --durations=30`, ушедший в 41% в аудите)
больше не воспроизводится при блочном запуске.

### Известная failure (out of scope для S1)

`tests/test_sprint32_parent_2fa.py::test_enable_2fa_returns_secret_and_codes`
падает только в составе большого suite `test_sprint*` (неустойчиво).
Изолированно тест зелёный (12 passed, 26s). Это ordering pollution,
классифицируется как debt и относится к Sprint 8 (`test_sprint_*`
fixtures/state). В S1 не правлю.

Тот же тест в повторном полном прогоне `test_sprint*` может проходить
(нестабильно). В статус внесена запись «flake», в S8 будет устранена как
часть maintenance debt.

### Критерии выхода Sprint 1

| Критерий | Статус |
|---|---|
| `tests/test_admin_evidence.py` green (10/10) | ✅ |
| Нет collection/setup errors | ✅ |
| Каждая backend-группа завершается явным exit code | ✅ |
| Timeout не скрывает неизвестный остаток suite | ✅ |
| `git diff --check` проходит | ✅ |
| Текущий status report содержит свежие результаты | ✅ (этот документ) |

Sprint 1 выполнен. Готовность к Sprint 2 — частичная: S2 закрывает Explain
и детерминированный student flow, что формально не относится к baseline,
поэтому переход возможен сразу.
