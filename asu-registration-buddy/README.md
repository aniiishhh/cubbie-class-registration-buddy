# ClassCue

Registration research in a Cubbie text conversation: find ASU courses or sections, filter by time/campus/credits, compare matched professor reviews, check fit through Cubbie's existing Calendar abilities, and keep a same-course backup ready.

Supports known course codes and discovery from a subject or interest, across all ASU campuses and ASU Online. Cubbie batches missing essentials into one or two clarification rounds. No new Calendar integration, hosted backend, separate LLM key or registration login is needed.

## Install on Cubbie

Text this link to Cubbie and approve installation:

```text
https://github.com/aniiishhh/cubbie-class-registration-buddy/tree/main/asu-registration-buddy
```

Cubbie reads [`SKILL.md`](SKILL.md) and runs its pinned Setup commands. Start a new message to try it. Text the same branch/folder link again after a pushed update.

Try:

- “Compare CSE 240 sections for Spring 2027. Tempe campus student, after 10, no Fridays.”
- “Find a three-credit upper-division CSE elective related to artificial intelligence.”
- “What if that section fills up?”

Missing essentials are grouped into a short message. Optional preferences do not become an interview. Calendar access uses Cubbie's existing connection; if unavailable, the workflow continues with stated availability and marks Calendar unchecked.

If ASU denies requests from Cubbie's sandbox with HTTP 403, ClassCue can use `--cached` without any browser handoff. The bundled, timestamped export covers the complete returned Spring 2027 semester: 20,316 section records across 297 ASU subjects and all returned campus/online locations. RMP and Calendar can continue live when available. Cached catalog data does not verify current seats or unchanged instructor assignments. Other semesters are not silently treated as empty. See [`references/commands.md`](references/commands.md) for provenance and refresh instructions.

## Local quick check

Samples work with Python 3.10+ without network access or installed third-party packages:

```bash
python3 scripts/registration.py search --sample --subject CSE --course-number 240
python3 scripts/registration.py professor --sample --course "CSE 240"
```

Real catalog snapshot lookup, also without network or third-party packages:

```bash
python3 scripts/registration.py search --cached --term "Spring 2027" --subject CSE --course-number 575
```

Samples are entirely fictional and cannot demonstrate live availability. For live retrieval, install `requirements.txt` in a virtual environment; Cubbie's persistent Setup commands are in `SKILL.md`. Commands and output contracts are in [`references/commands.md`](references/commands.md).

## Boundaries and data

Seat counts are snapshots, not enrollment guarantees. Verify prerequisites, reserved seats and required lab/recitation components on ASU. RMP evidence is anecdotal and may be incomplete, stale or for another course; it is labeled by scope. Missing time data stays unknown. Cubbie checks Calendar without sharing Calendar data with the retrieval scripts or public sources.

There is no full-semester optimizer, degree audit, automatic enrollment, cart modification or seat-monitoring service. Only an explicitly requested search cache of public catalog data is written, privately under HOME in the Cubbie workflow. No passwords or student API keys are needed. Live requests send course/search filters to ASU and instructor/course lookup information to RMP; do not send student identity or private Calendar details.

The source clients are adapted from the participant's existing Class_Helper ASU Class Search and Rate My Professors clients; matching, errors, pagination and output handling have been tightened for a standalone Skill. The public catalog snapshot contains only ASU catalog records and source metadata. [`references/testing.md`](references/testing.md) contains the real-account checklist.
