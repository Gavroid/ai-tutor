# AI-Tutor Content Quality Baseline

## Summary

- Mode: `content_quality_baseline_local_read_only`
- Production mutation: `False`
- Subjects audited: 12
- Topics audited: 225
- Technical issue count: 0
- Priority counts: `{"P0_fill_coverage": 2, "P1_textbook_grade_upgrade": 6, "P2_depth_upgrade": 4}`
- Production readiness problems: `[]`

## Subject Matrix

| Subject | Topics | Fallbacks | Sources | Source Mode | Technical Issues | Priority | Flags |
|---|---:|---:|---:|---|---:|---|---|
| rus | 13 | 13 | 13 | project_owned_internal_notes | 0 | P2_depth_upgrade | internal_notes_not_textbook_grade, fallbacks_need_subject_language_depth |
| lit | 17 | 17 | 17 | project_owned_internal_notes | 0 | P1_textbook_grade_upgrade | internal_notes_not_textbook_grade, needs_verified_subject_sources |
| math | 42 | 42 | 0 | missing_local_manifest | 0 | P0_fill_coverage | source_manifest_gap, no_local_source_manifest, fallbacks_need_subject_language_depth |
| algebra | 19 | 19 | 0 | missing_local_manifest | 0 | P0_fill_coverage | source_manifest_gap, no_local_source_manifest |
| geom | 13 | 13 | 13 | project_owned_internal_notes | 0 | P2_depth_upgrade | internal_notes_not_textbook_grade, source_notes_shallow |
| phys | 24 | 24 | 24 | project_owned_internal_notes | 0 | P1_textbook_grade_upgrade | internal_notes_not_textbook_grade, needs_verified_subject_sources |
| inf | 21 | 21 | 21 | project_owned_internal_notes | 0 | P2_depth_upgrade | internal_notes_not_textbook_grade |
| hist | 10 | 10 | 10 | project_owned_internal_notes | 0 | P1_textbook_grade_upgrade | internal_notes_not_textbook_grade, needs_verified_subject_sources |
| soc | 15 | 15 | 15 | project_owned_internal_notes | 0 | P2_depth_upgrade | internal_notes_not_textbook_grade |
| geo | 16 | 16 | 16 | project_owned_internal_notes | 0 | P1_textbook_grade_upgrade | internal_notes_not_textbook_grade, needs_verified_subject_sources |
| bio | 19 | 19 | 19 | project_owned_internal_notes | 0 | P1_textbook_grade_upgrade | internal_notes_not_textbook_grade, needs_verified_subject_sources |
| eng | 16 | 16 | 16 | project_owned_internal_notes | 0 | P1_textbook_grade_upgrade | internal_notes_not_textbook_grade, needs_verified_subject_sources |

## Interpretation

- `P0_*` means coverage or technical gates must be fixed before content depth work.
- `P1_textbook_grade_upgrade` means mechanically ready but should receive verified subject sources and richer explanations next.
- `P2_depth_upgrade` means safe MVP internal notes exist but remain shallow compared with textbook-grade coverage.
- This audit is local/read-only; it does not import sources, rebuild RAG, or mutate production data.

