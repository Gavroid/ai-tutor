# AI-Tutor — текущий статус (executive, 2026-08-23)

Дата: 2026-08-23
HEAD: `967a0ad` на ветке `design-audit-2026-08-20-fixes`.
План следующих работ: [`docs/AI-TUTOR-NEXT-PLAN-2026-08-23.md`](AI-TUTOR-NEXT-PLAN-2026-08-23.md).
Детальный per-sprint журнал: [`docs/AI-TUTOR-SPRINT-EXECUTION-LOG.md`](AI-TUTOR-SPRINT-EXECUTION-LOG.md).
Базовый аудит: [`docs/AI-TUTOR-AUDIT-CURRENT-2026-08-23.md`](AI-TUTOR-AUDIT-CURRENT-2026-08-23.md).
Roadmap: [`docs/AI-TUTOR-DEVELOPMENT-ROADMAP-2026-08-23.md`](AI-TUTOR-DEVELOPMENT-ROADMAP-2026-08-23.md).

---

## 1. Фактическое состояние (single source of truth)

8 spec test files, прогон в этой сессии:

```
pytest -q tests/test_admin_evidence.py \
        tests/test_ai_explain_contract.py \
        tests/test_evidence_schema.py \
        tests/test_math6_pilot.py \
        tests/test_manifest_provenance.py \
        tests/test_retrieval_benchmark.py \
        tests/test_disposable_environment.py \
        tests/test_maintenance_ci.py

135 passed, 131 warnings in 44.18s
```

| Sprint | Тест-файл | passed | warnings | sec |
|---|---|---|---|---|
| S1 — backend baseline | `test_admin_evidence.py` | 10 | 31 | 8.5 |
| S2 — Explain graceful | `test_ai_explain_contract.py` | 10 | 19 | 7.3 |
| S3 — Canonical readiness | `test_evidence_schema.py` | 15 | 8 | 2.7 |
| S4 — Math-6 pilot | `test_math6_pilot.py` | 50 | 82 | 29.7 |
| S5 — Manifest provenance | `test_manifest_provenance.py` | 18 | 3 | 0.9 |
| S6 — Retrieval benchmark | `test_retrieval_benchmark.py` | 8 | 3 | 0.9 |
| S7 — Disposable environment | `test_disposable_environment.py` | 15 | 3 | 1.0 |
| S8 — Maintenance + CI | `test_maintenance_ci.py` | 9 | 3 | 1.4 |
| **Итого** |   | **135** |   | **52.4** |

Полный `tests/test_sprint*.py` бандл:

```
637 passed, 20 skipped, 328 warnings in 177.07s
```

(flake в `test_sprint32_parent_2fa` закрыт в S1 через
`asyncio_default_fixture_loop_scope=function` в `pytest.ini`).

Frontend (`apps/frontend`):

```
npm run typecheck    → green
npm run build        → 24 routes (Next.js)
git diff --check     → clean
```

---

## 2. 6 коммитов этой сессии (на ветке `design-audit-2026-08-20-fixes`)

| SHA | Sprint | Title |
|---|---|---|
| `c77a92e` | post-Sprint-8 | docs(status): sync CURRENT-STATUS.md to actual post-Sprint-8 state |
| `2164a1f` | continuation T1 | chore: deprecation cleanup + status split + new plan |
| `b85e9fd` | continuation T2 | fix: Pydantic V1→V2 Config migration + flake-guard runner |
| `967a0ad` | continuation T2-T3 | test: /health schema contract + license draft |
| `dfc4d42` | S5–S8 | feat(backend+deploy): Sprint 5–8 — manifest, retrieval, disposable, maintenance |
| `388b3bd` | S4 | feat(backend): Sprint 4 — Math-6 pilot parametrized contracts (15 P0 topics) |
| `3ddd3d9` | S3 | feat(backend): Sprint 3 — canonical readiness policy + fail-closed validator |
| `2b8138d` | S2 | feat(backend+frontend): Sprint 2 — Explain graceful fallback + deterministic E2E |
| `c6537bf` | S1 | fix(backend): restore _EVIDENCE_PATH override + per-group suite runner |

Эта сессия (continuation) добавит новые коммиты поверх `c77a92e`.

---

## 3. Scope policy (что НЕ меняли и НЕ будем)

- `production data`, `.env`, `secrets/`, Nightscout — read-only.
- `manual_smoke_ready=true` НЕ подменяется автоматически — остаётся
  `false` чесно.
- Pilot scope остаётся Math-6 only:
  `PILOT_SCOPE = {"math"}` в
  `apps/backend/app/subjects/evidence_schema.py`.
- `/opt/ai-tutor` (production mount) — не правим.
- `disposable-staging.sh up` **не запускается** на этой машине:
  docker недоступен. Требуется CI runner.

---

## 4. Definition of Done — статус

| Критерий из roadmap | Статус | Где |
|---|---|---|
| `tests/test_admin_evidence.py` green | ✅ 10/10 | S1 |
| Backend suite без silent timeout | ✅ (группы по budget) | S1 |
| MVP E2E на deterministic provider | ✅ | S2 |
| 15 P0 Math topics contracts | ✅ 50/50 | S4 |
| Evidence validator без противоречий | ✅ | S3 |
| `/health` + `/ready` | ✅ contract tests | S7 |
| `manual_smoke_ready=false` честно | ✅ | S3 + S7 config |
| 20 manifest rows синхронизированы | ✅ schema validation | S5 |
| recall@k/MRR@k per subject | ✅ | S6 |
| Flake-стойкий test_sprint32 | ✅ | S1 (asyncio scope) |
| Production mutation отсутствует | ✅ | S7 toml |
| Cleanup deprecation warnings | ⚠️ частично: passlib/sqlalchemy filterwarnings (T1.3a), 1 jose fix (T1.3b), 2 pydantic V2-class (T1.3c). Plus backlog `AI-TUTOR-PYDANTIC-V2-MIGRATION-PLAN.md` для V3 | S continuation |
| License review manifest | ⚠️ draft готовится | T3.1 |
| Mobile Playwright runtime | ⚠️ deferred до CI | T3.2 |

---

## 5. Известные ограничения (out of S1–S8 scope)

- **Licenses**: 20 manifest rows = `needs_review`. Юр. review.
- **Mobile viewport Playwright** runtime: framework готов
  (`mvp-student-flow.spec.ts`), но запуск требует disposable CI.
- **3 deprecation categories**: `passlib.crypt`, `jose.utcnow`,
  `Pydantic V1 class-based config`. Зафиксированы в `test_maintenance_ci.py`
  inventory; точечное закрытие в T1.3/T2.
- **Pydantic V1→V2 codemod**: отдельный sprint, за рамками этой сессии.

---

## 6. Следующие действия (см. plan)

`AI-TUTOR-NEXT-PLAN-2026-08-23.md`, TIER 1–3.

**TIER 1 (сегодня):**
- T1.3a passlib `filterwarnings` в `pytest.ini`.
- T1.3b `app/auth/security.py`: `datetime.utcnow()` → `datetime.now(tz=utc)`.
- T1.3c Pydantic V2 migration plan (markdown backlog).
- T1.4 split CURRENT-STATUS.md (этот commit).

**TIER 2 (если время):**
- T2.1 расширить disposable tests (без docker).
- T2.3 flake-guard для test_sprint32 (10 повторных прогонов).

**TIER 3 (отдельные заходы):**
- T3.1 license review draft.
- T3.2 Playwright mobile runtime (требует docker CI).
