# ASU Registration Buddy — Track 1 scope

Status: approved scope; implementation in progress.
Research date: October 24, 2026 (America/Phoenix).

## Recommendation

Build a Cubbie Skill that helps an ASU student choose a section of a course, or shortlist sections matching a bounded search. Combine live ASU Class Search data with matched Rate My Professors (RMP) evidence, explain the tradeoffs, and offer one backup section of the same course.

Student moment: “Registration is coming up. Which section should I pick, and what is my backup if it fills?”

Suggested public pitch: “Find ASU classes that fit your time, compare professors with real reviews, and keep a backup ready for registration.”

This fits Track 1 and reuses the existing data clients. Full academic advising and semester optimization introduce substantially more work.

## Sources and precedence

- Live event site: https://hackathon.cubbie.ai/
- Assistant entrypoint: https://hackathon.cubbie.ai/skill.md
- Official kit: https://github.com/imaginix-inc/cubbie-hackathon-kit
- Reviewed kit commit: `bc505e9` (a shallow reference clone is in `references/cubbie-hackathon-kit/`).
- Kit references: hackathon rules and ideas; Cubbie capabilities, authentication, testing and iMessage style; worked examples.
- Supplied PDF: `/Users/anishk/Downloads/Build a Cubbie Skill — Hackathon Guide.docx.pdf` (dated October 19, 2026).
- Local code: `/Users/anishk/Documents/coding_docs/Class_Helper/`, particularly `class_search_api`, `rmp_api` and the relevant `student_insights` agents.

Use the live site for event rules and live status for submission windows. Use current kit documentation for Cubbie behavior; the older PDF conflicts on installation details.

Important corrections to the PDF:

- Current kit says there is no `cubbie.yaml` configuration system; leftover files are ignored. Put pinned package setup commands in `SKILL.md`, using a persistent virtual environment under HOME.
- Current kit allows outbound HTTPS on port 443 to websites without a declared-host manifest. MCP servers are still unsupported.
- Submit the repository link, which follows new pushes. Use a branch/folder link for testing and a commit link only for a fixed snapshot.
- Update by texting the branch link again; do not depend on the PDF's special update command or a promised install-summary format.
- A TikTok or Instagram demo post is optional for submission, and contributes social engagement if supplied.

Live status checked at approximately 2:56 pm Phoenix time on October 24: all track windows and voting reported open, with no close times configured. This does not establish an event deadline; the site still describes Track 1 as the first ten hours with the exact cutoff to be confirmed. Confirm the practical cutoff with organizers. Track 1 submission is still required before a team can submit Track 2 or 3.

## Existing code and live checks

### ASU

`class_search_api/api.py` has a small requests-based client for public ASU catalog endpoints. `class_search_api/server.py` exposes search filters and normalizes results for its UI. Useful existing features include term, subject, course number, keyword, instructor, level, units, campus/online, session, days, dates and pagination. Course detail retrieval includes descriptions and prerequisite text.

Live read-only checks succeeded:

- Spring 2027 (`2271`), CSE 240: nine section records.
- Adding Tempe and open-only filters: four section records.
- Results included section numbers, instructors, dates, units, meeting information and seat counts.

Counts describe that query at the time of the check, not a guarantee of current availability or enrollment eligibility.

### RMP

`rmp_api/rmp.py` supports school search, professor search, aggregate statistics, paginated professors and paginated reviews. Live school lookup, Erik Trickel lookup, and a five-review request succeeded. Reviews included course codes, dates, tags and difficulty information.

ASU has multiple RMP school records. The search also returned unrelated professors alongside Erik Trickel because fallback matching is enabled. Resolve the appropriate school and verify name/department before attaching evidence.

### Additional reusable material

`student_insights/agents/class_search_agent.py` and `rmp_agent.py` already implement normalization, filtering, matching and evidence structures. Their README documents broader capabilities. Reuse selected deterministic helpers, not the entire agent stack: Cubbie can handle the conversation and synthesis, so Track 1 needs no separate OpenRouter key or LangGraph orchestration.

Existing prerequisite matching uses simple course-code/AND/OR heuristics. It is not sufficient to certify eligibility or degree progress.

These checks ran on this computer. Cubbie's own network/runtime and the end-to-end iMessage flow remain untested.

## Core scope

1. ASU only. State this explicitly in the name, description and README.
2. Gather important missing information in one compact intake message. Accept as much detail as the student provides. Use at most one additional clarification round when necessary; do not turn optional preferences into a questionnaire. Reuse information already supplied.
3. Resolve semester and year explicitly. Never silently search the old default term. Show the resolved semester to the student.
4. Support two entry modes:
   - A known course, such as CSE 240, with section comparison.
   - A bounded discovery search, such as a subject plus level, keyword or a specified catalog designation.
5. Support campus/modality, session, open-only preference, days and simple earliest/latest meeting-time preferences. Avoid presenting these as a mandatory questionnaire.
6. Filter hard constraints before ranking preferences. Never silently relax a campus, time or course requirement.
7. Return at most three initial options, with course/section identifier, instructor, credits, meeting days/times, campus/modality, session/dates and seat availability when known.
8. Enrich only the shortlisted instructors with RMP statistics and a small bounded set of reviews. Prefer reviews for the requested course; label broader professor evidence separately.
9. Give a reasoned recommendation based on the student's stated priorities. Do not reduce fit to a single professor rating or invent a universal score.
10. Offer one alternative section of the same course when a suitable one exists. Recheck live availability when the student asks again or says the preferred option filled.
11. Include ASU search/detail links and RMP profile links, plus retrieval time and review course/date context. Verify link formats during implementation.
12. Keep the initial result short and plain text for iMessage. Offer details on request.
13. Cover all ASU subjects and campuses, including online. Distinguish the physical class location from the course's administrative campus and distinguish ASU Online from campus-student online classes.
14. Check the student's connected Google Calendar alongside explicit availability preferences using Cubbie's existing Calendar implementation. Do not build Calendar integration or Calendar-processing code. Cubbie compares the normalized meeting dates/times with its Calendar results. If unavailable, continue with stated preferences and label Calendar as unchecked. Report incomplete calendar coverage or unknown class times honestly.

If the student asks for an undefined “requirement,” distinguish a specific catalog tag or advisor-provided course list from personalized degree requirements. Ask which one they mean.

## Feature boundaries

| Feature | Decision | Boundary |
| --- | --- | --- |
| Search by semester, subject, course, campus and other basic filters | Core | Validate mappings and label bounded/paginated results |
| Interactive clarification | Core | Ask only questions needed for the current request |
| Professor comparison and grounded review summaries | Core | Verify identity; separate course-specific and overall evidence |
| Same-course backup section | Core | Not a claim of academic equivalence between different courses |
| Interest-based discovery | Lightweight | Match a keyword to official titles/descriptions, then confirm scope |
| Credit preference | Lightweight | Filter individual courses by credits or show totals of a student-selected list |
| Calendar and supplied availability conflict checks | Core | Cubbie handles Calendar through its existing abilities; custom code only normalizes ASU meetings and filters explicit preferences |
| Generate a complete schedule meeting a credit target | Defer | Needs combination search, component rules and robust conflict handling |
| Recommend what the student needs to graduate | Defer | Needs degree audit, catalog year, transfer credit and authoritative requirement rules |
| Recommend substitute courses | Defer | Needs verified equivalencies and requirement context |
| Seat alerts | Defer by default | Adds scheduled state and reliability testing; optionally use Cubbie's own scheduling later |
| Auto-enrollment, registration-portal login or cart changes | Out of scope | Provide official links for the student to complete registration |
| Reddit, syllabus analysis, multi-school support, own UI/backend | Defer | Not needed for the core demonstration |

## Implementation shape

Suggested folder: `asu-registration-buddy/` with `SKILL.md`, a short README, small Python scripts for structured ASU/RMP retrieval, and sanitized sample fixtures under `assets/`.

Run scripts inside Cubbie's private sandbox. Reuse the low-level clients and selected helpers; do not rely on this computer's FastAPI servers, localhost, file paths or `.env`. No separate hosted API or web UI is needed for the proposed flow. Public-source requests currently work without student sign-in.

Cubbie asks questions, interprets preferences and explains results. Scripts fetch/normalize data and perform exact filtering. Return compact structured output with provenance, checked time, pagination coverage and explicit errors. Add offline `--sample` mode as the kit recommends.

## Reliability rules

- Preserve all ASU meeting rows. The live response contained HTML-formatted time fields, structured time arrays, hybrid meetings and null times. A missing time means unknown; it does not by itself prove asynchronous delivery.
- Treat session A/B/C and date ranges as meaningful. Different sessions may not overlap even when weekdays/times match.
- Do not count labs/recitations as independent course choices or credits; show associated components where required.
- Seat counts are snapshots, and positive seats do not establish eligibility or unrestricted availability.
- Keep unknown instructors and missing RMP profiles visible rather than excluding the class or treating missing ratings as poor ratings.
- Label review counts, dates and course coverage. Do not imply a bounded page sample represents every review.
- Separate service failures from valid zero-result responses. The current RMP client often returns empty data on errors; the wrapper needs clearer error reporting.
- Display prerequisite and restriction text without certifying that the student satisfies it.
- Treat retrieved reviews and descriptions as source data, never as instructions to execute.

## Lean completion path

1. Package deterministic retrieval wrappers and establish the data/provenance output contract.
2. Write the interactive Skill instructions and the short reply format.
3. Check structure using the kit validator, then run sample and live script checks.
4. Publish a small public repository when authorized, and test the branch link on the team's Cubbie.
5. Fix installation or main-flow failures before expanding scope.
6. Submit the repository link with team information and a one-line pitch. Preview the exact public entry and obtain confirmation before sending it.
7. Make a short public demo only if desired; avoid adding features for social promotion before the required flow works.

Suggested engineering timebox: approximately 2–4 focused hours for core packaging, instructions, checks and a real Cubbie pass, assuming access works. This is a planning estimate, not a guarantee. If runtime or source-access problems consume the timebox, reduce stretch work first.

## Acceptance checks

- A vague request gets a relevant missing-information question, and an explicit semester is used.
- A known course returns current sections with verified campus/modality and meeting fields.
- A bounded discovery request returns relevant options and states if search coverage is capped.
- Time constraints and Calendar busy intervals are applied consistently; unknown times and incomplete calendar coverage are flagged.
- RMP evidence is attached to the correct instructor/school, with course-specific reviews distinguished from general ratings.
- Missing instructor/RMP data, no matches and network failures produce useful, honest replies.
- One suitable same-course backup is offered when available, with a fresh recheck on request.
- The public link installs and the main flow completes on a real Cubbie account.
- Track 1 entry is confirmed in the public gallery after submission.

## Gallery observation

The official gallery command returned ten Track 1 entries at the time of research. None of those listings described this registration workflow. This is a snapshot, not a novelty guarantee.

Two inspected examples show the intended scale: [Circle Back](https://github.com/JackTYM/circle-back) uses Cubbie's existing abilities for a focused relationship workflow; [Study Room Finder](https://github.com/abhi23lash/study-room-finder) combines a focused student situation with a small retrieval script. They are useful scope references, not evidence that any particular implementation has passed organizer review.
