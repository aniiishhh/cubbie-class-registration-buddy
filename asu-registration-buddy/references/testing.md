# Acceptance checks

Use these to verify the installed Skill after an update. Fixtures establish command behavior; real source and Calendar checks establish the student experience. Never report a test as passed merely because it is listed here.

## Offline smoke checks

From the Skill folder, with Python 3.10+:

```bash
python3 scripts/registration.py search --sample --subject CSE --course-number 240
python3 scripts/registration.py professor --sample --course "CSE 240"
python3 scripts/registration.py search --cached --term "Spring 2027" --subject CSE --course-number 572 --level 5 --population all --limit 3
```

Check that fictional samples are labeled, real catalog output preserves original source time, `--level 5` returns only 500–599, and generated ASU URLs use long query keys. The full automated suite lives at repository root in `tests/`; see CONTRIBUTING.md there.

## Cubbie conversation checks

1. **Install/update.** Send the public `asu-registration-buddy` folder link. Confirm Cubbie reads the current Skill and executes from the updated checkout.
2. **Intake.** Ask “Help me find machine learning classes.” Missing semester/program/preferences should be grouped together, with at most one further round for essentials. A course code is optional.
3. **Exact courses.** Ask for Spring 2027 CSE 575, 510, 512, and 572, with your actual program/location preferences. Expect separate exact searches, then one comparison. Spring 2027 uses `--cached` directly.
4. **Discovery.** Ask for a three-credit 500-level elective. Confirm keyword, level, population, and credit filters; unknowns should stay explicit. No eligible degree-plan guarantee.
5. **Source note.** Expect one brief original catalog date/current-seat note in the comparison. Ask a follow-up about a professor; the same warning should not be repeated automatically.
6. **Official links.** Open a returned ASU URL. It should load the requested semester/course; a valid section fragment should expand the intended section. Check returned IDs against the listing. RMP links should open the matched professor.
7. **Review depth.** Confirm live RMP lookup saves a full corpus, follows available pagination, and reads `review-page` batches until `next_offset >= total_reviews`. The final summary should include recurring and mixed themes, course/date scope, and actual examined coverage. A few overview excerpts do not count as reading the corpus.
8. **Calendar.** With the existing connection, check the full meeting date range and all rows against busy events. Known overlaps are excluded or clearly explained. Without Calendar access, continue with stated preferences and mark it unchecked.
9. **Backup.** Ask “What if that section fills?” Expect another suitable section of the same course if one exists; no historical-seat guarantee or invented academic equivalence.

## Failure checks

- A denied live ASU request should stop blocked requests, retain useful planning evidence, and continue independent RMP/Calendar work. No challenge bypass or unavailable browser handoff requirement.
- An unsupported bundled term should return `cache_miss`, not “no classes exist.”
- Ambiguous RMP identity should produce no verified ratings. A later-page review failure should retain partial evidence with explicit coverage.
- Incomplete Calendar or meeting data must not become a conflict-free guarantee.
- Refreshing a saved file page must preserve the original source timestamp.
- No fixture may write real saved state; no command should change Calendar events or registration accounts.

The corrected ASU course-results URL and UI-generated section fragment were checked in a real browser during development. Live RMP full-corpus retrieval was also checked. Recheck actual Cubbie behavior after installation; local success alone cannot establish Cubbie's network access or Calendar coverage.
