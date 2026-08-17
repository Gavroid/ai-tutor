# Next Stage 10 — Source Acquisition Policy And License Gate — 2026-08-17

## Decision

No Algebra or Geometry source may be imported into AI-Tutor until it passes this policy gate. The gate is fail-closed: unclear rights, unclear provenance, authentication-only access, `NoDerivatives`, or explicit AI/RAG/LLM ingestion restrictions block import.

This stage intentionally imports **zero** materials. Algebra (`19` route topics) and Geometry (`13` route topics) remain `preview` until future stages prove source/RAG coverage.

## Why This Gate Exists

Creative Commons licenses are standardized permissions for reuse, but the license variant matters. CC BY allows distribution, remixing, adaptation, and commercial use with attribution; CC BY-SA adds a same/compatible-license requirement for adaptations; CC BY-ND allows only unadapted redistribution; CC BY-NC and CC BY-NC-SA restrict reuse to non-commercial purposes; CC BY-NC-ND permits only unadapted non-commercial sharing with attribution.[1]

AI-Tutor needs more than “can view this page.” A source candidate must permit topic-scoped storage, excerpting, retrieval, citation, student-facing summaries, and adapted practice/explanation content. `ND` terms therefore fail the import gate because topic mapping, chunking, summarization, and generated explanations are derivative/adaptive uses.[1]

Open educational providers may add AI-specific restrictions even when textbook content is otherwise Creative Commons licensed. For example, the OpenStax page reviewed here says the book uses CC BY-NC-SA and can be non-commercially distributed/remixed with attribution and share-alike, but it also states that the book may not be used to train or otherwise be ingested into LLMs or generative AI offerings without OpenStax permission.[2] That means an OpenStax-style candidate is not automatically safe for AI-Tutor RAG import; the AI-ingestion terms must be checked per source.[2]

Khan Academy is useful for links and human study, but its terms reviewed here limit Licensed Educational Content to personal, non-commercial use, define several fee/ad-supported uses as outside non-commercial use, and require attribution/free-availability notices for embedded/distinct offerings.[3][4] Therefore Khan material is link-only by default unless a future legal/permission review explicitly approves the exact use.

## Source Acceptance Criteria

A candidate source must pass **all** of these checks before import:

| Gate | Pass | Fail |
|---|---|---|
| License clarity | License is explicit on the source page or in downloadable metadata. | License missing, contradictory, buried in unverifiable mirror text, or “all rights reserved.” |
| Provenance | Official publisher, author, institution, government, OER repository, or primary project page. | Random mirror, scraped PDF, Telegram/cloud repost, unclear scan, or unattributed derivative. |
| Adaptation rights | Public domain, CC0, CC BY, or compatible license that allows adaptation/chunking/summarization. | `ND`, “no modification,” “personal use only,” or any terms that prohibit derivative/adaptive use. |
| Commercial/NC fit | Commercial use allowed, or non-commercial terms are compatible with the actual AI-Tutor pilot/deployment model. | Monetized/paid/tutor-product use is planned but source is NC-only, or terms define the current use as commercial. |
| AI/RAG permission | No explicit restriction on LLM/generative AI ingestion, retrieval, embedding, or machine processing; or written permission exists. | Any “no LLM training,” “no AI ingestion,” “no automated extraction,” “no scraping,” or equivalent restriction unless written permission exists. |
| Attribution | Required attribution can be stored and shown in source metadata/citation UI. | Attribution requirements cannot be met in the product or require endorsement/confusing branding. |
| Topic coverage | Candidate maps to at least one route topic with page/section anchors and grade fit. | Broad resource cannot be mapped to Algebra/Geometry route topics. |
| Retrievability | Stable URL/PDF/API is accessible without private login, secrets, CAPTCHAs, or fragile session cookies. | Requires private account, manual browser-only export, or violates robots/terms to fetch. |
| Extraction quality | Text/diagrams can be extracted and validated with page/section references. | Scanned/diagram-heavy resource fails OCR/layout validation and cannot support reliable citations. |
| Student safety | Content is age-appropriate, educational, and does not introduce unsafe or irrelevant material. | Adult/off-topic/advertising-heavy content, unmoderated comments, or misleading examples. |

## License Tiers

### Tier A — Import-Eligible By Default

Use only after provenance, topic mapping, and extraction checks pass:

- Public Domain / government-public-domain where applicable.
- CC0.
- CC BY 4.0 or equivalent, with attribution metadata stored.
- CC BY-SA 4.0 only if downstream derivatives can comply with share-alike obligations.

### Tier B — Conditional / Legal Review Required

Do not import automatically:

- CC BY-NC or CC BY-NC-SA: allowed only if the current and planned deployment is genuinely non-commercial under the source’s own definition, and if attribution/share-alike can be honored.[1]
- Provider-specific OER terms such as OpenStax: require checking the exact book/page for AI/RAG/LLM restrictions before import.[2]
- Khan Academy or similar platform content: link-only by default; import only with explicit permission for the exact product use.[3][4]

### Tier C — Reject

Reject without further analysis unless written permission is obtained:

- CC BY-ND / CC BY-NC-ND.
- “All rights reserved.”
- Unclear scans/mirrors.
- Sources that prohibit scraping, indexing, embeddings, RAG, LLM ingestion, or generative AI use.
- Sources that require private login or credentials.
- Sources whose attribution/branding rules would imply endorsement.

## Candidate Intake Checklist

Future Stage 11–12 source reports must record this table for every candidate:

| Field | Required Value |
|---|---|
| Candidate name | Human-readable source title. |
| URL | Canonical primary URL, not mirror. |
| Publisher / owner | Institution, author, or organization. |
| Subject fit | Algebra, Geometry, or both. |
| Topic coverage | Route topic ids/names covered. |
| Grade fit | Why it matches grade 7 / middle-school level. |
| License text | Exact license label and URL/section where found. |
| AI/RAG terms | Explicit pass/fail note for AI ingestion, embeddings, RAG, LLM, scraping, automated extraction. |
| Attribution requirement | Exact attribution string or required fields. |
| Access method | Web, PDF, API, repository download. |
| Extraction quality | Text/table/diagram extraction notes. |
| Decision | `approved_for_dry_run`, `link_only`, `needs_permission`, or `rejected`. |
| Reason | Short evidence-backed explanation. |

## Import Rules

1. Never import directly into production during candidate search.
2. Dry-run locally/staging first after policy approval.
3. Store source metadata with license, URL, attribution, retrieval date, and topic mapping.
4. Keep raw source, extracted text, and chunk metadata auditable.
5. Map every chunk to `subject_id`, `topic_id`, topic name, section, source URL/file, and page/section anchor.
6. Do not mark Algebra/Geometry as `mvp_ready` until route, source/RAG, and practice coverage are all verified.
7. If a source later changes terms or becomes unavailable, freeze new imports and mark affected chunks for review.
8. Student-facing source boxes stay hidden or conservative unless citations point to trustworthy, topic-relevant chunks.

## Re-Evaluation Of Known Candidate Types

| Candidate Type | Decision | Reason |
|---|---|---|
| Random textbook PDFs/scans from mirrors | `rejected` | Provenance/license unclear; likely copyrighted. |
| Khan Academy pages/videos/exercises | `link_only` | Non-commercial and distinct-offering constraints require caution; no import without explicit permission.[3][4] |
| OpenStax-style CC BY-NC-SA textbooks | `needs_permission` or `conditional` | CC terms may permit non-commercial adaptation, but AI/LLM ingestion restrictions must be checked for each book/page.[2] |
| CC BY/CC0 OER repositories with stable downloads | `approved_for_dry_run` if topic/extraction checks pass | License permits adaptation and attribution can be stored.[1] |
| CC BY-ND / CC BY-NC-ND resources | `rejected` | No-derivatives conflicts with chunking, summarization, adaptation, and generated explanations.[1] |

## Verification

- Checklist has explicit pass/fail criteria.
- Algebra/Geometry route scopes are known from local route plans: Algebra `19` topics, Geometry `13` topics.
- No source files were imported.
- No production data was mutated.
- No Nightscout or external medical system was touched.

## Done Criteria

- Source acceptance criteria: complete.
- Import checklist: complete.
- Previous candidate classes re-evaluated: complete.
- No questionable material imported: complete.
- Algebra/Geometry remain preview: complete.
- Commit: pending at report creation.

## Sources

[1] Creative Commons license types — https://creativecommons.org/share-your-work/cclicenses
[2] OpenStax textbook licensing example — https://openstax.org/books/anatomy-and-physiology-2e/pages/preface
[3] Khan Academy Terms of Service — https://www.khanacademy.org/about/docs/khan-academy-terms-of-service
[4] Khan Academy materials usage help — https://support.khanacademy.org/hc/en-us/articles/202262954-Can-I-use-Khan-Academy-s-videos-name-materials-links-in-my-project
