# Implementation validation — October 24, 2026

## Completed locally

- Installable folder: `asu-registration-buddy/`, with standard Skill frontmatter, grouped intake, public-source retrieval scripts, fictional offline fixtures, command references and a real-account checklist.
- All ASU subjects and teaching locations can be queried. Both exact-course comparison and bounded subject/interest discovery are supported.
- Calendar is handled exclusively by Cubbie's existing connected abilities through Skill instructions. No Calendar client, OAuth setup, Calendar-processing code or backend was added. Calendar data is not sent to retrieval scripts or public data sources.
- Intake gathers missing essentials in one message, permits free-form detail, and allows at most one additional grouped clarification round. Unverified RMP identities do not cause further intake interrogation.
- Pinned `requests==2.32.5` installed successfully in a fresh project virtual environment. Offline samples also ran with `python3 -S`, with third-party site packages disabled.
- 71 deterministic automated tests passed. They cover physical vs administrative campus, ASU Online distinctions, secondary/unknown meeting rows, weekday/time bounds, semester validation, credit/tag filters, primary components, conservative RMP identity matching, course-specific vs general evidence, pagination coverage, source errors, private cache files, valid bounded JSON output, explicit snapshot provenance/coverage/staleness, privacy-safe diagnostics, complete-semester scope, compressed data loading, challenge classification and atomic write failures.
- The official kit validator passed without structural/metadata warnings after committing the final source changes.
- Git was initialized on `main`, and completed portions were committed incrementally. The imported kit clone, virtual environment, temporary live results and Python caches are ignored.
- With explicit user authorization, the repository was published at https://github.com/aniiishhh/cubbie-class-registration-buddy. GitHub reports it PUBLIC with default branch `main`. The official public-link checker passed without problems or notes, and both offline sample commands succeeded from a fresh anonymous clone.

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

The first real Cubbie trial reported HTTP 403 from the ASU live search and no section listings from an alternate web lookup. A later current-version request reported `cf-mitigated: challenge`, Server `cloudflare`, and HTML content: a Cloudflare browser-verification response. The exact risk rule remains unknown, but the immediate denial is identified. This remains a failed direct live-ASU test; local successes do not establish success on Cubbie.

A diagnostic inside Cubbie returned HTTP 200 at 4:04 pm Phoenix using the same ASUClient session through Python `Session.get()`, not a separate web fetch tool. A local comparison confirmed `.get()` and ClassCue's `request_json()` produce identical prepared requests and send options; Requests `.get()` delegates to `.request()`. The isolated success therefore does not establish a separate working transport or explain the later challenge. The same query succeeds locally and returns three matching sections across two courses. Error diagnostics retain only an allowlisted bounded set of response headers, never cookies, credentials or full bodies.

The user confirmed no usable interactive Cubbie browser handoff is available. Recovery no longer requires one. The complete returned Spring 2027 catalog was exported through normal public ASU access at `2026-10-24T23:39:17+00:00`: 20,316 records, 297 subjects, 102 pages, reported complete against the source total. It is stored as an approximately 1.5 MB gzip asset with a small public provenance manifest. This supersedes the initial CSE-only snapshot. It contains real public catalog records, separate from fictional samples, and supports every returned subject/location in that semester without network or extra packages. Other semesters still require a refreshed export or permitted live access.

The reader preserves source time, reports age/staleness/scope, labels current availability unverified, and distinguishes cache misses from covered zero-result searches. Maintainer refresh uses normal paced pagination, refuses incomplete results and writes the data atomically. RMP and Calendar can remain live independently. This is not a proxy, a Cloudflare bypass, an automatic refresh service, or a fix to direct ASU access.

- Installation and pinned package setup inside the actual Cubbie sandbox.
- Trigger selection and concise replies in a real iMessage conversation.
- Cubbie's use of its existing Calendar implementation over the full section date range, including recurrences, time zones, free/busy status, incomplete coverage and disconnected-account fallback.
- A real same-course backup exchange after a seat recheck.
- Hackathon submission/gallery confirmation.

Local tests validate the data layer, not Cubbie's private abilities. Use the verified public install link with the team's Cubbie account and follow the numbered checklist in `asu-registration-buddy/references/testing.md`.

## Published package

The public repository contains the Skill folder, project README, tests and scope/validation notes. The official reference kit, `.venv`, `.env`, Python caches and `tmp/` live-check files are excluded by `.gitignore`. No student Calendar data or student credentials are included.

Text this branch/folder link to Cubbie for the real-account test:

https://github.com/aniiishhh/cubbie-class-registration-buddy/tree/main/asu-registration-buddy

Submit the repository link only after reviewing the public entry and obtaining the required confirmation.
