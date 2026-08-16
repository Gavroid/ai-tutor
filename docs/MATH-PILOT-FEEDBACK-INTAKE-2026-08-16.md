# Math Pilot Feedback Intake — 2026-08-16

## Purpose

Single place to paste, triage, and decide on feedback from Math manual pilot testing. This file is intentionally account-neutral: do not paste passwords, tokens, cookies, screenshots with secrets, `.env`, private keys, JWTs, Bearer values, or SMB credentials.

## Current Pilot Scope

- Pilot subject: Math repeat (`subject_id=3`).
- Math readiness: route `42/42`, sources/RAG `42/42`, deterministic practice `42/42`.
- Algebra and Geometry remain preview and must not be treated as pilot-ready.

## Severity Rules

| Severity | Meaning | Examples | Default action |
|---|---|---|---|
| Blocker | Pilot cannot continue or safety/privacy is broken | `/ready` fails; student sees hidden answer before submit; parent sees raw AI chat; Math practice cannot be checked | Stop pilot and fix immediately |
| High | Core role cannot complete main task | Teacher cannot save QA status; parent dashboard fails; admin audit inaccessible; student cannot finish topic | Fix before next pilot session |
| Medium | Workaround exists but confidence is reduced | Slow route, confusing copy, repeated practice task, unclear empty state | Batch into next polish pass |
| Low | Cosmetic or wording issue | Typo, spacing, minor label inconsistency | Fix opportunistically |

## Intake Table

| ID | Date/time MSK | Reporter | Role | Route/page | Scenario | Step | Expected | Actual | Severity | Evidence path | Reproducible? | Owner | Decision | Status |
|---|---|---|---|---|---|---:|---|---|---|---|---|---|---|---|
| MATH-FB-001 |  |  | Student/Parent/Teacher/Admin |  |  |  |  |  | Blocker/High/Medium/Low |  | yes/no |  |  | New |

## Triage Checklist

For every feedback row:

1. Confirm role and route.
2. Check whether issue violates a hard boundary:
   - hidden answer leak;
   - raw JSON / `<think>` / broken markdown;
   - parent raw chat exposure;
   - wrong subject readiness;
   - `/ready` or `/health` failure.
3. Reproduce with the smallest safe command or browser scenario.
4. If blocker/high: write or identify regression test before fixing.
5. If production mutation is needed: run backup + offsite first.
6. Close with evidence: test command, production smoke, docs update, commit.

## Scenario Tags

Use these tags in the `Scenario` field:

- `student-login`
- `student-subjects`
- `student-topic-explain`
- `student-practice-generate`
- `student-practice-check`
- `parent-dashboard`
- `parent-privacy`
- `teacher-analytics`
- `teacher-readiness`
- `teacher-qa-workflow`
- `admin-audit`
- `admin-realtime`
- `mobile`
- `recovery-error`

## Current Route Verification

Routes from the final manual testing plan were checked on production LAN and returned HTTP 200:

```text
/login
/register
/forgot-password
/subjects
/subjects/3
/diagnostic
/student/badges
/parents
/teacher
/teacher/topics
/teacher/generate
/admin
/ready
/health
```

## Decision Log

| Date | Decision | Evidence | Owner |
|---|---|---|---|
| 2026-08-16 | Intake framework created; no manual feedback rows yet | Route verification HTTP 200 for listed routes | Hermes |

## Stage 02 Closure

This document closes Next Stage 02. It gives manual pilot feedback a stable intake format and severity rule set.
