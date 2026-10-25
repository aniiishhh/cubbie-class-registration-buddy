# ClassCue

Your ASU registration research, in a Cubbie conversation. Search classes, discover electives, compare professor feedback, check schedule fit, and find a same-course backup.

## Install

Send this folder link to Cubbie and approve installation:

```text
https://github.com/aniiishhh/cubbie-class-registration-buddy/tree/main/asu-registration-buddy
```

Then try:

> Compare CSE 575 and CSE 572 for Spring 2027. Tempe campus student, after noon. Check my Calendar and compare what students say about the listed professors.

Or start with an interest rather than a course code. Cubbie asks for missing essentials together and uses its existing Calendar connection when available.

The display name is **ClassCue**; `asu-registration-buddy` remains the installation identifier. Resend the same link to refresh an older installation.

## Inside this Skill

- [SKILL.md](SKILL.md): setup, query interpretation, comparison workflow, and response guidance.
- [Command reference](references/commands.md): ASU queries, RMP review pagination, data modes, and output fields.
- [Acceptance checks](references/testing.md): offline and real Cubbie checks.
- `scripts/`: small JSON CLI and public-source clients.
- `assets/`: public catalog data with provenance, plus clearly fictional test fixtures.

For the feature overview and workflow diagram, see the [project README](https://github.com/aniiishhh/cubbie-class-registration-buddy#readme).

## Local smoke check

Python 3.10+ can run the fictional fixtures without network access or extra packages:

```bash
python3 scripts/registration.py search --sample --subject CSE --course-number 240
python3 scripts/registration.py professor --sample --course "CSE 240"
```

Live retrieval needs `requests==2.32.5`; Cubbie's persistent environment setup is in `SKILL.md`. Samples do not verify real classes or professor ratings.

No student registration credentials or new Calendar integration are needed. Source timestamps, review coverage, and unknown meeting details remain explicit; enrollment eligibility still needs ASU verification.
