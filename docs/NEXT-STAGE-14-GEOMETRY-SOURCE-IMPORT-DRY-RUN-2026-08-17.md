# Next Stage 14 — Geometry Source Import Dry Run — 2026-08-17

## Decision

Geometry import is **not production-ready**, but the local dry-run path is now proven.

The dry run produced an auditable manifest for all `13` Geometry route topics without downloading source files into the repo, writing database rows, creating RAG chunks, or mutating production.

## Scope

Stage 14 was allowed to run only if approved Geometry sources existed. Stage 12 approved:

- Illustrative Mathematics Geometry as the primary source.
- Euclid’s Elements Redux as conditional secondary support for a few definition/proof gaps.

## Files Added

- `apps/backend/scripts/geometry_source_import_dry_run.py`
- `apps/backend/tests/test_geometry_source_import_dry_run.py`

## Dry-Run Design

The script builds a local JSON manifest with:

- topic id;
- route order;
- route focus;
- source key/title/URL;
- source section/unit;
- license;
- attribution string;
- decision (`approved_for_dry_run` or `conditional_secondary`);
- `diagram_review_required` flag;
- import notes;
- explicit flags proving no production/DB/RAG mutation.

This is intentionally a manifest generator, not an importer.

## Dry-Run Result

Command:

```text
cd /root/workspace/ai-tutor/apps/backend
python3 -m scripts.geometry_source_import_dry_run --out /tmp/ai-tutor-geometry-source-dry-run.json
```

Output:

```json
{
  "ok": true,
  "out": "/tmp/ai-tutor-geometry-source-dry-run.json",
  "topic_count": 13,
  "source_counts": {
    "im_geometry": 9,
    "euclid_redux": 4
  },
  "requires_diagram_review": true
}
```

Manifest safety flags:

```json
{
  "production_mutation": false,
  "db_import": false,
  "rag_chunk_creation": false,
  "requires_diagram_review": true
}
```

First mapping example:

```json
{
  "topic_id": 53,
  "topic_focus": "прямая, отрезок, луч, угол",
  "source_key": "im_geometry",
  "source_section": "Unit 1 Constructions and Rigid Transformations",
  "license": "CC BY 4.0"
}
```

Last mapping example:

```json
{
  "topic_id": 65,
  "topic_focus": "неравенство треугольника",
  "source_key": "euclid_redux",
  "source_section": "Triangle inequality / classical propositions",
  "license": "CC BY-SA"
}
```

## Coverage Finding

The approved Geometry source set can cover all 13 route topics at manifest level, but diagrams are the major remaining risk:

| Source | Topics Mapped | Role |
|---|---:|---|
| IM Geometry | 9 | Primary source for constructions, congruence, circles, coordinate/parallel-line-adjacent coverage. |
| Euclid’s Elements Redux | 4 | Conditional secondary support for adjacent/vertical angles, triangle parts, exterior angle, triangle inequality. |

Every mapped Geometry topic has `diagram_review_required=true`. This is intentional because Geometry RAG quality depends on diagrams, not just extracted text.

## Tests

```text
cd /root/workspace/ai-tutor/apps/backend
.venv/bin/pytest tests/test_geometry_source_import_dry_run.py -q
4 passed, 3 warnings
```

Test assertions cover:

- all 13 Geometry route topics mapped exactly once;
- no production mutation / DB import / RAG chunk creation;
- dry run requires diagram review;
- only policy-screened sources (`im_geometry`, `euclid_redux`);
- no CK-12 or `ND` sources;
- every row has source section, attribution, and import notes;
- IM Geometry remains the primary source.

## Production Impact

None.

- No source files downloaded into the repo.
- No source materials imported into DB/RAG.
- No production deploy.
- No production data mutation.
- No Nightscout or external medical systems touched.
- Geometry remains `preview`.

## Next Gate

Before any real Geometry import:

1. Fetch exact IM Geometry lesson pages locally.
2. Validate text and diagram extraction separately.
3. Decide whether diagram-heavy chunks should be imported, summarized manually, or deferred.
4. Confirm attribution and image-license handling for every selected lesson.
5. Use Euclid Redux only after page-level license/share-alike/readability review.
6. Keep all work local/staging until topic coverage and extraction quality are verified.

## Done Criteria

- Local import dry-run path proven: complete.
- Topic coverage count produced: complete (`13/13` manifest mappings).
- No production mutation without backup/offsite: complete (no production mutation occurred).
- Geometry remains preview: complete.
- Commit: pending at report creation.
