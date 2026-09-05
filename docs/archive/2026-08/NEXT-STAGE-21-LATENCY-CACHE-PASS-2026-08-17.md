# Next Stage 21 — Latency Budget And Cache Pass — 2026-08-17

## Decision

No code/cache change is required for Stage 21.

Common pilot routes are within an acceptable MVP latency budget after current caching. The only noticeable cold-cache path is `/api/v1/subjects`, but the existing cache already reduces it from ~381 ms cold to ~6.8 ms warm. Adding more cache/versioning now would add complexity without measured need.

## Latency Budget

| Route Class | MVP Budget | Rationale |
|---|---:|---|
| Public navigation routes | <100 ms warm | Used frequently in student/teacher navigation. |
| Protected analytics/dashboard routes | <250 ms median | Heavier DB aggregation is acceptable if stable. |
| Teacher readiness matrix | <250 ms median | Larger payload; acceptable if below 250 ms and no timeout. |
| Cold cache | Document only | Cold spikes are acceptable if warm behavior is stable. |

## Measurement Method

Measured inside the production backend container against `http://localhost:8000` to avoid WAN/browser noise.

For protected routes, short-lived JWTs were generated in memory inside the backend container from existing active users. Tokens were not printed or persisted.

Sample count:

- Public routes: 7 requests each.
- Heavier protected routes: 5–7 requests each.

## Production Timing Results

| Route | HTTP | Payload | First ms | Median ms | P95-ish ms | Max ms | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| `/api/v1/subjects` | 200 | 7,931 B | 381.20 | 6.75 | 7.23 | 381.20 | Existing cache effective; no change. |
| `/api/v1/subjects/3/route-plan` | 200 | 7,804 B | 4.58 | 4.74 | 4.94 | 9.33 | Healthy. |
| `/api/v1/subjects/4/route-plan` | 200 | 3,631 B | 3.92 | 4.14 | 4.69 | 4.72 | Healthy. |
| `/api/v1/subjects/5/route-plan` | 200 | 2,719 B | 4.24 | 4.24 | 4.58 | 5.08 | Healthy. |
| `/api/v1/topics/187` | 200 | 129 B | 41.99 | 8.79 | 41.99 | 44.37 | Healthy. |
| `/api/v1/analytics/learning?days=30` | 200 | 4,565 B | 28.49 | 23.31 | 28.49 | 29.42 | Healthy. |
| `/api/v1/teacher/topics/readiness?subject_id=3` | 200 | 26,235 B | 153.86 | 139.90 | 153.86 | 201.22 | Largest route but within budget. |
| `/api/v1/parents/students/51/dashboard` | 200 | 4,569 B | 49.65 | 35.50 | 44.01 | 49.65 | Healthy. |

## Findings

### `/subjects`

The first request took ~381 ms and subsequent requests dropped to ~6–7 ms. This confirms the current Redis/read-through cache is doing useful work. No cache key/versioning change is needed in this stage.

### Route Plans

Math, Algebra, and Geometry route plans are all ~4–5 ms. These are static in-process route maps and do not need extra caching.

### Topic Detail

Topic detail is small and warm median is ~8.8 ms. No blocker.

### Learning Analytics

Teacher analytics median is ~23 ms. This is safe for MVP teacher use and does not need additional caching yet.

### Teacher Readiness Matrix

Teacher readiness is the heaviest measured route: median ~140 ms, max ~201 ms, payload ~26 KB. This is still below the 250 ms MVP budget. Do not cache yet because readiness can change after content QA/fallback/RAG updates and stale readiness would be more harmful than a 140 ms response.

### Parent Dashboard

Parent dashboard median is ~35.5 ms with current linked student data. Privacy boundary was not changed and no raw chat was requested or exposed by this measurement.

## Cache Decision

No new cache layer added.

Reasons:

- Existing `/subjects` cache already fixes the one visible cold-cache spike.
- Route-plan endpoints are already very fast.
- Analytics and parent dashboard are comfortably within budget.
- Teacher readiness is acceptable and should remain fresh during content QA/RAG work.

## Production Health

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Verification

Commands performed:

```text
Production health check:
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

Production local timing script:

```text
subjects median=6.75 ms, first=381.20 ms
math_route_plan median=4.74 ms
algebra_route_plan median=4.14 ms
geometry_route_plan median=4.24 ms
topic_detail_math_187 median=8.79 ms
learning_analytics_teacher median=23.31 ms
teacher_readiness_math median=139.90 ms
parent_dashboard median=35.50 ms
```

No secrets were printed. No production data was mutated.

## Done Criteria

- `/subjects` measured: complete.
- Route-plan endpoints measured: complete.
- Topic detail measured: complete.
- Analytics measured: complete.
- Parent dashboard measured: complete.
- Slow/cold-cache paths identified: complete.
- Cache/versioning decision documented: complete.
- Commit: pending at report creation.
