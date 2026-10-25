# Developing ClassCue

The installable package is `asu-registration-buddy/`. Keep its folder and Skill identifier stable; **ClassCue** is the display name. Scripts return small JSON records so Cubbie can do the conversational reasoning and use its existing Calendar integration.

## Local setup and verification

Python 3.10+:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r asu-registration-buddy/requirements.txt
.venv/bin/python -m unittest discover -s tests -v
git diff --check
```

Offline fixture check, without installing packages:

```bash
python3 asu-registration-buddy/scripts/registration.py search --sample --subject CSE --course-number 240
```

Tests cover query/filter behavior, calendar-ready meeting data, identity matching, review pagination and corpus reading, source failures, snapshot provenance, bounded output, and official link generation. They do not call live services or prove the actual Cubbie Calendar flow.

Before publishing, use the official [Cubbie hackathon kit](https://github.com/imaginix-inc/cubbie-hackathon-kit) Skill validator and public-link checker. Follow the [installed acceptance checks](asu-registration-buddy/references/testing.md) on Cubbie after pushing. Keep documentation and helper flags consistent.

## Data and source clients

- `catalog.py`: ASU normalization, filters, meeting preferences, official URLs.
- `sources.py`: public ASU/RMP requests and bounded pagination.
- `professors.py`: cautious identity matching, corpus counts, and evidence grouping.
- `registration.py`: CLI, output limits, private file paging.
- `snapshots.py`: validated, timestamped public catalog exports.

The source clients build on the team's existing Class_Helper APIs. No student credentials are needed. Preserve clear differences between public catalog snapshots, live source checks, and fictional fixtures. Never commit student information, Calendar data, full temporary review corpora, secrets, or private submission drafts. Use ignored `tmp/` locally; Cubbie uses private files under `~/.config/asu-registration-buddy/`.

## Refresh the public catalog export

From an environment with normal authorized access to ASU's public source:

```bash
.venv/bin/python asu-registration-buddy/scripts/registration.py refresh-snapshot --term "Spring 2027"
```

This sequential maintainer export checks completeness and term consistency before replacing `assets/catalog_snapshot.json.gz` and updating `assets/catalog_manifest.json`. The default cap is 150 pages. Review coverage, source timestamp, term, subject count, and record count; run tests, then commit both assets together.

`--subject CSE` intentionally creates a narrower export and replaces the full-semester bundle; do this only when limited coverage is intended. A blocked or incomplete export is not a valid refresh. Do not bypass access controls or run exports as part of every student's search. There is no automatic refresh service.

## Publish an update

Commit focused changes, push `main`, and resend the [same Skill folder link](https://github.com/aniiishhh/cubbie-class-registration-buddy/tree/main/asu-registration-buddy) to Cubbie. Updating GitHub does not automatically refresh an installed checkout.
