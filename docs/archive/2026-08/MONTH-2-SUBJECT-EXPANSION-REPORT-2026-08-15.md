# Month 2 Subject Expansion Report — 2026-08-15

## Executive Decision

Decision: **do not move Algebra or Geometry into pilot-ready scope yet**.

Month 2 succeeded at creating honest preview infrastructure for Algebra and Geometry:

- route plans exist;
- deterministic practice banks exist;
- UI/API show readiness transparently;
- source/RAG blockers are documented.

But both subjects still lack verified source/RAG coverage, so they must remain `preview`.

## Production State

Latest production evidence:

```text
production marker: 6e698a0
/ready HTTP=200
/health HTTP=200
backend/frontend/db/redis/prometheus healthy; grafana/proxy running
```

The marker was not advanced because Month 2 work continued using targeted controlled deploys/registry mutations rather than a full release marker workflow. Deployed runtime behavior was verified directly by API and E2E smoke.

## Subject Readiness Matrix

| Subject | Status | Route | Sources/RAG | Practice | Pilot decision |
|---|---|---:|---:|---:|---|
| Math repeat | `mvp_ready` | 42/42 | 42/42 | 42/42 | Keep as primary pilot scope |
| Algebra | `preview` | 19/19 | 0/19 | 19/19 | Not pilot-ready; needs verified sources |
| Geometry | `preview` | 13/13 | 0/13 | 13/13 | Not pilot-ready; needs verified sources |

Production `/api/v1/subjects` smoke:

```text
{"id": 4, "code": "algebra", "mvp_status": "preview", "route_ready": true, "rag_ready": false, "practice_ready": true, "topic_count": 19, "route_topic_count": 19, "source_topic_count": 0, "practice_topic_count": 19}
{"id": 5, "code": "geom", "mvp_status": "preview", "route_ready": true, "rag_ready": false, "practice_ready": true, "topic_count": 13, "route_topic_count": 13, "source_topic_count": 0, "practice_topic_count": 13}
{"id": 3, "code": "math", "mvp_status": "mvp_ready", "route_ready": true, "rag_ready": true, "practice_ready": true, "topic_count": 42, "route_topic_count": 42, "source_topic_count": 42, "practice_topic_count": 42}
```

## Completed Month 2 Stages

| Stage | Status | Deliverable |
|---|---:|---|
| Stage 11 — Algebra/Geometry scope audit | Complete | `docs/ALGEBRA-GEOMETRY-SCOPE-AUDIT-2026-08-14.md` |
| Stage 12 — Algebra route plan | Complete | `docs/STAGE-12-ALGEBRA-ROUTE-PLAN-2026-08-14.md` |
| Stage 13 — Geometry route plan | Complete | `docs/STAGE-13-GEOMETRY-ROUTE-PLAN-2026-08-14.md` |
| Stage 14 — Algebra source/RAG audit | Complete, blocker documented | `docs/STAGE-14-ALGEBRA-SOURCE-RAG-AUDIT-2026-08-14.md` |
| Stage 15 — Geometry source/RAG audit | Complete, blocker documented | `docs/STAGE-15-GEOMETRY-SOURCE-RAG-AUDIT-2026-08-15.md` |
| Stage 16 — Algebra practice bank | Complete | `docs/STAGE-16-ALGEBRA-PRACTICE-BANK-PASS-1-2026-08-15.md` |
| Stage 17 — Geometry practice bank | Complete | `docs/STAGE-17-GEOMETRY-PRACTICE-BANK-PASS-1-2026-08-15.md` |
| Stage 18 — Multi-subject readiness UI | Complete | `docs/STAGE-18-MULTI-SUBJECT-READINESS-UI-2026-08-15.md` |

## What Changed

- Algebra now has a 19-topic preview route with tiers, checkpoints, focus labels, and next-topic links.
- Geometry now has a 13-topic preview route with tiers, checkpoints, focus labels, and next-topic links.
- Algebra has deterministic fallback practice for 19/19 route topics.
- Geometry has deterministic fallback practice for 13/13 route topics.
- `/api/v1/subjects` exposes readiness coverage fields for route/source/practice.
- Subjects UI shows readiness lines for every subject card: `Маршрут`, `Источники`, `Практика`.
- Cache keys were versioned to `subjects:v3:*` to avoid stale readiness shape.

## Source/RAG Findings

Algebra:

- The only previous Algebra material was a false positive: `geometry_test.txt` attached to Algebra topic 34.
- It contained geometry text about triangle area, not Algebra.
- After backup, the invalid material and its chunk were removed.
- Algebra source/RAG coverage is now honestly `0/19`.

Geometry:

- Production had no Geometry materials or chunks.
- Public candidates were checked, but not imported because license/reuse certainty was insufficient.
- Geometry source/RAG coverage remains `0/13`.

## Tests And Gates

Latest Month 2 verification:

```text
cd apps/backend
.venv/bin/pytest tests/test_subjects.py tests/test_math_route_plan.py tests/test_algebra_fallback_seed.py tests/test_geometry_fallback_seed.py tests/test_health.py -q
26 passed, 3 warnings in 2.01s

cd apps/frontend
npm run typecheck
exit 0
```

Stage 18 production student smoke after UI/API deploy:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/mvp-student-flow.spec.ts --grep "student can open topic" --project=chromium
1 passed (22.5s)
```

## Backups Used

Production backup/offsite verification was run before every production mutation in Month 2. Key manifests:

```text
manifest-20260814T184623Z.md5  # Stage 12 backend route deploy
manifest-20260814T194154Z.md5  # Stage 13 backend route deploy
manifest-20260814T210245Z.md5  # Stage 14 invalid Algebra material cleanup
manifest-20260814T214053Z.md5  # Stage 16 Algebra fallback registry mutation
manifest-20260814T215652Z.md5  # Stage 17 Geometry fallback registry mutation
manifest-20260814T220831Z.md5  # Stage 18 backend/frontend readiness UI deploy
```

All listed stage reports record offsite verification.

## Remaining Non-Blockers / Blockers

Blockers before Algebra/Geometry pilot:

- acquire owner-approved or clearly open-license Algebra sources;
- acquire owner-approved or clearly open-license Geometry sources;
- index and verify RAG chunks with stable metadata;
- run source-backed explanation smoke for representative topics.

Non-blockers:

- production marker remains `6e698a0` due targeted deploy mode;
- production working tree hygiene still needs a dedicated full-release cleanup stage;
- untracked stakeholder presentation intermediate files remain intentionally untouched.

## Month 3 Priorities

Proceed to Month 3 platform layer while keeping Math as the only pilot-ready subject:

1. Learning Analytics V1 for teacher/admin: attempts, accuracy, mastery, weak topics, recent activity.
2. Content Quality Workflow V1: repeatable statuses, QA loops, audit visibility.
3. Manual testing readiness: final human test plan and scenario scripts.
4. Production release hygiene: clean marker workflow before broad release deploys.
