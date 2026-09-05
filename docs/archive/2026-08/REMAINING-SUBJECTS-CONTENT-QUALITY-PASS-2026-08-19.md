# Remaining Subjects Content Quality Pass — 2026-08-19

## Scope

This stage improved the MVP-safe internal content for the nine non-math subjects after all subjects had already reached mechanical `mvp_ready`.

The previous remaining-subject fallback answers were too generic. This stage added quality gates and regenerated project-owned notes/fallbacks with subject-specific learning actions.

## Subjects Covered

```text
rus, lit, phys, inf, hist, soc, geo, bio, eng
```

Total production scope:

```text
151 topics
151 learning materials
151 RAG chunks
151 fallback-practice entries
```

## Quality Gates Added

`apps/backend/tests/test_remaining_subjects_internal_source_manifest.py` now checks:

- fallback answers are not one generic template;
- each subject has subject-specific language/action anchors;
- source notes contain no student-facing artifacts such as `<think>`, `JSON`, `correct_answer`, provider/parser terms, or table fence markers.

Initial RED:

```text
AssertionError: assert 1 >= 9
# all fallback answers were identical
```

GREEN:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_remaining_subjects_internal_source_manifest.py -q
5 passed, 3 warnings
```

Broader regression:

```text
PYTHONPATH=apps/backend apps/backend/.venv/bin/pytest \
  apps/backend/tests/test_remaining_subjects_internal_source_manifest.py \
  apps/backend/tests/test_remaining_subjects_production_import.py \
  apps/backend/tests/test_subjects.py \
  apps/backend/tests/test_rag_metadata_audit.py -q
26 passed, 3 warnings
```

## Content Changes

`apps/backend/scripts/remaining_subjects_internal_source_manifest.py` now uses per-subject guidance:

- Russian: orthography, morphology, syntax, punctuation rule checking.
- Literature: genre, character, artistic detail, conflict, author position.
- Physics: phenomenon, quantity, unit, experiment, cause-effect relation.
- Informatics: data, algorithm, coding, device, program.
- History: period, participants, causes, events, consequences.
- Social Studies: concept, real-life example, fact vs evaluation.
- Geography: map object, process, Earth system, place relationship.
- Biology: organism/system/function/environment trait.
- English: meaning, grammar form, short phrase use.

## Staging-Shaped Rehearsal

```text
manifest topic_count=151
staging import material_count=151
staging import chunk_count=151
metadata_audit bad_rows=0
rows_written=302
```

## Production Update

Fresh backup/offsite before mutation:

```text
RUN_BACKUP_START=2026-08-19T17:52:38+00:00
OFFSITE OK: hash verified manifest-20260819T175238Z.md5 (de614ef386b71ba775eca81e57a5fbe2)
OFFSITE OK: 129 uploaded, 0 deleted, 217 total on SMB
```

Production reimport:

```text
remaining_materials_after=151
remaining_chunks_after=151
remaining_source_topic_count_after=151
fallback_topics_updated=151
```

## Final Verification

Production readiness:

```text
all_subjects_ready 12
READY_HTTP=200
HEALTH_HTTP=200
```

Student smoke:

```text
BASE_URL=https://192.168.1.86 npx playwright test e2e/pilot.spec.ts:94 --project=chromium --reporter=list
1 passed
```

## Decision

All 12 subjects remain production `mvp_ready`. The nine non-math subjects now have safer, subject-specific MVP internal content instead of one generic fallback/template.

This still does not mean textbook-grade depth for every non-math subject; it closes the MVP content-quality pass for safe route/source/practice readiness.
