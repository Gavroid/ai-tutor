# Next Month 2 Source Expansion Report — 2026-08-17

## Executive Decision

Month 2 source expansion produced honest preview infrastructure and guardrails, but **did not produce verified Algebra or Geometry RAG coverage**.

Final decision:

- Math stays `mvp_ready`.
- Algebra stays `preview`.
- Geometry stays `preview`.
- Do not promote Algebra or Geometry until actual source imports, RAG chunks, metadata audit, and student/teacher smoke pass.

## Current Production Baseline

Checked at `2026-08-17 18:03 MSK`:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
backend/frontend/db/redis/prometheus healthy
grafana/proxy running
```

Production marker remains intentionally unchanged because release marker hygiene is still blocked by the dirty production tree / targeted deploy mode.

## Current Readiness Matrix

Read-only production `/api/v1/subjects` snapshot:

| Subject | Status | Route | Source/RAG | Practice | Topics | Route Topics | Source Topics | Practice Topics |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Math | `mvp_ready` | ✅ | ✅ | ✅ | 42 | 42 | 42 | 42 |
| Algebra | `preview` | ✅ | ❌ | ✅ | 19 | 19 | 0 | 19 |
| Geometry | `preview` | ✅ | ❌ | ✅ | 13 | 13 | 0 | 13 |

Production DB source/RAG count:

```text
algebra|19|0|0
geom|13|0|0
math|42|42|20289
```

## Stage 10–18 Summary

| Stage | Result | Decision Trail |
|---|---|---|
| Stage 10 — Source Acquisition Policy | Created fail-closed license/provenance/AI-RAG gate. | No unclear, `ND`, login-only, or AI-ingestion-prohibited sources may be imported. |
| Stage 11 — Algebra Candidates | Found IM first edition as primary dry-run candidate; Wallace Algebra as secondary support; CK-12 rejected without permission. | Algebra has candidate sources, not import-ready RAG. |
| Stage 12 — Geometry Candidates | Found IM Geometry as primary dry-run candidate; Euclid Redux as conditional secondary; CK-12 rejected without permission. | Geometry has candidate sources, but diagrams require special extraction review. |
| Stage 13 — Algebra Import Dry Run | Added local manifest generator; mapped `19/19` Algebra topics. | Manifest only: `db_import=false`, `rag_chunk_creation=false`, `production_mutation=false`. |
| Stage 14 — Geometry Import Dry Run | Added local manifest generator; mapped `13/13` Geometry topics. | Manifest only; every row has `diagram_review_required=true`. |
| Stage 15 — RAG Metadata Contract | Added audit script and tests for topic/source/license/attribution/subject alignment. | Geometry cannot falsely count as Algebra coverage; known good/bad fixture passes. |
| Stage 16 — Algebra RAG Blocker | Verified production Algebra has `19` topics, `0` materials, `0` chunks. | Algebra remains `preview`, `rag_ready=false`. |
| Stage 17 — Geometry RAG Blocker | Verified production Geometry has `13` topics, `0` materials, `0` chunks. | Geometry remains `preview`, `rag_ready=false`; diagram extraction unresolved. |
| Stage 18 — Promotion Gate | Compared Math/Algebra/Geometry readiness. | Do not promote Algebra or Geometry. |

## What Is Actually Ready

### Ready

- Written source policy gate.
- Algebra candidate list with decisions.
- Geometry candidate list with decisions.
- Local Algebra dry-run manifest path.
- Local Geometry dry-run manifest path.
- RAG metadata audit contract.
- Route/practice coverage for Algebra and Geometry preview mode.

### Not Ready

- Algebra source import.
- Geometry source import.
- Algebra RAG chunks.
- Geometry RAG chunks.
- Diagram extraction and attribution handling for Geometry.
- Any promotion beyond preview for Algebra/Geometry.

## Blockers

### Blocker — Algebra RAG

Algebra has no imported learning materials or RAG chunks in production:

```text
algebra topics=19 materials=0 chunks=0
```

The Stage 13 manifest proves mapping feasibility, not import quality.

### Blocker — Geometry RAG

Geometry has no imported learning materials or RAG chunks in production:

```text
geom topics=13 materials=0 chunks=0
```

Geometry also requires diagram/image extraction review before text chunks can count as reliable RAG.

### Blocker — Production Release Hygiene

Production marker remains `6e698a0` and targeted deploy mode remains active. Broad deploy / marker advancement should wait for release hygiene cleanup.

## Next Operational Focus

1. Build **local-only source fetch/extraction fixtures** for the approved IM Algebra and IM Geometry pages.
2. Create a small local import fixture for 2–3 Algebra topics first.
3. Run `scripts.rag_metadata_audit --subject-code algebra` and require `bad_rows=0`.
4. For Geometry, add a diagram extraction decision: import diagrams, manually summarize them, or defer diagram-heavy topics.
5. Only after local import quality passes, consider targeted production import with backup/offsite.
6. Keep Math pilot operations active and use feedback intake for real supervised Math sessions.

## Verification

Stage reports referenced:

```text
docs/NEXT-STAGE-10-SOURCE-ACQUISITION-POLICY-2026-08-17.md
docs/NEXT-STAGE-11-ALGEBRA-SOURCE-CANDIDATES-2026-08-17.md
docs/NEXT-STAGE-12-GEOMETRY-SOURCE-CANDIDATES-2026-08-17.md
docs/NEXT-STAGE-13-ALGEBRA-SOURCE-IMPORT-DRY-RUN-2026-08-17.md
docs/NEXT-STAGE-14-GEOMETRY-SOURCE-IMPORT-DRY-RUN-2026-08-17.md
docs/NEXT-STAGE-15-RAG-METADATA-QUALITY-CONTRACT-2026-08-17.md
docs/NEXT-STAGE-16-ALGEBRA-RAG-BUILD-OR-BLOCKER-2026-08-17.md
docs/NEXT-STAGE-17-GEOMETRY-RAG-BUILD-OR-BLOCKER-2026-08-17.md
docs/NEXT-STAGE-18-MULTI-SUBJECT-PROMOTION-DECISION-2026-08-17.md
```

Latest relevant commits:

```text
9011d08 docs: close next stage 18 promotion decision
05e9046 docs: close next stage 17 geometry rag blocker
929fa1f docs: close next stage 16 algebra rag blocker
28998a0 feat: close next stage 15 rag metadata contract
5bcbfc8 feat: close next stage 14 geometry import dry run
381110e feat: close next stage 13 algebra import dry run
6d6d78e docs: close next stage 12 geometry source candidates
9274a8a docs: close next stage 11 algebra source candidates
6636eba docs: close next stage 10 source policy gate
```

Production health referenced:

```text
marker=6e698a0
READY_HTTP=200
HEALTH_HTTP=200
backend/frontend/db/redis/prometheus healthy
grafana/proxy running
```

No production mutation was performed for Stage 19.

## Done Criteria

- Stages 10–18 consolidated: complete.
- Readiness matrix updated: complete.
- Next-month operational focus defined: complete.
- Actual docs, counts, commits, and prod health referenced: complete.
- Month 2 honest source/RAG status and decision trail: complete.
- Commit: pending at report creation.
