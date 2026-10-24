# ASU Registration Buddy

A Cubbie Skill for finding ASU classes, comparing sections with grounded Rate My Professors evidence, checking Calendar availability, and keeping a same-course backup ready.

The installable folder is [`asu-registration-buddy/`](asu-registration-buddy/). It is self-contained: no local web server, separate LLM key or student registration login.

Text this link to Cubbie, approve installation, then send your registration request in a new message:

```text
https://github.com/aniiishhh/cubbie-class-registration-buddy/tree/main/asu-registration-buddy
```

Try: “Compare CSE 240 sections for Spring 2027. I'm a Tempe campus student, after 10, no Fridays.” Or ask for classes by subject/interest without a course code.

For the hackathon submission, use the [repository link](https://github.com/aniiishhh/cubbie-class-registration-buddy).

See [`docs/track-1-scope.md`](docs/track-1-scope.md) for the agreed scope and research. The official hackathon kit is a local, ignored reference clone in `references/cubbie-hackathon-kit/`; it is not part of the published Skill.

Track 1 progress: scope agreed; Skill written; local checks passed; public repository and install link verified; real Cubbie installation/Calendar test and hackathon submission pending.

Local verification:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r asu-registration-buddy/requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

Samples also run with ordinary Python, without installed third-party packages:

```bash
python3 asu-registration-buddy/scripts/registration.py search --sample --subject CSE --course-number 240
```

See [`docs/validation.md`](docs/validation.md) for verified behavior and remaining checks, and [`asu-registration-buddy/references/testing.md`](asu-registration-buddy/references/testing.md) for the real Cubbie checklist.
