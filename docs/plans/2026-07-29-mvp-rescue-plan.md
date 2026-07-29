# MVP Rescue Plan — AI Tutor

> **For Hermes:** use `test-driven-development` for every code change. No feature creep until MVP gate is green.

**Date:** 2026-07-29

**Goal:** turn the current overgrown prototype into a usable MVP for a 7th-grade student pilot.

**Current verdict:** not MVP-ready. The repo builds and selected backend tests pass, but the core student path is broken by raw AI reasoning leakage, weak structured-output parsing, old inconsistent UI, and misleading production health checks.

---

## Evidence From Current Audit

### Confirmed Blockers

1. **AI leaks reasoning to users**
   - Production `/api/v1/ai/explain` returned escaped `<think>...` as visible lesson content.
   - Production `/api/v2/exercises/generate` returned `question_text` beginning with escaped `<think>...`, then truncated.
   - Root cause candidates:
     - `apps/backend/app/ai/hermes.py` only parses JSON when response starts/ends with `{}` after `sanitize_output()`.
     - `apps/backend/app/ai/sanitize.py` escapes HTML before structured parsing, so `<think>` becomes `&lt;think&gt;` and survives as user-visible text.
     - `apps/backend/app/ai/service.py` fallback copies `resp.content[:500]` into exercise text.

2. **Structured AI output is not robust enough for MVP**
   - Prompt says “STRICT JSON”, but MiniMax emits reasoning first.
   - `service.generate_exercise()` accepts fallback text as valid exercise instead of failing cleanly or retrying.
   - `check_answer()` fallback returns raw model content as explanation.
   - Teacher generation inherits the same escaped-content parse failure from the provider path.

3. **Exercise correctness is not trustworthy**
   - `apps/backend/app/v2/exercises.py` defaults many generated exercises to keyword checking.
   - For single-choice options like “Вариант A/B/C”, wrong choices can pass because all answers share common words.
   - Adaptive difficulty is computed as `target_difficulty`, but generation/storage still use `payload.difficulty`; frontend sends explicit topic difficulty, so auto mode is bypassed.
   - Frontend “Покажи правильный ответ” shows `(недоступен)` because v2 submit never returns/stores `correct_answer`.

4. **Student lesson page is not redesigned**
   - `apps/frontend/app/topics/[id]/page.tsx` still uses old narrow slate layout, plain buttons, alerts, and raw text blocks.
   - `SafeMarkdown` exists but exercise question/explanation/check result are still displayed as plain text / `whitespace-pre-wrap` in key places.
   - WebSocket errors are appended into assistant content as `[Ошибка: ...]`; other failures use blocking `alert()` dialogs.
   - Chat context is suspect: frontend sends `topicId`, backend reads `topic_id`; heartbeat sends `{type:"ping"}`, backend can treat it as a chat payload.

5. **Auth/navigation UX is inconsistent**
   - Root route `/` is only a redirect spinner with “Загрузка…”, not an MVP landing/loading experience.
   - `getToken()` always returns `"cookie"`, so core pages optimistically render and fail silently instead of having clear auth loading/redirect states.
   - `/subjects` logout only pushes `/login` and does not call backend `api.logout()`.
   - New `Header` redesign is unused in core student routes.

6. **Production readiness is misleading**
   - `/ready` can return HTTP 200 even when the body is `not_ready`; deploy workflow checks only HTTP code.
   - Backend logs showed Redis readiness failures around the same audit while Redis container itself responded `PONG`.
   - Duplicate backup cron runs at 03:00 from both root crontab and `/etc/cron.d/ai-tutor-backup`, creating race/corruption risk.
   - Deploy rollback path still contains `TODO`, and production release artifacts were not proven.

7. **Testing coverage is inflated around MVP path**
   - Local selected backend tests passed: `23 passed`, but with runtime warnings.
   - `apps/frontend/e2e/pilot.spec.ts` exists, but frontend `package.json` has no `test`, `lint`, or E2E script, so MVP browser flow is not an obvious CI/local gate.
   - Current E2E coverage is not enough until it explicitly asserts “no `<think>` / no escaped reasoning / valid exercise / clean feedback”.

8. **Design system is partially broken**
   - New UI components use classes like `bg-brand-500`, `bg-surface`, `border-border`, `bg-danger`.
   - Generated CSS check showed several token classes missing, which means “2026 design” components can silently render without intended styling.
   - `apps/frontend/app/topics/[id]/page.tsx` still mostly bypasses the new component system.

9. **Production drift exists**
   - GitHub/local main HEAD is `caa81c9`.
   - Production `/opt/ai-tutor` git metadata earlier showed `master/cb99f2b` while containers run newer built artifacts.
   - Treat release artifacts/container behavior as source of truth until deploy pipeline is fixed.

---

## MVP Definition

MVP means the following path works reliably for one student and one parent:

1. Login.
2. See clear subject/topic list.
3. Open one topic.
4. Press **Explain** and receive clean, concise, age-appropriate output with no `<think>`, JSON, escaped HTML, provider garbage, or giant walls of text.
5. Press **Practice** and receive one valid exercise with answer options/input.
6. Submit answer and receive clean feedback plus next action.
7. Leave/return without losing draft.
8. Parent can see a simple progress summary.
9. Production `/health` and `/ready` truthfully fail when dependencies fail.
10. CI verifies this MVP flow before deploy.

Everything else is non-MVP until this is green: teacher flows, admin realtime, GraphQL, CGM UI, badges, voice, complex dashboards, extra AI modes.

---

## Phase 0 — Freeze Scope And Baseline

**Objective:** stop adding features and establish a reliable baseline.

**Files:**
- Read: `apps/backend/app/ai/*`
- Read: `apps/frontend/app/topics/[id]/page.tsx`
- Read: `apps/frontend/app/subjects/page.tsx`
- Read: `apps/backend/tests/*ai*`
- Read: `.github/workflows/*.yml`

**Steps:**
1. Create branch: `mvp-rescue`.
2. Run baseline:
   - `cd apps/frontend && npm run build`
   - `cd apps/backend && .venv/bin/pytest tests/test_ai.py tests/test_pilot_secure_exercises_v2.py tests/test_health.py -q`
3. Capture production smoke samples for explain/generate/check.
4. Do not touch production until local MVP gate is green.

**Acceptance:** baseline commands and known failures documented.

---

## Phase 1 — Fix AI Output Contract First

**Objective:** no user-visible provider reasoning, malformed JSON, escaped `<think>`, or raw fallback blobs.

### Task 1.1 — Add AI output cleaning tests

**Files:**
- Create/modify: `apps/backend/tests/test_ai_output_contract.py`
- Modify after RED: `apps/backend/app/ai/hermes.py`, `apps/backend/app/ai/sanitize.py`

**Required tests:**
- strips raw `<think>...</think>` before rendering
- strips escaped `&lt;think&gt;...&lt;/think&gt;`
- extracts first valid JSON object even if model prepends reasoning
- rejects malformed structured exercise instead of turning reasoning into `question_text`
- preserves safe Markdown after cleaning

**Command:**
```bash
cd apps/backend
.venv/bin/pytest tests/test_ai_output_contract.py -q
```

### Task 1.2 — Parse before HTML escaping

**Files:**
- Modify: `apps/backend/app/ai/hermes.py`
- Modify: `apps/backend/app/ai/sanitize.py`

**Implementation direction:**
- Keep `raw_content` separate.
- Strip provider reasoning from raw content.
- Try structured extraction from cleaned raw content before `html.escape`.
- Only then sanitize display content.
- Never expose `<think>` content in `AIResponse.content`.

### Task 1.3 — Make exercise generation fail closed

**Files:**
- Modify: `apps/backend/app/ai/service.py`
- Modify: `apps/backend/app/v2/exercises.py`

**Rules:**
- If structured JSON is absent/invalid after retries, return a controlled 502/503-style app error, not a fake exercise.
- Validate exercise fields:
  - `question_text` length > 10 and no `<think>` / JSON braces blob
  - `type` in allowed set
  - options required for `single`/`multiple`
  - `correct_answer` not placeholder
- Add one retry with stronger “return JSON only” repair prompt if first parse fails.

### Task 1.4 — Clean check/hint/explain outputs

**Files:**
- Modify: `apps/backend/app/ai/service.py`
- Modify: `apps/backend/app/ai/prompts.py`
- Modify: `apps/backend/app/ai/router.py`

**Rules:**
- Explain: max 5 short sections, no reasoning, no meta-commentary.
- Hint: one hint only, no answer at level 1/2.
- Check: if structured parse fails, return controlled fallback message, not raw model dump.

### Task 1.5 — Fix answer checking and adaptive difficulty

**Files:**
- Modify: `apps/backend/app/v2/exercises.py`
- Modify: `apps/frontend/app/topics/[id]/page.tsx`
- Test: `apps/backend/tests/test_pilot_secure_exercises_v2.py`

**Rules:**
- `single`/`multiple` choice must use exact option matching, not keyword matching.
- Store/use `target_difficulty`, not `payload.difficulty`, after adaptive computation.
- Frontend should send `difficulty: 0` when user asks for auto/adaptive practice.
- Remove broken “Покажи правильный ответ” reveal unless backend returns a safe post-submit answer.

**Acceptance:** wrong single-choice option cannot pass because of shared words, and generated exercise difficulty reflects adaptive mode.

---

## Phase 2 — Redesign The Core Student Flow

**Objective:** make the product feel like a real MVP, not a pile of sprint widgets.

**Primary file:**
- `apps/frontend/app/topics/[id]/page.tsx`

**Supporting files:**
- `apps/frontend/components/SafeMarkdown.tsx`
- `apps/frontend/lib/markdown.ts`
- `apps/frontend/components/ui/*`
- `apps/frontend/app/subjects/page.tsx`
- `apps/frontend/app/globals.css`

### UX Strategy

Use one clean “learning workspace”:
- left/top: topic context and progress
- central: AI explanation / conversation
- right/bottom: practice card
- 3 primary actions only: **Объяснить**, **Практика**, **Подсказка**
- hide non-MVP clutter unless useful in the current state

### Required Fixes

1. Replace `alert(...)` with inline error cards.
2. Render exercise explanations and feedback via `SafeMarkdown` or normalized text component.
3. Add `aria-live` for AI answer, generation, check result, and errors.
4. Remove raw `whitespace-pre-wrap` for AI-originated content.
5. Make mobile layout first-class.
6. Add clear loading states per action, not one global ambiguous `busy`.
7. Use the design tokens already in `globals.css`; stop mixing old `slate/sky/emerald` ad hoc styles.
8. Add “what to do next” CTA after every AI result.

**Acceptance:** one topic lesson can be used by a child without seeing technical/internal text.

---

## Phase 3 — Simplify Navigation To MVP

**Objective:** remove distraction from the first pilot.

**Files:**
- `apps/frontend/app/subjects/page.tsx`
- `apps/frontend/components/Header.tsx`
- `apps/frontend/app/page.tsx`
- potentially route guards/layout

**Rules:**
- Student sees: Subjects, Continue/Review, Profile/Logout.
- Parent sees: Child summary, weak topics, recent activity.
- Admin/teacher/diagnostic/CGM/voice/badges remain accessible only if role-gated and not prominent for student MVP.

**Acceptance:** landing after login has one obvious next action.

---

## Phase 4 — Fix Readiness And Deploy Gates

**Objective:** production status must be truthful.

**Files:**
- `apps/backend/app/main.py`
- `apps/backend/app/config.py`
- `.github/workflows/deploy.yml`
- `deploy/release/smoke.sh` if present

**Tasks:**
1. Fix Redis readiness client. Current code appears to await a sync Redis client or wrong helper.
2. Return HTTP 503 for `not_ready`.
3. Update deploy healthcheck to inspect JSON body, not only HTTP code.
4. Make Prometheus `/metrics` 403 issue explicit: either intentional allowlist or broken scraping.
5. Remove duplicate 03:00 backup cron path; keep exactly one authoritative backup scheduler.
6. Remove unsafe SSH secret diagnostics from `.github/workflows/test.yml` if still present.
7. Replace rollback `TODO` with a real rollback or make deploy fail closed before pilot.
8. Restrict `/docs` / `/openapi.json` exposure or document why public schema exposure is acceptable.

**Acceptance:** `/ready` returns HTTP 200 only with `{"status":"ready"}`; backup runs once; deploy has a proven rollback/restore path.

---

## Phase 5 — Add Real MVP E2E

**Objective:** CI protects the actual student path.

**Files:**
- Create: `apps/frontend/e2e/student-mvp.spec.ts` or root `e2e/student-mvp.spec.ts`
- Create/modify: `apps/frontend/playwright.config.ts`
- Modify: `apps/frontend/package.json`
- Modify: `.github/workflows/ci.yml`

**Scenarios:**
1. Login as pilot student.
2. Open subjects.
3. Open first subject/topic.
4. Click Explain; assert no `<think>`, no JSON braces blob, no `&lt;think&gt;`.
5. Click Practice; assert valid question appears.
6. Submit answer; assert feedback appears and no alert/raw technical error.

**Acceptance:** E2E is run in CI or at least in deploy smoke before production.

---

## Phase 6 — MVP Pilot Hardening

**Objective:** make pilot recoverable and safe.

**Tasks:**
1. Verify backups and restore drill freshness.
2. Fix production git/release metadata display.
3. Add user-facing “AI temporarily unavailable” state.
4. Add budget/429 UX that tells the child what to do, not “HTTP 429”.
5. Confirm parent progress page hides child email/PII where not needed.

---

## Priority Order

1. **P0:** AI output contract and `<think>` stripping.
2. **P0:** fail-closed exercise generation.
3. **P0:** `/ready` HTTP/status correctness.
4. **P1:** redesign `topics/[id]` into MVP lesson workspace.
5. **P1:** E2E for student MVP flow.
6. **P1:** simplify student navigation.
7. **P2:** parent MVP polish.
8. **P2:** teacher/admin/voice/CGM cleanup later.

---

## Commands For Next Work Session

```bash
cd /root/workspace/ai-tutor
git checkout -b mvp-rescue

cd apps/backend
.venv/bin/pytest tests/test_ai.py tests/test_pilot_secure_exercises_v2.py tests/test_health.py -q

cd ../frontend
npm run build
```

Production read-only smoke:

```bash
TOKEN=$(curl -sk -X POST https://192.168.1.86/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"kirill@example.com","password":"Kirill2026!"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("access_token", ""))')

curl -sk -X POST https://192.168.1.86/api/v1/ai/explain \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"topic_id":1}' | python3 -m json.tool | head -80

curl -sk -X POST https://192.168.1.86/api/v2/exercises/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"topic_id":1,"difficulty":2}' | python3 -m json.tool
```

---

## Do Not Do Yet

- Do not add new product features.
- Do not redesign admin/teacher dashboards before student MVP.
- Do not deploy until AI output contract tests pass.
- Do not trust sprint counts/commit counts as readiness evidence.
- Do not accept fallback AI blobs as successful output.
