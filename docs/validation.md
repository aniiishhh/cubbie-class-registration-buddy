# Implementation validation — October 24, 2026

## Completed locally

- Installable folder: `asu-registration-buddy/`, with standard Skill frontmatter, grouped intake, public-source retrieval scripts, fictional offline fixtures, command references and a real-account checklist.
- All ASU subjects and teaching locations can be queried. Both exact-course comparison and bounded subject/interest discovery are supported.
- Calendar is handled exclusively by Cubbie's existing connected abilities through Skill instructions. No Calendar client, OAuth setup, Calendar-processing code or backend was added. Calendar data is not sent to retrieval scripts or public data sources.
- Intake gathers missing essentials in one message, permits free-form detail, and allows at most one additional grouped clarification round. Unverified RMP identities do not cause further intake interrogation.
- Pinned `requests==2.32.5` installed successfully in a fresh project virtual environment. Offline samples also ran with `python3 -S`, with third-party site packages disabled.
- 48 deterministic automated tests passed. They cover physical vs administrative campus, ASU Online distinctions, secondary/unknown meeting rows, weekday/time bounds, semester validation, credit/tag filters, primary components, conservative RMP identity matching, course-specific vs general evidence, pagination coverage, source errors, private cache files and valid bounded JSON output.
- The official kit validator passed without structural/metadata warnings after committing the final source changes.
- Git was initialized on `main`, and completed portions were committed incrementally. The imported kit clone, virtual environment, temporary live results and Python caches are ignored.

## Live read-only checks

These are snapshots, not current guarantees of seats or enrollment eligibility:

| Check | Observed result |
| --- | --- |
| Spring 2027, CSE 240, unrestricted | Nine section records in the initial research check |
| Spring 2027, CSE 240, campus student, Tempe, open only, after 10 | Four matching sections; multiple meeting rows retained and unresolved hybrid rows flagged |
| Spring 2027, CSE 240, ASU Online | Three matching sections |
| Spring 2027, BIO 181, Polytechnic | One primary course section in the bounded check; linked components remain subject to official verification |
| Spring 2027, upper-division CSE, artificial intelligence, three credits, campus student | CSE 471, Introduction to Artificial Intelligence; missing instructor and reserved-seat flag preserved |
| Course details for CSE 240 | Description and listed prerequisite/restriction text returned |
| Subject lookup for “biology” | Five matching subject codes/names returned |
| Erik Trickel, ASU, CSE 240 RMP lookup | Matched profile, overall statistics, dated course-specific reviews; bounded review coverage disclosed |
| Saved search paging | Later section returned without a new network request; original retrieval timestamp retained |

An important live finding was corrected: ASU silently ignores a singular `keyword` HTTP parameter. The CLI now maps `--keyword` to the verified plural `keywords` parameter. A regression test protects this behavior. Before the correction, the same request returned unrelated CSE courses; afterward it returned the relevant AI offering.

The generated ASU course-search link returned HTTP 200. The canonical RMP profile URL is constructed from the returned legacy professor ID; a plain automated page request received HTTP 403 even while the public GraphQL retrieval succeeded. Do not describe automated profile-page viewing as verified. The student can follow the source link, and browser access must respect the site's access controls.

## Not yet verified

- Installation and pinned package setup inside the actual Cubbie sandbox.
- Trigger selection and concise replies in a real iMessage conversation.
- Cubbie's use of its existing Calendar implementation over the full section date range, including recurrences, time zones, free/busy status, incomplete coverage and disconnected-account fallback.
- A real same-course backup exchange after a seat recheck.
- A public repository install link, pushed-commit verification, and hackathon submission/gallery confirmation.

Local tests validate the data layer, not Cubbie's private abilities. These remaining checks require the public install link and the team's Cubbie account. Use the numbered checklist in `asu-registration-buddy/references/testing.md`.

## Proposed publishing package

Publish this repository with the Skill folder, project README, tests and scope/validation notes. The official reference kit, `.venv`, `.env`, Python caches and `tmp/` live-check files are excluded by `.gitignore`. No student Calendar data or student credentials are included.

Once publishing is authorized, create or select the public GitHub repository, push `main`, run the kit's public-link checker, and text the resulting branch/folder link to Cubbie for the real-account test. Submit the repository link only after reviewing the public entry and obtaining the required confirmation.
