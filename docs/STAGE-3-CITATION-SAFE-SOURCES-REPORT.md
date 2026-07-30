# Stage 3 Citation-Safe RAG Sources Report

Date: 2026-07-30
Branch: `mvp-rescue`
Production host: `192.168.1.86`

## Result

Stage 3 — **Citation-Safe RAG Sources** is complete for the current MVP surface.

Sources are now shown again, but only when they pass strict verification:

- source belongs to the current `topic_id`;
- source `topic_name` matches the current topic;
- source has textbook `part`;
- source has printed `page_number`;
- source has `citation_confidence = verified`;
- UI displays only a clean label, not raw PDF-extracted snippet text.

## Why This Is Safe

Earlier source display was removed because it could show:

- sources from the wrong topic;
- duplicate rows;
- vague page links;
- noisy raw extracted textbook snippets.

The new Stage 3 implementation prevents those failure modes:

1. Backend filters sources by exact topic metadata.
2. Backend creates verified source labels.
3. Frontend shows only the label.
4. Frontend does not display noisy snippets.

## Implementation Summary

Backend:

- Added `_verified_rag_sources(...)` in `apps/backend/app/ai/service.py`.
- Added `_source_label(...)` helper.
- `AIService._build_rag_context(...)` now searches inside learning materials for the current topic first.
- Explain response now returns verified sources when available.
- If `topic.id` is unavailable in tests, sources safely remain empty.

Frontend:

- Extended source typing in:
  - `apps/frontend/lib/api.ts`
  - `apps/frontend/types/index.ts`
- Updated topic UI to show verified source label.
- Snippets are intentionally not shown to avoid PDF extraction artefacts.

Tests:

- Added `test_verified_rag_sources_require_topic_and_page_metadata`.
- Existing MVP E2E remains green.

## Verification

Local gates:

- Backend targeted: `57 passed`
- Frontend typecheck: passed
- MVP E2E: `2 passed`

Production smoke:

- `/ready`: ready, HTTP 200
- Citation smoke for P0+P1 topics: 30/30 topics returned verified sources.
- Every returned source had:
  - `citation_confidence = verified`
  - matching `topic_id`
  - non-empty `label`
  - `part`
  - `page_number`

## Current MVP Coverage

| Topic Group | Count | Explain QA | Practice QA | Sources |
|---|---:|---|---|---|
| P0 | 15 | Smoke OK | Smoke OK | Verified |
| P1 | 15 | Smoke OK | Smoke OK | Verified |
| P2 | 12 | TODO | TODO | Hidden/TODO |

## Remaining Non-Blocking Work

- Manual QA for P1 topics is still TODO.
- P2 topics remain outside the current MVP scope.
- Snippets can be revisited later after PDF extraction cleanup / OCR normalization.
- Source confidence is metadata-based, not semantic entailment-based. It is safe enough for topic/page citation, but not yet a quote-level citation engine.

## Recommendation

Run manual walkthrough on 5–10 P1 topics next. Keep sources visible and watch specifically for:

- page label feels plausible;
- no noisy source text appears;
- no source from a different topic appears;
- no duplicate source rows.
