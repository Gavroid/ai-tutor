# Stage 24 — Performance And Cost Review — 2026-08-15

## Scope

Stage 24 goal: establish a production performance/cost baseline for pilot scaling.

## Production Baseline

```text
production marker: 6e698a0
/ready HTTP=200
/health HTTP=200
backend/frontend/db/redis/prometheus healthy; grafana/proxy running
```

## Container Resource Snapshot

Measured with `docker stats --no-stream` on production:

| Service | CPU | Memory | Memory % |
|---|---:|---:|---:|
| backend | 0.44% | 457.4 MiB / 4 GiB | 11.17% |
| frontend | 0.00% | 72.91 MiB / 4 GiB | 1.78% |
| db | 0.00% | 118.6 MiB / 4 GiB | 2.90% |
| redis | 0.45% | 5.145 MiB / 4 GiB | 0.13% |
| prometheus | 0.00% | 44.59 MiB / 256 MiB | 17.42% |
| grafana | 0.04% | 65.46 MiB / 256 MiB | 25.57% |

Interpretation: backend memory is the largest app component but still within comfortable pilot headroom. Prometheus/Grafana are within configured 256 MiB limits.

## Route Latency Snapshot

Measured with production `curl` timings against nginx/TLS localhost:

| Route | HTTP | TTFB | Total |
|---|---:|---:|---:|
| `/ready` | 200 | 0.011111s | 0.011156s |
| `/health` | 200 | 0.011193s | 0.011234s |
| `/api/v1/subjects` | 200 | 0.363173s | 0.363219s |
| `/api/v1/subjects/3/route-plan` | 200 | 0.018635s | 0.018679s |

Interpretation: health/route-plan are fast; `/subjects` is acceptable but noticeably slower because it now computes readiness counts. Cache is already enabled through Redis (`subjects:v3:*`), so repeat-user latency should improve after warm cache.

## Frontend Load Snapshot

Measured with Playwright Chromium mobile viewport `390 × 844`, `networkidle`:

| URL | Wall time | DOMContentLoaded | Load end | Response start | Transfer size | Overflow |
|---|---:|---:|---:|---:|---:|---|
| `/login` | 689ms | 84ms | 196ms | 48ms | 4,153 bytes | false |
| `/subjects` | 857ms | 27ms | 55ms | 5ms | 4,598 bytes | false |
| `/subjects/3` | 631ms | 72ms | 79ms | 35ms | 4,752 bytes | false |

Interpretation: primary mobile pages are responsive and do not horizontally overflow in the sampled viewport.

## Prometheus Snapshot

Prometheus query API returned:

```text
http_4xx_rate = 0
http_5xx_rate = empty/no current 5xx samples
http_requests_by_path_status:
  /api/v1/subjects 200 = 2
  /api/v1/auth/me 401 = 2
  /api/v1/subjects/{subject_id}/route-plan 200 = 1
  /api/v1/progress/due-for-review 401 = 1
  /api/v1/ai/ping 401 = 1
  /api/v1/progress/recommend-review 401 = 1
```

`histogram_quantile` returned `NaN` for the short 15-minute rate window because the current post-restart sample volume is too small for meaningful quantiles. Direct route timings above are therefore the authoritative Stage 24 latency baseline.

## AI Cost / Token Baseline

Prometheus queries:

```text
sum(ai_requests_total) = empty
sum by (mode,status) (ai_requests_total) = empty
sum by (role) (ai_tokens_total) = empty
```

Interpretation: after the latest backend restart, no AI request/token counters were present in the current Prometheus runtime. This means current marginal AI cost in the measured window is zero/unknown rather than high. Cost tracking exists through `ai_requests_total` and `ai_tokens_total`, but a future live lesson with real AI calls should be measured again after user activity.

## Existing Cost Controls

Current controls already present in code/config:

- AI provider timeout: `ai_timeout_seconds`.
- AI provider retries: `ai_max_retries`.
- Input cap: `ai_max_input_chars`.
- Redis cache for read-heavy subjects/topics/materials.
- Deterministic fallback practice banks for Math/Algebra/Geometry reduce dependency on free-text generation for common practice.
- Rate limits for login/register/AI endpoints remain active.

## Bottlenecks / Risks

| Area | Status | Action |
|---|---|---|
| `/subjects` readiness query | Acceptable but slower than route-plan | Keep Redis cache; revisit only if >1s after warm cache |
| AI cost visibility | No current AI samples after restart | Re-measure after a real AI lesson/session |
| Prometheus quantiles | `NaN` with tiny sample volume | Use direct timings for baseline; quantiles become useful after traffic |
| Backend memory | ~457 MiB | Acceptable for pilot; monitor if workers or AI/RAG load grows |
| Frontend mobile load | <1s sampled pages | No immediate action |

## Verification Commands

```text
cd apps/backend
.venv/bin/pytest tests/test_ops_metrics.py tests/test_health.py -q
10 passed, 3 warnings
```

Production health was verified after measurements:

```text
/ready HTTP=200
/health HTTP=200
```

## Decision

No performance/cost blocker for manual pilot at current traffic. The only follow-up is to repeat AI token/cost measurement after a real AI-heavy lesson because the current measured window has no AI counters.

## Next Stage

Proceed to Stage 25 — Security And Privacy Review.
