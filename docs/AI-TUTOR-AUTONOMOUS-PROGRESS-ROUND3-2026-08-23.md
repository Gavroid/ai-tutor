# AI-Tutor — autonomous progress update, 2026-08-23

## New completed slices

### Math-6-only pilot scope

- Fixed evidence loader to derive public promotion flags through canonical fail-closed policy.
- Persisted `pilot_visible=true` for Algebra/other subjects no longer bypasses scope.
- Verified API exposes only `math` as pilot-visible.
- Full backend regression after fix: `1312 passed, 29 skipped, 15 warnings`.

### Backup safety

- Added local read-only backup artifact preflight: size, gzip, SQL signature, SHA-256.
- Tests: `4 passed`.
- Actual Docker restore remains blocked by missing Docker/CI environment.

### Dependency and test hygiene

- Current frontend audit recorded: `4 high severity vulnerabilities`; unsafe `npm audit fix --force` deliberately not run.
- Registered pytest markers `slow` and `timeout`.
- Replaced deprecated sentence-transformers dimension API with compatible getter fallback.
- Embedding/retrieval checks: `14 passed` after warning fix.

### Production read-only health

- `/health`: HTTP 200, `status=ok`.
- `/ready`: HTTP 200, `status=ready`.
- Only GET requests executed; no deployment, marker write, DB mutation, RAG import, or user AI request.

## Commits

```text
f5fc083 fix(ai-tutor): enforce math-only pilot scope from evidence
603ea3a docs(ai-tutor): record read-only production health
99a8f3c chore(ai-tutor): register pytest markers and modernize embedding API
```

## Remaining hard gates

1. Docker/CI disposable staging.
2. Actual backup + offsite verification + PostgreSQL restore drill.
3. Full Playwright smoke against staging.
4. Manual child/parent learning walkthrough.
5. Security dependency upgrades with separate compatibility regressions.
6. Owner approval for production rollout.

Pre-existing dirty files remain untouched and are not included in the commits above.
