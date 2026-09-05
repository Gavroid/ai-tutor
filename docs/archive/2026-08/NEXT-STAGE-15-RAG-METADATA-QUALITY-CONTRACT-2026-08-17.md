# Next Stage 15 — RAG Metadata Quality Contract — 2026-08-17

## Decision

Stage 15 is complete. False source/RAG readiness is now automatically detectable through a read-only metadata audit contract.

The contract validates RAG chunk metadata before any Algebra/Geometry source coverage can be trusted. It catches missing topic/source metadata, mismatched `topic_id`, subject-code mismatches, and the critical case where Geometry source material is incorrectly counted as Algebra coverage.

## Files Added

- `apps/backend/scripts/rag_metadata_audit.py`
- `apps/backend/tests/test_rag_metadata_audit.py`

## Contract

Each RAG chunk must provide or align with:

- `topic_id`
- `topic_name`
- `source_title`
- `source_section`, `page_number`, or `page_range`
- `license`
- `attribution`
- subject code alignment between material subject and metadata subject
- material topic id alignment with metadata topic id
- source-title sanity check against expected subject

## What The Audit Detects

Known-bad fixture output proves detection of:

```text
missing:topic_name
missing:license
missing:attribution
missing:source_section_or_page
topic_id_mismatch:metadata=53 material=35
subject_code_mismatch:metadata=geometry expected=algebra
material_metadata_subject_mismatch:metadata=geometry material=algebra
source_subject_mismatch:source_looks_like=geometry expected=algebra
```

This directly satisfies the Stage 15 requirement that a Geometry file cannot count as Algebra source coverage.

## CLI Usage

DB mode:

```text
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/python -m scripts.rag_metadata_audit --subject-code algebra --json
```

Fixture mode, useful for CI and known good/bad examples without requiring live DB settings:

```text
.venv/bin/python -m scripts.rag_metadata_audit \
  --subject-code algebra \
  --input-json /tmp/rag-audit-fixture.json \
  --json
```

Exit semantics:

- `0`: all checked rows are clean.
- `1`: bad rows were detected.

## Fixture Evidence

Fixture run with one good Algebra row and one bad Geometry-as-Algebra row:

```json
{
  "summary": {
    "rows_checked": 2,
    "ok_rows": 1,
    "bad_rows": 1,
    "problems": {
      "material_metadata_subject_mismatch:metadata=geometry material=algebra": 1,
      "missing:attribution": 1,
      "missing:license": 1,
      "missing:source_section_or_page": 1,
      "missing:topic_name": 1,
      "source_subject_mismatch:source_looks_like=geometry expected=algebra": 1,
      "subject_code_mismatch:metadata=geometry expected=algebra": 1,
      "topic_id_mismatch:metadata=53 material=35": 1
    }
  }
}
```

## Tests

Focused test:

```text
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest tests/test_rag_metadata_audit.py -q
6 passed, 3 warnings
```

Broader backend slice:

```text
.venv/bin/pytest \
  tests/test_rag_metadata_audit.py \
  tests/test_algebra_source_import_dry_run.py \
  tests/test_geometry_source_import_dry_run.py \
  tests/test_health.py -q
22 passed, 3 warnings
```

## Production Impact

None.

- No production deploy.
- No production data mutation.
- No DB/RAG write.
- No Nightscout or external medical system touched.
- Algebra and Geometry remain `preview`.

## Next Gate

Stages 16–17 must run this metadata audit after any local or production RAG build. Algebra/Geometry source coverage cannot be considered verified unless:

1. topic coverage counts exist;
2. metadata audit returns `bad_rows=0`;
3. source/title/license/attribution fields are present;
4. subject-code and topic-id alignment are clean;
5. teacher readiness confirms source counts only for the correct subject.

## Done Criteria

- Tests/checks for `topic_id`, `topic_name`, source title, page/section metadata: complete.
- Audit script to detect mismatched subject/material chunks: complete.
- Geometry file cannot count as Algebra source coverage: complete.
- Backend tests and known good/bad script output: complete.
- Commit: pending at report creation.
