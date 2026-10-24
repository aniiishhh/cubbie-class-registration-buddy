# ASU Registration Buddy

A Cubbie Skill for finding ASU classes, comparing sections with grounded Rate My Professors evidence, checking Calendar availability, and keeping a same-course backup ready.

The installable folder is [`asu-registration-buddy/`](asu-registration-buddy/). It will be self-contained: no local web server, separate LLM key or student registration login.

See [`docs/track-1-scope.md`](docs/track-1-scope.md) for the agreed scope and research. The official hackathon kit is a local, ignored reference clone in `references/cubbie-hackathon-kit/`; it is not part of the published Skill.

Track 1 progress: scope agreed; Skill written; local checks passed; real Cubbie installation/Calendar test and public submission pending.

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
