# Next Stage 12 — Geometry Source Candidate Search Pass — 2026-08-17

## Decision

Geometry has **one strong dry-run candidate** and several conditional/rejected candidates. No source was imported. Geometry remains `preview` until a later local import dry run proves topic coverage, diagram/text extraction quality, attribution storage, and RAG mapping.

Best candidate for Stage 14 local dry run: **Illustrative Mathematics Geometry course hosted by Kendall Hunt**, because the course page lists Geometry units and states it is licensed under Creative Commons Attribution 4.0.[1]

## Geometry Route Scope

Local `GEOMETRY_TOPIC_PLAN` has `13` topics:

- line, segment, ray, angle;
- segment and angle measurement;
- adjacent/vertical angles;
- perpendicular lines;
- triangle congruence;
- median/bisector/altitude;
- isosceles triangle;
- circle and construction tasks;
- parallel lines;
- triangle angle sum;
- exterior angle;
- triangle inequality.

A candidate must cover these route topics with diagrams and page/section anchors before it can be imported.

## Candidate Register

| Candidate | URL | License / Terms | Route Fit | Decision | Reason |
|---|---|---|---|---|---|
| Illustrative Mathematics Geometry course | `https://im.kendallhunt.com/HS/teachers/2/index.html` | Course page says © 2019 Illustrative Mathematics and licensed under Creative Commons Attribution 4.0; it also warns the IM name/logo are not under the CC license.[1] | Strong route fit for Geometry units: constructions/rigid transformations, congruence, similarity, right triangles, coordinate geometry, circles.[1] | `approved_for_dry_run` | Official course page, clear CC BY 4.0, strong geometry scope. Dry run must handle diagrams carefully and store attribution/trademark restrictions.[1] |
| Illustrative Mathematics first edition terms | `https://illustrativemathematics.org/terms-of-use/` | First edition IM K–12 Math is CC BY 4.0 and allows sharing/adaptation for any purpose including commercially with attribution; v.360 is CC BY-NC.[3] | Confirms the policy basis for using first-edition IM materials. | `supporting_evidence` | Use the course page as primary Geometry source and terms page for license/trademark context.[1][3] |
| Open Textbook Library Geometry and Trigonometry subject page | `https://open.umn.edu/opentextbooks/subjects/geometry-and-trigonometry` | Mixed per-book licenses: examples include CC BY-SA, CC BY-NC-SA, GNU FDL, and CC BY entries.[2] | Includes some geometry titles, but many are college/advanced or trigonometry-focused.[2] | `index_only` | Useful discovery index, not a direct import. Each book needs separate grade, license, diagram extraction, and AI/RAG review.[2] |
| Euclid’s Elements Redux via OTL | Listed on OTL Geometry page | OTL listing says CC BY-SA and describes use for grades 7–12 and undergraduate proof writing.[2] | Partial fit: classical proof/logic geometry may help foundations but not all route topics. | `conditional_secondary` | Potentially useful for proofs/definitions only; share-alike and age/diagram fit must be reviewed before dry run.[2] |
| Elementary College Geometry via OTL | Listed on OTL Geometry page | OTL listing says CC BY-NC-SA.[2] | Introductory plane geometry, but college-oriented and NC/share-alike. | `conditional_low_priority` | License and level are less ideal than IM Geometry. Use only if IM leaves specific gaps and non-commercial terms are acceptable.[2] |
| Wikibooks geometry pages | `https://en.wikibooks.org/wiki/Wikibooks:Copyrights` | Wikibooks text is generally dual licensed under CC BY-SA 4.0 and GFDL unless otherwise noted.[4] | Unknown until page-level review; editable community quality varies. | `needs_quality_review` | Possible fallback for definitions/proofs; requires stability, attribution/share-alike, diagram license, and topic-fit review.[4] |
| CK-12 Geometry / FlexBooks | `https://help.ck12.org/hc/en-us/articles/51042851054235-CK-12-Terms-of-Use` | Terms prohibit using CK-12 materials to build/train AI or ML models and prohibit aggregator-style redistribution through separate services.[5] | Likely good subject fit, but terms fail Stage 10 AI/RAG gate. | `needs_permission` / reject by default | Do not import unless CK-12 gives express written permission for AI-Tutor RAG/import use.[5] |
| Random Geometry PDFs / school mirrors / Big Ideas free access pages | Search results only | License/provenance unclear or publisher-specific all-rights-reserved risk. | Unknown. | `rejected` | Fails Stage 10 provenance/license gate unless a primary license page proves reuse/adaptation/AI-RAG rights. |

## Approved Dry-Run Candidate

### Candidate A — Illustrative Mathematics Geometry

Decision: `approved_for_dry_run`.

Why:

- Officially hosted course page lists Geometry units directly.[1]
- The page states the content is licensed under Creative Commons Attribution 4.0.[1]
- The route fit is strong for current Geometry preview topics: basic geometry, congruence, similarity, coordinate geometry, circles, and triangle reasoning.[1]
- The related IM terms page confirms first edition IM K–12 Math is CC BY 4.0 and permits sharing/adaptation for any purpose including commercially with attribution.[3]

Required Stage 14 checks before import:

1. Map IM Geometry units/lessons to the 13 AI-Tutor `GEOMETRY_TOPIC_PLAN` topic ids.
2. Confirm every selected page belongs to the CC BY 4.0 first-edition course, not v.360 CC BY-NC.
3. Validate diagram extraction separately from text extraction.
4. Store attribution and avoid using IM trademark/logo in product naming.
5. Exclude or separately attribute third-party/public-domain/open images as required by the IM page.[1]
6. Keep dry run local/staging only until topic coverage and extraction are verified.

## Secondary Candidates

### Candidate B — Euclid’s Elements Redux

Decision: `conditional_secondary`.

Why:

- OTL lists it as CC BY-SA and says it is based on Euclid’s Elements for grades 7–12 and undergraduate proof writing.[2]
- Could support foundations/proofs if IM Geometry lacks short definitional chunks.

Risks:

- Share-alike obligations.
- More proof-oriented than current AI-Tutor route.
- Needs page-level review and extraction test.

### Candidate C — Wikibooks Geometry Pages

Decision: `needs_quality_review`.

Why:

- Wikibooks licensing can be compatible in principle under CC BY-SA 4.0/GFDL unless otherwise noted.[4]
- Geometry content quality and diagrams must be reviewed per page.[4]

Use only as a fallback for definitions after IM mapping.

## Coverage Fit Snapshot

| Geometry Route Area | IM Geometry | Euclid’s Elements Redux | Elementary College Geometry | Wikibooks | CK-12 |
|---|---:|---:|---:|---:|---:|
| Basic objects / angles | likely | likely | likely | unknown | blocked |
| Perpendicular / parallel lines | likely | likely | likely | unknown | blocked |
| Congruent triangles | likely | likely | likely | unknown | blocked |
| Triangle centers/parts | likely | partial | likely | unknown | blocked |
| Circles / constructions | likely | partial | partial | unknown | blocked |
| Triangle angle relationships | likely | likely | likely | unknown | blocked |

`likely` means candidate search found plausible source coverage, not verified import coverage. Stage 14 must prove exact mapping and diagram extraction.

## Stage 14 Input

- Use Stage 10 policy gate for every selected page.
- Use IM Geometry as the first dry-run target.
- Treat OTL as discovery only; do not import directly from the index.
- Keep Euclid/Wikibooks as secondary fallback candidates.
- Do not import CK-12 without written permission.
- Reject school mirrors/random PDFs unless a primary license page proves rights.

## Verification

- Every candidate has a decision and evidence.
- No source files were downloaded into the repo.
- No source materials were imported into DB/RAG.
- No production mutation was performed.
- Geometry remains `preview`.

## Done Criteria

- Geometry approved source ready for local dry-run: complete (`Illustrative Mathematics Geometry`).
- Conditional/rejected candidates documented: complete.
- No material imported unless it passed Stage 10 gate: complete.
- Commit: pending at report creation.

## Sources

[1] Illustrative Mathematics Geometry course — https://im.kendallhunt.com/HS/teachers/2/index.html
[2] Open Textbook Library Geometry and Trigonometry subject — https://open.umn.edu/opentextbooks/subjects/geometry-and-trigonometry
[3] Illustrative Mathematics Terms of Use — https://illustrativemathematics.org/terms-of-use
[4] Wikibooks Copyrights — https://en.wikibooks.org/wiki/Wikibooks:Copyrights
[5] CK-12 Terms of Use — https://help.ck12.org/hc/en-us/articles/51042851054235-CK-12-Terms-of-Use
