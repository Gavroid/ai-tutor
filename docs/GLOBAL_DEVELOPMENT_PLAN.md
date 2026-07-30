# AI-Tutor Global Development Plan

Date: 2026-07-30 17:29 MSK
Branch: `mvp-rescue`
Current repo HEAD when audited: `0b8b005`
Production marker when audited: `0b8b005`
Production host: `192.168.1.86`

> Purpose: a single, current, multi-level plan for turning the rescued AI-Tutor MVP into a reliable pilot product and then a scalable learning platform.

---

## 1. Executive Summary

The project has moved from “broken prototype” to a working **P0 pilot MVP** for one supported subject:

- Subject: `Математика (6 класс - повторение пройденного материала)`.
- Curriculum: rebuilt from two Vilenkin 6th grade textbook PDFs.
- Current production content state:
  - 42 real math topics.
  - 42 topic-scoped learning materials.
  - 832 RAG chunks.
  - 15 P0 pilot topics.
- Core student flow works:
  - login/logout;
  - topic page;
  - explain;
  - practice;
  - wrong answer;
  - corrected answer;
  - chat;
  - clear state.
- P0 topic smoke status:
  - 15/15 P0 topics have `Explain QA = Smoke OK`.
  - 15/15 P0 topics have `Practice QA = Smoke OK`.
  - P0 deterministic fallback bank is in place.
- Student-facing source links are intentionally hidden until exact citation mapping is reliable.

The next product milestone is not “more features”. It is **manual pilot confidence**: run real walkthroughs, record issues in `docs/pilot-topic-matrix.md`, and only then expand topic coverage.

---

## 2. Current Production Audit

### 2.1 Runtime Health

| Area | Status |
|---|---|
| Backend container | Healthy |
| Frontend container | Healthy |
| PostgreSQL | Healthy |
| Redis | Healthy |
| Prometheus | Healthy |
| Grafana | Running |
| Proxy | Running |
| `/ready` | `ready`, HTTP 200 |
| `/metrics` | HTTP 200 |
| Authoritative backup cron | `/etc/cron.d/ai-tutor-backup` exists |

### 2.2 Code/Test Surface

| Area | Count / Status |
|---|---:|
| Backend test files | 104 |
| Frontend E2E specs | 19 |
| Docs files | 37 |
| Latest backend targeted gate | 40 passed |
| Latest MVP E2E gate | 1 passed |

### 2.3 Important Recent Commits

| Commit | Meaning |
|---|---|
| `9f73bab` | Rebuild real math curriculum and RAG mapping. |
| `2c15562` | Clear math topic dependencies during RAG rebuild. |
| `d304244` | Remove visible AI text artefacts. |
| `7a94c3e` | Add pie chart practice fallback. |
| `8ef9224` | Hide recovery banner in MVP topic flow. |
| `372b552` | Define pilot plan and P0 practice fallback bank. |
| `0b8b005` | Mark P0 topic smoke readiness. |

### 2.4 Current Documentation Anchors

| File | Purpose |
|---|---|
| `docs/PILOT_PLAN.md` | Current MVP pilot plan and acceptance criteria. |
| `docs/pilot-topic-matrix.md` | 42-topic QA matrix with P0/P1/P2 status. |
| `docs/plans/2026-07-29-mvp-rescue-plan.md` | Historical MVP rescue execution plan. |
| `docs/AUDIT-FOR-NEXT-AI-2026-07-27.md` | Original handoff/audit file. |
| `docs/ROADMAP.md` | Older broad roadmap; partly stale after MVP rescue. |
| `docs/pilot-core-stage-2-plan.md` | Older stage-2 plan; useful as backlog input, not current source of truth. |

---

## 3. Architecture Audit

### 3.1 What Is Working Well

- FastAPI/Next/Postgres/Redis/Docker stack is operational on production.
- Cookie auth and HTTP student chat path are stable enough for MVP.
- `/ready` is now meaningful: it returns ready only when dependencies are ready.
- AI output contract is guarded against common model artefacts:
  - reasoning blocks;
  - escaped JSON;
  - LaTeX/code/table artefacts;
  - exposed `correct_answer`.
- RAG is now persistent in Postgres table `rag_chunks` and topic-scoped by rebuilt materials.
- Practice is server-owned through `/api/v2/exercises/generate` and `/answer`.
- Wrong answer → corrected answer works.
- Recovery banner no longer interrupts the main lesson UX.

### 3.2 Weak Points / Risks

| Risk | Severity | Current Mitigation | Next Action |
|---|---|---|---|
| AI may return off-topic or invalid structured JSON | High | P0 deterministic fallback bank | Expand fallback bank to P1 after pilot. |
| Student-facing sources can mislead | High | Sources hidden | Build exact citation mapping later. |
| AI budget can block student E2E | Medium | Reset test budget for smoke; admin explain smoke | Add dedicated test user/budget bypass for E2E. |
| WS remains fragile | Medium | Student chat uses HTTP | Either delete WS from student path or harden separately. |
| Topic quality beyond P0 unknown | Medium | Matrix tracks P1/P2 TODO | QA after P0 pilot. |
| Existing roadmap/docs stale | Medium | This plan becomes new source | Archive/annotate stale roadmap sections. |
| Warnings remain in tests | Low | Not blocking MVP | Clean after pilot stability. |

---

## 4. Product Stages

### Stage 0 — Completed: Rescue MVP

**Goal:** Make one student learning flow actually usable.

Completed:

- Rebuilt real math curriculum from 2 textbook PDFs.
- Reindexed topic-scoped RAG chunks.
- Fixed AI output parsing/sanitization.
- Fixed `/ready`, backup cron, frontend theme/readability, chat path, practice correction flow.
- Built P0 deterministic fallback bank.
- Added P0 matrix and pilot plan.

Exit status: **Done**.

---

### Stage 1 — Current: Guided P0 Pilot MVP

**Goal:** 5–15 short manual walkthroughs with P0 topics, with real feedback recorded.

#### Stage 1 Exit Criteria

- Manual QA completed for at least 5 P0 topics:
  - `187` Среднее арифметическое
  - `188` Проценты
  - `189` Круговые диаграммы
  - `196` Сравнение, сложение и вычитание обыкновенных дробей
  - `225` Решение уравнений
- For each manual topic:
  - Explain OK.
  - Practice OK.
  - Wrong→Correct OK.
  - Chat OK.
  - Clear OK.
  - No visual noise/regressions.
- `docs/pilot-topic-matrix.md` updated after every walkthrough.
- MVP E2E green after any fix.

#### Stage 1 Tasks

##### 1.1 Manual Walkthrough Recording

**Files:**
- Modify: `docs/pilot-topic-matrix.md`
- Optional create: `docs/pilot-walkthrough-notes.md`

**Actions:**
1. For each tested topic, update `Manual QA`:
   - `Manual OK` if no blocker.
   - `Issue: short note` if problem found.
2. If issue found, create a row in `docs/pilot-walkthrough-notes.md`:
   - date/time;
   - topic id;
   - screenshot path if any;
   - observed issue;
   - severity;
   - fix decision.

##### 1.2 Fix Only Walkthrough Blockers

Rules:

- No feature creep.
- Every bug fix uses TDD:
  - add failing regression;
  - verify RED;
  - implement;
  - verify GREEN;
  - run targeted gates;
  - deploy;
  - smoke.

##### 1.3 Stabilize E2E Budget Handling

Problem: student E2E can hit hourly AI limit.

Preferred solution:

- Add a dedicated E2E test user or admin-only smoke mode with separate budget bucket.
- Do not globally raise student budget just for tests.

Candidate implementation:

- Backend: allow `Role.ADMIN` bypass already exists for `/api/v1/ai/*`; verify `/api/v2/exercises/*` budget status.
- Frontend E2E: keep student login for UX, but reset only `ai-budget:*:1` keys before running prod E2E via a safe smoke script.
- Better long-term: create `kirill_e2e@example.com` with isolated progress/budget.

##### 1.4 Stage 1 Gate

Commands:

```bash
cd /root/workspace/ai-tutor/apps/backend
python3 -m py_compile app/ai/sanitize.py app/ai/service.py app/v2/exercises.py
.venv/bin/pytest tests/test_ai_output_contract.py tests/test_pilot_secure_exercises_v2.py tests/test_subjects.py -q

cd /root/workspace/ai-tutor/apps/frontend
npm run typecheck
npm run test:e2e:mvp
```

Prod smoke:

```bash
ssh -i /root/.ssh/id_ed25519_kirill_ai root@192.168.1.86 \
  'curl -sk -w "\nHTTP=%{http_code}\n" https://localhost/ready; cat /opt/ai-tutor/.mvp-rescue-commit'
```

---

### Stage 2 — P1 Expansion MVP

**Goal:** Expand reliable coverage from 15 P0 topics to P1 topics without weakening P0.

#### Stage 2 Scope

P1 topics:

- Виды треугольников
- Понятие множества
- Дробные выражения
- Прямая и обратная пропорциональные зависимости
- Масштаб
- Симметрия
- Положительные и отрицательные числа
- Противоположные числа
- Модуль числа
- Сравнение положительных и отрицательных чисел
- Сложение отрицательных чисел
- Сложение чисел с разными знаками
- Вычитание рациональных чисел
- Умножение рациональных чисел
- Деление рациональных чисел

#### Stage 2 Workstreams

##### 2.1 P1 Fallback Bank

For every P1 topic, add deterministic fallback:

- concrete question;
- type `single` where possible;
- 4 options;
- exact answer;
- explanation;
- typical mistakes.

Tests:

- Extend `tests/test_ai_output_contract.py` with `test_generate_exercise_p1_fallback_bank_is_student_ready`.
- Ensure no generic text fallback leaks:
  - `Сформулируй короткий ответ`
  - `AI`
  - `JSON`
  - `резерв`

##### 2.2 P1 Explain Smoke

Use admin smoke to avoid student budget problems.

Check:

- content length > 250;
- no artefacts;
- no sources;
- no raw JSON/LaTeX/reasoning.

##### 2.3 Matrix Update

Update `docs/pilot-topic-matrix.md`:

- P1 `Fallback = OK`
- `Explain QA = Smoke OK`
- `Practice QA = Smoke OK`

#### Stage 2 Exit Criteria

- P0 remains green.
- P1 fallback tests green.
- P1 API smoke green.
- MVP E2E green.

---

### Stage 3 — Citation-Safe RAG Sources

**Goal:** Re-enable sources only when citations are exact and trustworthy.

#### Problem

Earlier source display was misleading:

- duplicate sources;
- sources from wrong topic;
- links to pages containing examples rather than the explanation actually used.

Current mitigation: sources hidden.

#### Required Design

A source can be shown only if all are true:

1. `chunk.metadata.topic_id == current_topic.id`.
2. The displayed explanation includes claims supported by the chunk.
3. The page range is precise enough for a student/parent to verify.
4. Duplicate `(material_title, part, page_number)` entries are deduped.
5. Source label is human-readable:
   - textbook name;
   - part;
   - printed page;
   - optional short quote/snippet.

#### Implementation Plan

1. Add metadata fields if missing:
   - `part`
   - `printed_page`
   - `topic_id`
   - `topic_name`
   - `page_range`
2. Build `source_candidate` model in backend.
3. Add strict filter in `AIService._build_rag_context`.
4. Add a `citation_confidence` flag.
5. UI only shows source when `citation_confidence == verified`.
6. Tests:
   - wrong topic source hidden;
   - duplicate source deduped;
   - verified source shown;
   - unverified source hidden.

Exit criterion: source box can return without undermining trust.

---

### Stage 4 — Teacher Content Workflow

**Goal:** Stop editing production curriculum/RAG by hand; give adult/teacher controlled content operations.

#### Required Capabilities

- Upload/source management.
- AI draft generation.
- Teacher approval.
- Publish/unpublish.
- Rebuild RAG for selected subject/topic.
- View what changed before applying.

#### Workstreams

1. **Teacher RBAC hardening**
   - Verify teacher/admin endpoints.
   - Ensure student cannot see drafts.

2. **Material lifecycle**
   - `draft → ai_generated → teacher_approved → published`.
   - Soft delete only.

3. **RAG rebuild UI/CLI**
   - Dry-run mode.
   - Apply mode.
   - Backup before rebuild.
   - Report topics/materials/chunks changed.

4. **Content QA dashboard**
   - Show topics with no chunks.
   - Show topics without fallback.
   - Show topics with failed smoke.

Exit criterion: adding another subject does not require direct SQL/container work.

---

### Stage 5 — Parent / Progress Product

**Goal:** Turn the tutor from a chat/demo into a learning product with measurable progress.

#### Workstreams

1. Parent dashboard:
   - mastery by topic;
   - attempts;
   - correct rate;
   - weak topics;
   - weekly summary.

2. Privacy boundary:
   - parent sees progress, not raw child chat by default.

3. Review scheduling:
   - lightweight spaced repetition;
   - daily review queue;
   - cap per day to avoid overload.

4. Reporting:
   - export weekly summary;
   - teacher/parent notes.

Exit criterion: parent can understand whether the child is improving without reading chat logs.

---

### Stage 6 — Reliability / Operations Hardening

**Goal:** Make production boring and recoverable.

#### Workstreams

1. **Backups**
   - Verify local + offsite backup freshness.
   - Add restore drill schedule.
   - Document RTO/RPO.

2. **Observability**
   - Prometheus `/metrics` already returns 200.
   - Add user-facing health dashboard only for admin.
   - Alert on:
     - 5xx rate;
     - backup stale;
     - DB/Redis down;
     - AI provider failure;
     - disk >80%.

3. **AI budget**
   - Separate student budget from automated smoke budget.
   - Add admin view/reset for test budgets.
   - Prevent E2E from exhausting real student limit.

4. **WS decision**
   - Either remove WS from student path entirely or harden it as separate real-time feature.
   - Current student chat uses HTTP and should stay that way for pilot.

5. **Warnings cleanup**
   - `pytest-asyncio` fixture loop warning.
   - `datetime.utcnow` deprecation.
   - coroutine warning around embeddings if still present.

Exit criterion: failures are detected, explainable, and recoverable without manual archaeology.

---

### Stage 7 — Multi-Subject Expansion

**Goal:** Add more subjects without repeating the math rescue manually.

Preconditions:

- Teacher content workflow exists.
- RAG rebuild is safe/dry-runnable.
- Topic matrix workflow is standard.
- Source discipline is solved or sources remain hidden.

For each new subject:

1. Import real curriculum.
2. Upload source materials.
3. Build topic-scoped RAG.
4. Create P0/P1 topic matrix.
5. Add fallback bank for pilot subset.
6. Run smoke.
7. Manual walkthrough.

Exit criterion: a new subject can reach P0 pilot readiness in days, not weeks.

---

## 5. Immediate Next Actions

### Next 24 Hours

1. User completes manual walkthrough for topics `187`, `188`, `189`, `196`, `225`.
2. Record findings in `docs/pilot-topic-matrix.md`.
3. Fix only blockers found in manual QA.
4. Keep P0 smoke green.

### Next 2–3 Days

1. Convert manual notes into repeatable browser/API tests where useful.
2. Add `docs/pilot-walkthrough-notes.md` if more than 3 issues are found.
3. Stabilize E2E budget isolation.
4. Run one full P0 walkthrough session without code changes.

### Next Week

1. Expand fallback bank to P1 topics.
2. Run P1 explain/practice smoke.
3. Decide whether to build citation-safe source display or keep sources hidden through pilot.
4. Start teacher workflow design only after P0/P1 are stable.

---

## 6. Definition of “Next MVP Ready”

The next MVP is ready when:

- P0 manual walkthrough has no blockers.
- P0 matrix has `Manual OK` for at least 5 topics.
- P0 smoke remains green.
- `npm run test:e2e:mvp` passes.
- Backend targeted suite passes.
- Production `/ready` is 200/ready.
- No student-facing technical artefacts are visible.
- No misleading sources are visible.
- No noisy recovery/debug banners appear in the lesson flow.

---

## 7. Files to Treat as Current Source of Truth

| File | Role |
|---|---|
| `docs/PILOT_PLAN.md` | Current short-term pilot acceptance and workflow. |
| `docs/pilot-topic-matrix.md` | Per-topic readiness state. |
| `docs/GLOBAL_DEVELOPMENT_PLAN.md` | This global multi-level development plan. |
| `apps/backend/app/ai/service.py` | AI orchestration, fallback bank, topic drift guard. |
| `apps/backend/app/ai/sanitize.py` | Student-facing output normalization. |
| `apps/frontend/app/topics/[id]/page.tsx` | Main student lesson UX. |
| `apps/frontend/e2e/mvp-student-flow.spec.ts` | MVP browser regression. |

Older roadmap files remain useful background, but this file should be treated as the current high-level plan after the MVP rescue work.
