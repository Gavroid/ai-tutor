# Current Pilot Status — 2026-08-14

_Recorded: 2026-08-14 18:17 MSK_

## Scope

This status closes Stage 01 of `docs/AUTONOMOUS-3-MONTH-EXECUTION-PLAN-2026-08-14.md`: Pilot Baseline And Repo Hygiene.

## Repository Baseline

- Workspace: `/root/workspace/ai-tutor`
- Branch: `mvp-rescue`
- Latest local commit at baseline: `c98c3c7 docs: add autonomous three month execution plan`
- Production marker: `6e698a0`
- Important current deployment commit: `6e698a0 fix: expose diagnostic correct answer`

## Production Health

Command evidence collected over SSH from `root@192.168.1.86` without printing secrets:

```text
MARKER=6e698a0
READY={"status":"ready"} HTTP=200
HEALTH={"status":"ok","service":"AI Tutor 7","env":"production","version":"0.1.0-mvp"} HTTP=200
```

Docker Compose service state:

```text
deploy-backend-1      running   healthy
deploy-db-1           running   healthy
deploy-frontend-1     running   healthy
deploy-grafana-1      running
deploy-prometheus-1   running   healthy
deploy-proxy-1        running
deploy-redis-1        running   healthy
```

## Pilot Scope Baseline

- Pilot subject: `Математика (6 класс — повторение пройденного материала)`
- Math technical readiness: `42/42`
- Math verified source coverage: `42/42`
- Math followup coverage: `42/42`
- Math route plan: `/api/v1/subjects/3/route-plan`
- Math diagnostic: 8 checkpoint questions, includes `correct_answer`

## Presentation Artifacts

Committed and discoverable stakeholder artifacts:

```text
docs/AI-Tutor-Stakeholder-Presentation-2026-08-14.pdf
docs/AI-Tutor-Stakeholder-Presentation-2026-08-14.html
docs/AI-Tutor-Stakeholder-Presentation-2026-08-14.md
docs/AI-Tutor-Stakeholder-Presentation-SLIDES-2026-08-14.md
docs/AI-Tutor-Stakeholder-Presentation-2026-08-14-FINAL.pptx
```

Known untracked intermediate artifacts intentionally left untouched in Stage 01:

```text
docs/AI-Tutor-Stakeholder-Presentation-2026-08-14.pptx
docs/AI-Tutor-Stakeholder-Presentation-PANDOC-2026-08-14.pptx
docs/AI-Tutor-Stakeholder-Presentation-SAFE-2026-08-14.pptx
tmp/stakeholder-html-qa/slide-01.jpg ... slide-18.jpg
```

Decision: keep these untracked for now because the plan explicitly marks them as intermediate artifacts from an earlier presentation generation attempt and says not to delete them outside a dedicated cleanup stage.

## Stage 01 Verification

- `git status --short --branch` inspected and documented.
- Production marker confirmed from `/opt/ai-tutor/.mvp-rescue-commit`.
- Production `/ready` returned HTTP 200.
- Production `/health` returned HTTP 200.
- Docker services checked through `docker compose ps`.
- No production mutation performed; no backup required for this read-only stage.

## Next Stage

Proceed to Stage 02: create a structured 42-topic math editorial review framework and ensure every topic has a human-review slot and clear quality status.
