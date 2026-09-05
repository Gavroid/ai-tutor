# AI-Tutor Development Direction Options — 2026-08-18

## Current Baseline

AI-Tutor is ready for a supervised **Math-only** manual pilot wave, but Igor does not currently have time to run pilot sessions.

Production state at last verification:

```text
Branch: mvp-rescue
Marker: 6e698a0
/ready=200
/health=200
Math: mvp_ready, route/source/practice 42/42
Algebra: preview, route/practice 19/19, source/RAG 0/19
Geometry: preview, route/practice 13/13, source/RAG 0/13
```

Main constraint: do not spend weeks polishing based on imagined child feedback. If manual pilot is delayed, development should focus on work that is useful without live pilot feedback: operations, content pipeline, product-grade self-checks, and future expansion foundations.

---

# Option A — Ops / Release Hygiene Track

## Idea

Turn the current targeted-safe production workflow into a clean repeatable release process.

## Build

- Clean production tree/marker workflow.
- Define full release vs targeted hotfix modes.
- Add release checklist command/script.
- Add rollback checklist command/script.
- Verify marker advancement in a non-destructive way.
- Add CI-style local gates summary.

## Why It Matters

Right now production marker is still `6e698a0` because work used targeted deploys. That is safe but not scalable. Before more feature work, release confidence matters.

## Output

- Clean release/rollback runbook.
- Optional `scripts/release_preflight.sh`.
- Optional `scripts/targeted_deploy_manifest.py`.
- Production marker hygiene decision.

## Time

2–5 days.

## Risk

Low if kept read-only/targeted until explicitly deploying.

## Best When

You want infrastructure confidence before touching new learning features.

---

# Option B — Algebra Source/RAG Pipeline Track

## Idea

Promote Algebra from preview foundation toward real readiness by building the source import pipeline, not by faking readiness.

## Build

- Select exact Algebra source set.
- Extract source pages/sections.
- Create provenance metadata per topic.
- Import Algebra learning materials locally first.
- Build RAG chunks with metadata.
- Run `rag_metadata_audit.py`.
- Keep production blocked until coverage is real.

## Why It Matters

Algebra already has route/practice `19/19`, but source/RAG is `0/19`. This is the highest-leverage path if the product should become multi-subject.

## Output

- Real Algebra source ingestion workflow.
- Topic-to-page provenance.
- RAG metadata audit pass/fail.
- Algebra readiness decision.

## Time

1–3 weeks depending on source extraction quality.

## Risk

Medium. Source licensing/provenance can block progress. Bad source import is worse than no import.

## Best When

You want to expand beyond Math and are willing to do content/source work properly.

---

# Option C — Math Autonomous Quality Lab Track

## Idea

Since live pilot feedback is delayed, simulate quality evaluation across all Math topics with automated checks.

## Build

- Batch-generate explanations for representative Math topics using admin/budget-safe mode.
- Score outputs for length, readability, raw JSON, broken math, source support, child-readability.
- Generate deterministic practice variants and check rotation/no-repeat behavior.
- Create a quality dashboard/report per topic.
- Add regression tests for repeated weak patterns.

## Why It Matters

This improves Math without needing a live child session. It is not as good as real feedback, but better than idle waiting.

## Output

- `docs/MATH-AUTONOMOUS-QUALITY-LAB-YYYY-MM-DD.md`.
- Per-topic quality matrix.
- New tests for common defects.
- Improved fallback/explain rules where evidence supports it.

## Time

4–8 days.

## Risk

Medium-low. Risk is overfitting to automated heuristics instead of real child behavior.

## Best When

You want safer Math before live pilot but cannot run manual sessions now.

---

# Option D — Teacher Content Studio Track

## Idea

Make the teacher/admin side strong enough that a human can curate and approve content efficiently later.

## Build

- Improve teacher material list/detail workflow.
- Add bulk QA review surfaces.
- Add diff/history for material status changes.
- Add “why blocked/needs review” summaries.
- Add import preview before save.
- Add audit drill reports for QA transitions.

## Why It Matters

If content quality is the bottleneck, the teacher workflow must be excellent. This also supports future Algebra/Geometry source import.

## Output

- Better teacher QA UI.
- Stronger audit UX.
- Content workflow docs.
- Faster manual content review later.

## Time

1–2 weeks.

## Risk

Medium. Could become UI polishing without actual content progress unless tied to source/import tasks.

## Best When

You expect a teacher/adult reviewer to curate content before child pilot expands.

---

# Option E — Parent Value / Reporting Track

## Idea

Make parent reporting feel genuinely useful even before many child sessions exist.

## Build

- Better empty-state and low-data recommendations.
- Weekly parent summary format.
- “What to do tomorrow” action cards.
- Progress explanation in human language.
- Export/share parent summary PDF/HTML.
- Keep aggregate-only privacy boundary.

## Why It Matters

Parent value can be improved without running many sessions. It also makes the product more convincing for future pilot stakeholders.

## Output

- Parent report v3.
- Weekly summary artifact.
- Better recommendations with low/no data.
- Regression tests for privacy.

## Time

4–7 days.

## Risk

Low-medium. Without real sessions, recommendations may remain generic.

## Best When

You care about family-facing polish and perceived value.

---

# Option F — AI Cost / Reliability Control Plane Track

## Idea

Make AI usage measurable, controllable, and safe before heavier usage.

## Build

- Reset-safe AI usage accounting in DB or Redis snapshots.
- Per-user/per-mode cost estimates.
- Admin budget dashboard.
- Alert thresholds for request/token spikes.
- Graceful degradation tests.
- Provider failover strategy or mock fallback policy.

## Why It Matters

Current AI token baseline is partial because Prometheus counters reset after backend recreate. Before larger usage, cost accounting should be reliable.

## Output

- Durable usage ledger.
- Admin AI cost dashboard.
- Budget alerts.
- Better AI limit UX.

## Time

1–2 weeks.

## Risk

Medium. Needs careful handling to avoid exposing API/provider internals or confusing users.

## Best When

You expect heavier AI usage soon or want cost confidence first.

---

# Option G — Product Demo / Stakeholder Track

## Idea

Instead of deep engineering, package the current Math MVP into a strong demo/story.

## Build

- Update stakeholder deck from latest execution state.
- Create guided demo script.
- Add screenshots/video walkthrough.
- Build “what works / what is preview / what is next” one-pager.
- Create a non-technical roadmap.

## Why It Matters

If nobody can test right now, a crisp demo can help decide whether the project is worth more engineering time.

## Output

- Updated deck.
- Demo script.
- Product one-pager.
- Decision memo.

## Time

2–4 days.

## Risk

Low. Does not improve product internals.

## Best When

You need clarity, motivation, or external buy-in before more coding.

---

# Recommended Direction

## My Recommendation: C → A → B

### 1. Math Autonomous Quality Lab

Do this first because live pilot is delayed but Math is the only pilot-ready subject. It improves the core without pretending to have real feedback.

### 2. Ops / Release Hygiene

Do this next because the marker/release workflow is still known debt. More features on top of dirty release hygiene increases future risk.

### 3. Algebra Source/RAG Pipeline

Do this third if you still want multi-subject expansion. Algebra is closer than Geometry because it has fewer diagram complications.

## Alternative If You Want Product Polish

C → E → G

- improve Math quality;
- make parent reporting more valuable;
- package a strong demo.

## Alternative If You Want Engineering Hardening

A → F → C

- clean release workflow;
- make cost/control reliable;
- then improve Math quality.

## Alternative If You Want Multi-Subject Growth

B → D → Geometry later

- build Algebra source import;
- improve teacher content studio around review/import;
- only then tackle Geometry diagram/source complexity.

---

# Decision Matrix

| Option | User-visible value | Engineering value | Risk | Time | My Priority |
|---|---:|---:|---:|---:|---:|
| A Ops / Release Hygiene | Medium | Very high | Low | 2–5d | 2 |
| B Algebra Source/RAG | High later | High | Medium | 1–3w | 3 |
| C Math Quality Lab | High | High | Medium-low | 4–8d | 1 |
| D Teacher Studio | Medium-high | Medium | Medium | 1–2w | 4 |
| E Parent Reporting | Medium-high | Medium | Low-medium | 4–7d | 5 |
| F AI Cost Control | Medium | High | Medium | 1–2w | 6 |
| G Demo/Stakeholder | Medium | Low | Low | 2–4d | 7 |

---

# Concrete Next Plan If Igor Picks Recommended Path

## Phase 1 — Math Autonomous Quality Lab

1. Build topic sampling list: first/middle/checkpoint/last + weak/complex Math topics.
2. Add script to request explain/practice in admin-safe mode.
3. Add output validators for child readability and safety.
4. Generate report per topic.
5. Patch only repeated concrete defects.
6. Run backend safety tests and student Playwright smoke.
7. Commit with report.

## Phase 2 — Release Hygiene

1. Inspect production tree vs local HEAD.
2. Define clean release marker workflow.
3. Add release preflight command/script.
4. Run dry-run marker advancement check.
5. Update deploy docs.
6. Commit.

## Phase 3 — Algebra Source/RAG

1. Pick approved Algebra source package.
2. Extract exact topic-page mapping.
3. Build local material import dry-run v2 with real extracted snippets.
4. Import locally/staging first.
5. Generate chunks and metadata.
6. Run RAG metadata audit.
7. Decide if any production import is safe.

---

# Decision Needed

Pick one direction:

1. `C → A → B` — quality first, then release hygiene, then Algebra.
2. `A → F → C` — engineering/ops first.
3. `B → D` — multi-subject/source growth first.
4. `C → E → G` — product polish/demo first.
5. Custom mix.
