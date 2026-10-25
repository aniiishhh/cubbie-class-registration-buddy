# Command reference

Run from the Skill folder. Examples use `python`; in Cubbie, use `~/.local/share/venvs/asu-registration-buddy/bin/python` after Setup in `SKILL.md`.

## ASU section search

```bash
python scripts/registration.py search --cached --term "Spring 2027" --subject CSE --course-number 572 --level 5 --population campus --campus TEMPE --limit 3 --save ~/.config/asu-registration-buddy/cse572.json
```

For discovery, omit the course number and use a subject, keyword, or catalog designation. Separate several requested course codes into individual exact queries with different saved filenames.

| Flag | Meaning |
| --- | --- |
| `--term "Spring 2027"` | Required semester/year, or ASU code `2271`. Spring=1, Summer=4, Fall=7 in `2YYs` encoding. |
| `--subject CSE --course-number 572` | Exact course; subject alone explores its courses. |
| `--keyword "machine learning"` | Concise interest. Live maps to ASU's plural `keywords`; bundled lookup matches titles only. |
| `--population campus` | Campus students, including iCourses; excludes ASU Online program offerings. |
| `--population asu-online` | ASU Online program offerings. |
| `--population all` | Default: unrestricted exploration. Label eligibility differences. |
| `--campus TEMPE` | Teaching location. Also WEST, POLY, DTPHX, MESACITYCR, or other returned location codes. Administrative campus may differ. |
| `--modality in-person` | Also hybrid, online, sync, any. Online does not establish asynchronous delivery. |
| `--session A` | Exact session code; inspect returned dates, including for full-semester C. |
| `--level 5` | 500–599. Also 1–9 for hundreds; lower=100–299, upper=300–499, graduate=500–999. |
| `--min-credits 3 --max-credits 3` | Individual-course bounds. A variable-credit range must fit entirely inside them. |
| `--designation gold:HUAD` | Exact catalog designation; gold, maroon, and other are separate systems. |
| `--instructor "Full Name"` | Filter by ASU instructor; verify identities in returned results. |
| `--days MON,TUE,WED,THU,SAT,SUN` | All allowed days, e.g. no Friday. Known meetings outside these days are excluded. |
| `--after 12:00 --before 18:00` | Earliest start/latest end in America/Phoenix, for every known meeting row. |
| `--open-only` | Positive known seats, open enrollment status, active section. Historical in bundled mode; never proves reserved-seat eligibility. |
| `--limit 3` | Display 1–5 records, possibly fewer to fit the output budget. |
| `--max-pages 3` | Live retrieval cap: 1–5 pages. Read `coverage.complete`. |
| `--save PATH` | Save all filtered fetched candidates privately for paging. Use one path per query. |

Explicit filters are checked locally even when also sent upstream. Unknown meetings remain flagged. Discovery initially displays distinct courses; exact searches display sections. Neither solves required component enrollment rules.

## Source modes and freshness

- **Default for Spring 2027 in Cubbie:** `--cached`. Reads the complete bundled public ASU export without network access or third-party packages.
- **Live:** omit `--cached` for direct ASU queries when accessible, including other terms or an explicit fresh-seat request.
- **Fictional fixtures:** `--sample`. Offline only, clearly labeled, and cannot write saved searches or real review corpora.

The Spring 2027 export originally contains 20,316 records across 297 subjects and all returned campus/online locations. Its source time is **2026-10-24 23:39:17 UTC** (4:39 pm Phoenix). `assets/catalog_manifest.json` records provenance; trust runtime metadata if refreshed.

For bundled results, use `source_checked_at`, `cache_age_hours`, `cache_stale`, `snapshot_scope`, and coverage fields. Never use command execution time as a new source check. `checked_at` is null, and `live_availability_verified` is false. Out-of-scope terms return `cache_miss`, not zero sections. `no_results` within scope describes that dataset and filters only. No automatic refresh runs.

For live results, `checked_at` records retrieval time. Coverage can be incomplete. Seats remain subject to change and restrictions.

Give the student one brief source/freshness note per comparison. Reuse that context in follow-ups; repeat only when the source changes, becomes stale, or current availability is material. Do not repeat the same warning per option or per review batch.

An HTTP 403 is an access denial, not a zero-result response. `cf-mitigated: challenge` identifies Cloudflare verification. Stop blocked requests; do not probe repeatedly or bypass challenges. Use the covered export for planning, and continue independent RMP/Calendar work. Only safe response-header metadata is retained; cookies, authorization, and raw response bodies are omitted. A browser handoff is not required.

## Page saved candidates

```bash
python scripts/registration.py page --file ~/.config/asu-registration-buddy/cse572.json --offset 3 --limit 3
```

Use the actual returned `next_offset` for the next call; output sizing may reduce the page. This reads the saved ordering without network and preserves original source times. An exact query for a course found through discovery can expose its alternative sections.

## Valid official ASU links

Copy `asu_url` from normalized results. For valid numeric section/course IDs, it includes the official `#detailsOpen=CLASSNBR-CRSEID` fragment. `asu_search_url` opens that course's results without expanding a section. Without valid IDs, the helper falls back to course results.

Current ASU routes use long parameter names, such as:

https://catalog.apps.asu.edu/catalog/classes/classlist?campusOrOnlineSelection=A&honors=F&promod=F&searchType=all&subject=CSE&catalogNbr=575&term=2271

`campusOrOnlineSelection=O` selects ASU Online. Never rebuild links using legacy `t`, `s`, `n`, `hon`, or `e` keys. Preserve literal `&`, not `\&` or `&amp;`. In iMessage send raw URLs on separate lines. These are official listing links, not enrollment actions.

## Subjects and course detail (live)

```bash
python scripts/registration.py subjects --term "Spring 2027" --query biology
python scripts/registration.py detail --term "Spring 2027" --subject CSE --course-number 572 --course-id RETURNED_COURSE_ID
```

Use actual `course_id` from search results, not a guessed identifier. `subjects` returns up to 40 matches; narrow the query if necessary. `detail` returns descriptions and listed prerequisites/restrictions. Neither has a bundled-data mode. If live access is blocked, do not repeatedly invoke these. Catalog requirements do not certify student-specific eligibility.

## Professor lookup and full review corpus

```bash
python scripts/registration.py professor --name "Erik Trickel" --course "CSE 240" --campus TEMPE --save-reviews ~/.config/asu-registration-buddy/erik-trickel-reviews.json
```

Names must come from actual ASU section results. The helper searches ASU RMP directory entries, rechecks affiliation, and requires a single exact name match. Check department compatibility before attaching ratings. `needs_confirmation` means no verified rating; never choose a different person because their ratings look better. `--school-id` and `--teacher-id`, when needed, must come from returned candidates. Campus orders identity searches; it does not certify RMP affiliation.

| Professor flag | Purpose |
| --- | --- |
| `--max-pages 2` | Identity-search pages per ASU directory entry; 1–3. |
| `--review-pages 250` | Separate review pagination cap; 1–500, 20 reviews per page, with about 60 seconds of retrieval budget. Stops earlier on exhaustion, stalled pagination, or source failure. |
| `--max-reviews 4` | Overview excerpts only; 1–6. Does not limit the full saved corpus. |
| `--save-reviews PATH` | Save full unique fetched comments privately; returns `reviews_file`. |

Overview output:

- `statistics`: overall professor metrics, not course-specific scores.
- `course_reviews` / `general_reviews`: a few varied overview excerpts, including positive/critical examples when available. These are not sufficient for the complete analysis.
- `review_coverage`: page count, stop reason, reported total, elapsed time, and pagination completeness.
- `reviews_fetched`: unique fetched records; a profile total may differ.
- `corpus_summary`: date span, course/tag counts, and score distributions across the fetched corpus. These are counts, not automated sentiment claims.
- `reviews_status`: `ok`, `partial`, or `unavailable`; partial retrieval retains usable reviews with explicit limits.

Read the complete fetched corpus in batches:

```bash
python scripts/registration.py review-page --file ~/.config/asu-registration-buddy/erik-trickel-reviews.json --offset 0 --limit 10
```

Repeat using each response's **actual `next_offset`** until it reaches `total_reviews`. This command reads full comments locally, without network; it may return fewer than requested to stay under the output limit. `checked_at` remains the original retrieval time.

Build notes across every batch: recurring themes, supporting counts, contrary evidence, requested-course vs broader reviews, and recent vs older experiences. Fetching all pages does not prove Cubbie read all comments. If the reading or retrieval stops early, report the actual coverage. Pagination completion establishes exhaustion of available pages at retrieval time, not that RMP exposes every review ever posted.

RMP comments are unverified student opinions. Missing profiles or reviews are not negative evidence. Keep full corpora in private working files, reuse them during the comparison, and remove them when no longer needed. They must not be committed to the public repository.

## Output, storage, and exit codes

Output stays under 7,800 characters. `returned` and `next_offset` reflect records actually emitted. Lists may be shortened with `output_limited: true`; individual records/meeting rows are never silently cut. Overview excerpts are explicitly shortened; saved review comments are full text. If one record cannot fit, exit 5 requests a narrower output or direct inspection of the private file.

| Exit | Meaning |
| --- | --- |
| 0 | Read the status: success, no_results, not_found, or needs_confirmation. |
| 2 | Invalid input or unreadable local file. |
| 3 | Source/API unavailable; no false empty result inferred. |
| 4 | Missing runtime dependency; follow Setup. |
| 5 | Output too large; reduce displayed results/excerpts or read a private file in smaller batches. |
| 6 | Requested term/subject outside bundled snapshot coverage. |

Saved searches and review corpora use mode 600. Public APIs receive only course/search filters or professor lookup information. Calendar details stay with Cubbie. The scripts never enroll, modify carts, send messages, or access Google accounts. Snapshot refresh is a maintainer operation documented in the project CONTRIBUTING guide.
