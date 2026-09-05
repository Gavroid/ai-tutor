# Next Stage 13 — Algebra Source Import Dry Run — 2026-08-17

## Decision

Algebra import is **not production-ready**, but the local dry-run path is now proven.

The dry run produced an auditable manifest for all `19` Algebra route topics without downloading source files into the repo, writing database rows, creating RAG chunks, or mutating production.

## Scope

Stage 13 was allowed to run only if approved Algebra sources existed. Stage 11 approved:

- Illustrative Mathematics first edition Algebra 1 as the primary source.
- Tyler Wallace `Beginning and Intermediate Algebra` as secondary support for topics IM Algebra 1 index does not expose directly.

## Files Added

- `apps/backend/scripts/algebra_source_import_dry_run.py`
- `apps/backend/tests/test_algebra_source_import_dry_run.py`

## Dry-Run Design

The script builds a local JSON manifest with:

- topic id;
- route order;
- route focus;
- source key/title/URL;
- source section/unit;
- license;
- attribution string;
- decision (`approved_for_dry_run` or `secondary_support`);
- import notes;
- explicit flags proving no production/DB/RAG mutation.

This is intentionally a manifest generator, not an importer.

## Dry-Run Result

Command:

```text
cd /root/workspace/ai-tutor/apps/backend
python3 -m scripts.algebra_source_import_dry_run --out /tmp/ai-tutor-algebra-source-dry-run.json
```

Output:

```json
{
  "ok": true,
  "out": "/tmp/ai-tutor-algebra-source-dry-run.json",
  "topic_count": 19,
  "source_counts": {
    "wallace_algebra": 12,
    "im_first_edition": 7
  }
}
```

Manifest safety flags:

```json
{
  "production_mutation": false,
  "db_import": false,
  "rag_chunk_creation": false
}
```

First mapping example:

```json
{
  "topic_id": 34,
  "topic_focus": "числовые выражения",
  "source_key": "wallace_algebra",
  "source_section": "0.3 Order of Operations",
  "license": "CC BY 3.0"
}
```

Last mapping example:

```json
{
  "topic_id": 52,
  "topic_focus": "способ сложения",
  "source_key": "im_first_edition",
  "source_section": "Unit 2 Linear Equations, Inequalities, and Systems",
  "license": "CC BY 4.0"
}
```

## Coverage Finding

The approved Algebra source set can cover all 19 route topics at manifest level, but **not with one source alone**:

| Source | Topics Mapped | Role |
|---|---:|---|
| Tyler Wallace Algebra | 12 | Secondary support for numeric expressions, powers, monomials, polynomials, special products. |
| IM Algebra 1 first edition | 7 | Primary source for linear equations, functions, and systems. |

This means the next import stage must remain conservative:

- IM should be imported first for topics it clearly covers.
- Wallace sections should be used only after manual level/readability review.
- No Algebra topic should become `mvp_ready` until page/section extraction and RAG chunk quality are verified.

## Tests

```text
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest tests/test_algebra_source_import_dry_run.py -q
4 passed, 3 warnings
```

Test assertions cover:

- all 19 Algebra route topics mapped exactly once;
- no production mutation / DB import / RAG chunk creation;
- only policy-approved sources (`im_first_edition`, `wallace_algebra`);
- no CK-12, Khan, or `ND` sources;
- every row has URL, source section, attribution, and import notes;
- both primary and secondary source coverage are present.

## Production Impact

None.

- No source files downloaded into the repo.
- No source materials imported into DB/RAG.
- No production deploy.
- No production data mutation.
- No Nightscout or external medical systems touched.
- Algebra remains `preview`.

## Next Gate

Before any real Algebra import:

1. Fetch exact selected source pages/sections locally.
2. Validate text extraction and page/section anchors.
3. Confirm attribution storage format.
4. Create a local import fixture for a small subset first, ideally 2–3 topics.
5. Run RAG chunk quality checks before marking any coverage verified.

## Done Criteria

- Local import dry-run path proven: complete.
- Topic coverage count produced: complete (`19/19` manifest mappings).
- No production mutation without backup/offsite: complete (no production mutation occurred).
- Algebra remains preview: complete.
- Commit: pending at report creation.
