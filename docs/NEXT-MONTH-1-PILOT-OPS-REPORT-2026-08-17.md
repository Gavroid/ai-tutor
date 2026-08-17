# Next Month 1 Pilot Operations Report — 2026-08-17

## Executive Decision

**Recommendation: conditional GO for one supervised Math-only real child pilot session.**

Math is ready for a narrow manual pilot if the operator follows the feedback intake process and keeps scope limited to verified Math routes. This is **not** a go for broad release, unsupervised rollout, Algebra, or Geometry.

## Current Production Baseline

Checked at `2026-08-17 15:32 MSK` after Stage 08 targeted deploy:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
backend/frontend/db/redis/prometheus healthy
grafana/proxy running
```

Production marker remains intentionally unchanged because production tree is still dirty/on `master`; targeted deploy mode remains active.

## Stage 01–08 Evidence Summary

| Stage | Evidence | Pilot Impact |
|---|---|---|
| Stage 01 — Release Hygiene | Production healthy but marker/release state untrustworthy; marker `6e698a0`; dirty production tree documented. | Broad deploy and marker advancement remain blocked, but targeted deploys are safe with backup/offsite. |
| Stage 02 — Feedback Intake | Math pilot feedback intake template created with blocker/high/medium/low severity rules. | Real child session can be captured and triaged without inventing process mid-session. |
| Stage 03 — Student Evidence | Production student Math smoke passed; output cleanliness checked; route timing captured. | Student flow has current evidence beyond route availability. |
| Stage 04 — Explanation Sweep | Representative Math explanations checked; backend quality tests passed. | Math explanations are usable enough for supervised pilot. |
| Stage 05 — Practice Rotation | Production fallback registry fixed after backup/offsite; sampled topics now rotate 3/3 unique questions. | Repeat practice no longer obviously loops stale tasks on sampled topics. |
| Stage 06 — Parent Report | Backend parent tests `18 passed`; parent E2E `1 passed`; privacy boundary verified with seeded/mocked evidence. | Parent dashboard is privacy-safe, but production had no active parent-child link for live smoke. |
| Stage 07 — Teacher QA | Backend teacher+health tests `46 passed`; teacher Playwright `2 passed`; `blocked/needs_review` cannot publish; audit transitions verified. | Teacher review path is covered and unsafe material states are blocked from publication. |
| Stage 08 — Admin Monitoring | Backend ops slice `12 passed`; Admin Realtime smoke `1 passed`; Prometheus rules ok; active alerts `0`; DB/Redis/disk/backup visible. | Operator can inspect app health without SSH; monitoring gap found and fixed. |

## Issue Register

### Blockers

- **Broad release hygiene:** production tree is dirty/on `master`, marker remains `6e698a0`, and full release/marker advancement must wait for a dedicated cleanup workflow.
- **Algebra/Geometry readiness:** both remain `preview`; source/RAG coverage is still `0` for those subjects and they must not be treated as pilot-ready.

### High

- **Pilot data capture discipline:** real child session must use the Stage 02 intake table immediately; otherwise feedback becomes anecdotal and hard to triage.
- **Parent live evidence gap:** parent dashboard behavior is tested, but production had no active parent-child link during Stage 06; create/link only through normal user flow if parent live review is needed.
- **Targeted deploy discipline:** any further production mutation must continue to run backup + offsite verification first.

### Medium

- **Teacher material QA evidence is mocked/browser-assisted:** workflow is covered and backend audited, but production content QA should be exercised with real teacher account during manual pilot ops.
- **4xx interpretation:** Admin Realtime now separates expected vs actionable 4xx, but operators still need to interpret auth probes and missing drafts correctly.
- **Practice depth:** sampled fallback rotation is fixed, but broader Math editorial quality should continue improving as real feedback arrives.

### Low

- **Warnings:** pytest still reports dependency deprecation warnings (`pytest-asyncio`, `passlib`, Pydantic V2 config style); no current pilot blocker.
- **Untracked presentation/tmp artifacts:** existing untracked docs/tmp files remain outside the staged plan work and were not deleted.

## Go / No-Go

### GO

Proceed with **one supervised Math-only session** if all of these are true immediately before the session:

1. `/ready` and `/health` return `200`.
2. Admin Realtime shows DB/Redis `ok`, no 5xx, and fresh backup age below 26h.
3. The session uses Math subject only (`subject_id=3`).
4. Feedback is recorded in `docs/MATH-PILOT-FEEDBACK-INTAKE-2026-08-16.md` format.
5. An adult/operator is available to stop if output quality, privacy, or UX breaks.

### NO-GO

Do not proceed with:

- Algebra or Geometry pilot sessions.
- Broad user rollout.
- Full destructive release deploy or marker advancement.
- Any workflow that requires exposing raw AI chat to parent/admin dashboards.
- Any production content/data mutation without backup + offsite verification.

## Immediate Next-Month Priorities

1. **Stage 10 — Source Acquisition Policy:** write hard pass/fail rules for acceptable educational sources before importing anything.
2. **Stage 11–12 — Algebra/Geometry Candidate Search:** find legally usable sources or document blocker remains.
3. **Stage 13–16 — Import/RAG Dry Runs:** only if sources pass the policy gate; keep preview subjects preview until coverage is verified.
4. **Release Hygiene Follow-Up:** restore clean production branch/marker workflow so broad deploys are safe again.
5. **Real Pilot Feedback Loop:** run the first supervised Math session and convert findings into blocker/high/medium/low issues.

## Verification Used For This Report

```text
git log --oneline -10
ba60276 feat: close next stage 08 admin monitoring drill
55a8b2b test: close next stage 07 teacher qa evidence
3ca19b6 docs: add next session handoff
b4512f8 docs: close next stage 06 parent evidence
172588f docs: close next stage 05 math practice rotation
af5fc71 docs: close next stage 04 math explanation sweep
b7991a5 docs: close next stage 03 math student evidence
417190b docs: close next stage 02 feedback intake
70e5567 docs: close next stage 01 release hygiene
```

```text
Production health:
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
backend/frontend/db/redis/prometheus healthy
grafana/proxy running
```

Report references actual Stage 01–08 reports and current production health. No production mutation was performed for Stage 09.

## Done Criteria

- Stage 01–08 evidence consolidated: complete.
- Blocker/high/medium/low issue register: complete.
- Math manual pilot go/no-go recommendation: complete.
- Next-month priorities updated: complete.
- Current production health referenced: complete.
- Commit: pending at report creation.
