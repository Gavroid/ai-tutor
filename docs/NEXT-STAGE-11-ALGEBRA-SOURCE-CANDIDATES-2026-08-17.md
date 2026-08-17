# Next Stage 11 — Algebra Source Candidate Search Pass — 2026-08-17

## Decision

Algebra has **one strong dry-run candidate** and several blocked/conditional candidates. No source was imported. Algebra remains `preview` until a later local import dry run proves topic coverage, extraction quality, attribution storage, and RAG mapping.

Best candidate for Stage 13 local dry run: **Illustrative Mathematics first edition IM K–12 Math / Algebra 1 path**, because IM states that its first edition curriculum is licensed under CC BY 4.0, allows sharing/adaptation for any purpose including commercial use with attribution, and is a primary official source.[1]

## Algebra Route Scope

Local `ALGEBRA_TOPIC_PLAN` has `19` topics:

- numeric expressions;
- variables and expressions;
- algebraic transformations;
- linear equations;
- functions and linear functions;
- direct proportionality;
- powers and monomials;
- polynomials and special products;
- systems of linear equations.

A source candidate must map to these route topics before it can be imported.

## Candidate Register

| Candidate | URL | License / Terms | Route Fit | Decision | Reason |
|---|---|---|---|---|---|
| Illustrative Mathematics first edition IM K–12 Math | `https://illustrativemathematics.org/terms-of-use/` / first edition hosted at Kendall Hunt | CC BY 4.0 for first edition IM K–12 Math; share/adapt for any purpose including commercially with attribution and change notice.[1] | Strong conceptual fit for Algebra 1 and middle/high-school transition; needs exact topic mapping. | `approved_for_dry_run` | Official source, clear permissive license, no `ND`, no login for student content noted; dry run still must store attribution and avoid IM trademark misuse.[1] |
| Illustrative Mathematics v.360 | `https://illustrativemathematics.org/terms-of-use/` / AccessIM | CC BY-NC 4.0 for v.360 curriculum; share/adapt for non-commercial purposes only.[1] | Likely good grade/topic fit. | `conditional` | License is clear, but NC terms require deployment/business-model review; use first edition CC BY path first.[1] |
| Tyler Wallace — Beginning and Intermediate Algebra | `http://www.wallace.ccfaculty.org/book/book.html` | CC BY 3.0 Unported; page provides full textbook and section PDFs, plus modifiable files.[2] | Covers many Algebra topics: linear equations, graphing, systems, exponents, polynomials, factoring, functions.[2] | `approved_for_dry_run_secondary` | Clear attribution license and downloadable/modifiable sections; grade may be too broad/college-prep, so use only for mapped support chunks after reading section quality.[2] |
| Open Textbook Library Algebra subject page | `https://open.umn.edu/opentextbooks/subjects/algebra` | Mixed per-book licenses: CC BY-SA, CC BY-NC-SA, CC BY-NC-ND, CC BY, GNU FDL, etc.[3] | Mostly undergraduate/college algebra/linear algebra, not grade 7 Algebra route. | `index_only` | Useful discovery index, but not itself an import source; each listed book must pass license + grade + AI/RAG gate individually.[3] |
| OpenStax Algebra and Trigonometry via OTL listing | Listed on Open Textbook Library as `Algebra and Trigonometry 2e` | OTL listing says CC BY for this algebra/trigonometry title.[3] | Too broad/advanced for current grade-7 Algebra route without careful section filtering. | `needs_page_level_review` | Potentially useful as a later candidate, but Stage 10 already found OpenStax pages can include AI/LLM ingestion restrictions; must verify exact book page before import.[3] |
| Wikibooks algebra/math content | `https://en.wikibooks.org/wiki/Wikibooks:Copyrights` | Wikibooks text is generally dual licensed under CC BY-SA 4.0 and GFDL unless otherwise noted.[4] | Route fit unknown and quality varies by page/book. | `needs_quality_review` | License may be compatible if attribution/share-alike are handled, but editable community content needs page-level stability, quality, and topic mapping review.[4] |
| CK-12 Algebra / FlexBooks | `https://help.ck12.org/hc/en-us/articles/51042851054235-CK-12-Terms-of-Use` | CK-12 terms restrict use to educational purposes and explicitly prohibit use to build/train AI or machine-learning algorithms/models; aggregators distributing materials through their own services are also prohibited.[5] | Content fit likely strong, but terms fail AI/RAG gate. | `needs_permission` / reject by default | Do not import into AI-Tutor RAG unless CK-12 gives express written permission for this exact use.[5] |

## Approved Dry-Run Candidate

### Candidate A — Illustrative Mathematics First Edition

Decision: `approved_for_dry_run`.

Why:

- Official source and terms are from Illustrative Mathematics itself.[1]
- First edition IM K–12 Math is explicitly described as OER and CC BY 4.0.[1]
- Terms state users may share and adapt for any purpose, including commercially, with appropriate attribution, license hyperlink, and change indication.[1]
- Grade/topic fit is likely strong enough to justify local mapping work, especially for Algebra 1 adjacent topics.

Required Stage 13 checks before import:

1. Locate exact Algebra 1 / grade-band pages and downloadable assets.
2. Confirm each selected page still uses first edition CC BY 4.0, not v.360 CC BY-NC.
3. Build mapping from IM lesson/unit to AI-Tutor `ALGEBRA_TOPIC_PLAN` topic ids.
4. Validate extraction into clean text with section anchors.
5. Store attribution exactly as required and avoid implying IM endorsement or using restricted trademarks as product naming.
6. Keep all work local/staging until coverage is proven.

## Secondary Candidate

### Candidate B — Tyler Wallace Beginning and Intermediate Algebra

Decision: `approved_for_dry_run_secondary`.

Why:

- The source page gives a CC BY 3.0 Unported license for the algebra textbook.[2]
- It provides a full textbook, section PDFs, practice problems, student solutions, and modifiable files.[2]
- It covers several relevant route areas, including one-step/two-step/general linear equations, slope/lines, systems, exponents, polynomials, factoring, quadratic equations, and functions.[2]

Risks:

- It is not explicitly grade-7 aligned.
- Some topics are beyond current route scope.
- The source is hosted on an individual faculty site over HTTP; provenance is still direct to author but should be snapshotted during dry run.

Use rule: import only small, topic-mapped sections after manual review.

## Rejected Or Conditional Candidates

### CK-12

Decision: `needs_permission`; reject by default.

CK-12 terms prohibit using the platform or curriculum materials to build or train artificial intelligence or machine-learning algorithms/models, and also prohibit aggregator-style redistribution through a separate service.[5] This conflicts with AI-Tutor RAG/import use unless written permission is obtained.[5]

### Open Textbook Library Index

Decision: `index_only`.

The Algebra subject page is useful for discovery, but it lists mixed licenses and mostly college-level materials.[3] It is not itself a source to import; every listed book needs separate review against Stage 10.

### Wikibooks

Decision: `needs_quality_review`.

Wikibooks licensing may be compatible in principle because most text is CC BY-SA 4.0/GFDL unless otherwise noted.[4] However, editable community content requires page-level quality, stability, attribution, and topic-fit checks before any dry run.[4]

## Coverage Fit Snapshot

| Algebra Route Area | IM First Edition | Tyler Wallace | CK-12 | Wikibooks / OTL |
|---|---:|---:|---:|---:|
| Expressions / variables | likely | yes | blocked | unknown |
| Linear equations | likely | yes | blocked | unknown |
| Functions / linear functions | likely | yes | blocked | unknown |
| Powers / monomials | likely | yes | blocked | unknown |
| Polynomials / special products | likely | yes | blocked | unknown |
| Systems of equations | likely | yes | blocked | unknown |

`likely` means candidate search found a plausible source, not verified import coverage. Stage 13 must prove exact mapping.

## Stage 12/13 Input

- Use Stage 10 policy gate for every future source.
- Use IM first edition as the first Algebra dry-run target.
- Keep Tyler Wallace as a fallback/secondary source for specific algebra skills if IM mapping leaves gaps.
- Do not import CK-12 without written permission.
- Do not use OTL/Wikibooks as direct imports without page-level review.

## Verification

- Every candidate has a decision and evidence.
- No source files were downloaded into the repo.
- No source materials were imported into DB/RAG.
- No production mutation was performed.
- Algebra remains `preview`.

## Done Criteria

- Algebra approved source ready for local dry-run: complete (`Illustrative Mathematics first edition`).
- Conditional/rejected candidates documented: complete.
- No material imported unless it passed Stage 10 gate: complete.
- Commit: pending at report creation.

## Sources

[1] Illustrative Mathematics Terms of Use — https://illustrativemathematics.org/terms-of-use
[2] Beginning and Intermediate Algebra by Tyler Wallace — http://www.wallace.ccfaculty.org/book/book.html
[3] Open Textbook Library Algebra subject — https://open.umn.edu/opentextbooks/subjects/algebra
[4] Wikibooks Copyrights — https://en.wikibooks.org/wiki/Wikibooks:Copyrights
[5] CK-12 Terms of Use — https://help.ck12.org/hc/en-us/articles/51042851054235-CK-12-Terms-of-Use
