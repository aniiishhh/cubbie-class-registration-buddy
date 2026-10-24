# Real Cubbie test checklist

Local script tests cannot verify Cubbie's trigger selection, connected Calendar implementation or iMessage replies. Finish these checks on a real Cubbie account before marking the main flow complete.

1. Text the public branch/folder link. Cubbie should explain the third-party Skill and ask before installation. Approve; Setup should run. Start a new message after install so the Skill appears in its list.
2. Text: “Help me pick classes.” Expect ONE short grouped intake covering missing semester/year, course or subject/interest, and relevant campus/ASU Online distinction. Optional preferences are welcomed, not individually required.
3. Reply with semester, subject, campus and preferences in one message. Cubbie should use them without repeating questions. If an essential is absent, it gets at most one grouped follow-up. No course code is required for discovery.
4. Text a complete known-course request, for example “Compare CSE 240 sections for Spring 2027. I'm a Tempe campus student, no classes before 10.” Expect live sections, Phoenix-local time filtering, correct physical location, seat-check time and source links. Do not use the sample fixture for this check.
5. With Calendar connected, put or identify a real busy event that overlaps a returned meeting during the actual section dates. Cubbie should use its existing Calendar abilities, identify that conflict and prefer another section. Check recurring events, the full session range, timezone conversion and any linked-component/unknown-time caveats. The Skill must not install a Calendar client or change events.
6. Check a section whose session dates do not overlap a Calendar event; it should not be rejected solely because its weekday/time matches outside the session. For a partial Calendar read, Cubbie must state the checked range rather than claim complete freedom from conflicts.
7. With Calendar unavailable, repeat the request. Cubbie should continue from explicit preferences and say Calendar was not checked, without a setup questionnaire.
8. Text “Find a three-credit upper-division CSE elective related to AI for Spring 2027.” Expect bounded discovery, different candidate courses where available, descriptions supporting interest relevance, and no claim that these fulfill personalized degree requirements. If “AI” has no literal matches, propose a broader catalog keyword.
9. Compare instructors. Check one RMP profile and review against the linked page: name/school/department, overall rating count, course-specific vs general evidence, review dates and bounded sample disclosure. An unresolved identity or missing profile must not produce invented ratings.
10. Ask “What if that section fills?” Expect a different section of the same course with a fresh live seat check and Calendar/preferences check. If no suitable backup exists, say so; do not invent a substitute course or ignore a time constraint.
11. Try “Find a Tempe section” on a course whose administrative campus differs from its teaching location. Cubbie must use teaching location. Check ASU Online vs iCourse distinctions too.
12. Ask an unrelated question, such as “Write my professor an absence email.” Cubbie should use its existing relevant behavior rather than force this Skill.
13. Push a fix when authorized and text the branch link again. Confirm the updated version runs. “What Skills do I have?” should list it. Test removal when finished if desired; the optional cache under HOME can be removed separately.

## Short conversation evaluations

These are expected behaviors, not claims of completed Cubbie tests:

| Prompt | Expected behavior |
| --- | --- |
| “Spring 2027, CSE 240, Tempe, after 10, no Fridays” | Starts retrieval without intake questions; uses Calendar natively; provides section comparison plus same-course backup if available. |
| “Need an AI elective next semester, 3 credits, campus student” | Resolves the semester from student-local date, searches bounded discovery, batches any genuinely missing essentials in one message. |
| “I want something online” | One grouped clarification for semester, course/interest and ASU Online vs campus-student iCourse eligibility. Does not equate online with asynchronous. |
| “That professor has no RMP page?” | Keeps the class visible, says professor evidence is unavailable, does not invent or downgrade a rating. |
| “No matches? Try another campus.” | Updates the explicitly relaxed campus constraint while keeping other hard constraints. |
| “Choose the 15 credits I need to graduate” | Explains the boundary, can shortlist individual classes from an advisor-provided list, does not certify a degree plan. |

## Track 1 completion

The Skill must pass the official validator, scripts must pass local sample/live checks, and the main flow must work on the team's Cubbie. Submit a public repository link with the team/member details and a one-line pitch. A TikTok/Instagram demo is optional. Preview the exact public submission and obtain a clear yes before sending it, following the official kit.
