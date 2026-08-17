# Next Stage 20 — AI Cost And Token Measurement — 2026-08-17

## Decision

AI cost baseline is **partially measured** from real production counters, but current post-restart live counters are empty.

Use the 7-day Prometheus `max_over_time` snapshot as the current evidence-backed baseline, and treat `increase()` over 7d as unreliable because backend restarts/counter resets inflated the values.

## Production AI Configuration

Read without exposing secrets:

```json
{
  "AI_BASE_URL_HOST": "api.minimax.io",
  "AI_BASE_URL_PATH": "/v1",
  "AI_MODEL": "MiniMax-M3",
  "AI_API_KEY_SET": true
}
```

No API keys, Bearer tokens, `.env`, or secret values were printed.

## Current Metrics State

Direct backend `/metrics` currently has no `ai_requests_total` / `ai_tokens_total` series after the recent backend recreate.

Admin Realtime snapshot currently shows:

```json
{
  "ai_modes": {},
  "ai_tokens": {},
  "http_total": {
    "2xx": 8,
    "4xx": 6,
    "5xx": 0
  }
}
```

Prometheus 24h `increase()` is zero:

```json
{
  "increase(ai_requests_total[24h])": [
    { "mode": "chat", "status": "ok", "value": "0" },
    { "mode": "explain", "status": "ok", "value": "0" },
    { "mode": "generate", "status": "ok", "value": "0" }
  ],
  "increase(ai_tokens_total[24h])": [
    { "role": "input", "value": "0" },
    { "role": "output", "value": "0" }
  ]
}
```

Interpretation: no measurable AI traffic since the latest backend recreate, or counters have not been re-created yet.

## Historical 7-Day Baseline

Prometheus still has historical series in the 7-day window.

### Request Counters

`max_over_time(ai_requests_total[7d])`:

| Mode | Status | Count |
|---|---|---:|
| chat | ok | 6 |
| check | ok | 106 |
| explain | ok | 54 |
| generate | ok | 53 |

### Token Counters

`max_over_time(ai_tokens_total[7d])`:

| Role | Tokens |
|---|---:|
| input | 285,016 |
| output | 114,402 |

### Counter Reset Caveat

`increase(ai_requests_total[7d])` and `increase(ai_tokens_total[7d])` returned much larger values than `max_over_time`, for example `8,300,813 input` and `4,396,762 output` tokens. Because backend restarts/recreates happened during the window, those `increase()` values are not reliable for cost baseline. Use `max_over_time` until counters are persisted or reset-safe recording rules exist.

## Cost Estimate

MiniMax-M3 pricing used for estimate: ≤512k input tier at `$0.30 / 1M input tokens` and `$1.20 / 1M output tokens`, from the MiniMax Pay-as-you-go pricing page.[1]

Using the conservative 7-day `max_over_time` baseline:

```text
Input:  285,016 tokens × $0.30 / 1M = $0.085505
Output: 114,402 tokens × $1.20 / 1M = $0.137282
Total:  $0.222787
```

Rounded baseline: **~$0.22** for the observed historical production AI counters.

This is not a billing statement. It is a telemetry estimate from app counters and current public pricing; actual billing may differ due to plan tier, cache reads/writes, long-context tiering, retries, provider-side accounting, or subscription/token-plan credits.

## Expensive Flow Flags

Based on request count:

1. `check` — 106 calls; likely frequent during practice answer evaluation.
2. `explain` — 54 calls; user-visible explanations can grow with longer context.
3. `generate` — 53 calls; exercise generation can become expensive under repeated practice.
4. `chat` — 6 calls; low count in current history.

Based on token mix:

- Output tokens are the main cost lever: 114,402 output tokens cost more than 285,016 input tokens under the observed price ratio.
- `generate` and `explain` should be monitored first once live usage resumes.

## Recommended Next Instrumentation

1. Add reset-safe Prometheus recording rules or persist AI usage events in DB so restarts do not distort `increase()`.
2. Add per-mode token counters, not only global input/output counters, so cost by flow can be calculated precisely.
3. Add cache-read/write counters if MiniMax prompt caching is enabled later.
4. After the next real AI-heavy lesson, capture `/metrics` immediately and again after Prometheus scrape to establish fresh non-empty current counters.

## Production Health

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
```

## Verification

Commands run:

```text
Prometheus query API:
- ai_requests_total
- ai_tokens_total
- sum by (mode,status) (ai_requests_total)
- sum by (role) (ai_tokens_total)
- increase(ai_requests_total[24h])
- increase(ai_tokens_total[24h])
- sum by (mode,status) (max_over_time(ai_requests_total[7d]))
- sum by (role) (max_over_time(ai_tokens_total[7d]))
- sum by (mode,status) (increase(ai_requests_total[7d]))
- sum by (role) (increase(ai_tokens_total[7d]))
```

No secrets were printed. No production mutation was performed.

## Done Criteria

- Prometheus query output captured: complete.
- Non-empty historical counters found: complete.
- Current post-restart empty counter state documented: complete.
- Cost estimate produced from measured tokens: complete.
- Expensive flows flagged: complete.
- No secrets in logs: complete.
- Commit: pending at report creation.

## Sources

[1] MiniMax Pay as You Go pricing — https://platform.minimax.io/docs/guides/pricing-paygo
