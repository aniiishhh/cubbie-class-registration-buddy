"""Conservative professor identity resolution and bounded review evidence."""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from catalog import clean, number
from sources import SourceError


def normalized_name(value):
    text = unicodedata.normalize("NFKD", clean(value).casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\b(professor|prof|dr)\.?\s*", "", text)
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text).split())


def course_code(value):
    return re.sub(r"[^A-Z0-9]", "", clean(value).upper())


def candidate(raw):
    return {"teacher_id": raw["id"], "name": clean(f"{raw.get('firstName', '')} {raw.get('lastName', '')}"),
            "department": clean(raw.get("department")), "school": raw.get("school", {}),
            "url": f"https://www.ratemyprofessors.com/professor/{int(raw['legacyId'])}"}


def metric(value, upper=5):
    value = number(value)
    return value if value is not None and 0 <= value <= upper else None


def review(raw, url):
    return {"course": clean(raw.get("class")), "date": clean(raw.get("date"))[:10],
            "excerpt": clean(raw.get("comment"))[:450], "tags": clean(raw.get("ratingTags"))[:160],
            "difficulty": metric(raw.get("difficultyRating")), "clarity": metric(raw.get("clarityRating")),
            "attendance": clean(raw.get("attendanceMandatory")), "online": raw.get("isForOnlineClass"),
            "source_url": url}


def professor_evidence(client, name, course="", campus="", school_id=None, teacher_id=None,
                       max_pages=2, max_reviews=4):
    schools = [s for s in client.schools() if normalized_name(s.get("name", "")).startswith("arizona state university")]
    if school_id:
        schools = [s for s in schools if s.get("id") == school_id]
        if not schools:
            raise ValueError("The school ID must come from the returned ASU RMP directory entries.")
    # A teaching campus is not the same as an RMP school directory entry. Search
    # all returned ASU entries; use campus only to order candidates for display.
    target = {"WEST": "glendale", "POLY": "polytechnic", "TEMPE": "tempe"}.get(campus.upper(), "tempe")
    schools.sort(key=lambda s: target not in (s.get("city", "") + " " + s.get("name", "")).lower())
    found, complete, failures = {}, True, []
    for school in schools[:6]:
        try:
            rows, done = client.professors(school["id"], name, max_pages=max_pages)
            complete = complete and done
            for row in rows:
                if row.get("school", {}).get("id") == school["id"]:
                    found[row["id"]] = row
        except SourceError:
            complete = False
            failures.append(clean(school.get("name")))
    if schools and len(failures) == min(len(schools), 6):
        raise SourceError("Rate My Professors searches failed; use the ASU listings without ratings.")
    rows = list(found.values())
    exact = [r for r in rows if normalized_name(candidate(r)["name"]) == normalized_name(name)]
    if teacher_id:
        exact = [r for r in rows if r["id"] == teacher_id]
        if not exact:
            raise ValueError("The teacher ID must be a candidate returned by this ASU name search.")
    result = {"requested_name": name, "requested_course": course or None,
              "search_complete": complete and len(schools) <= 6,
              "school_entries_searched": len(schools[:6]),
              "caveats": ["RMP reviews are anecdotal; overall ratings are not course-specific.",
                          "RMP directory affiliation does not establish a section's teaching campus."]}
    if failures:
        result["caveats"].append("Some school searches failed; identity search coverage is incomplete.")
    if len(exact) != 1:
        ranked = sorted(rows, key=lambda r: SequenceMatcher(None, normalized_name(name), normalized_name(candidate(r)["name"])).ratio(), reverse=True)
        result.update({"status": "needs_confirmation" if rows else "not_found",
                       "candidates": [candidate(r) for r in ranked[:5]],
                       "message": "Do not attach ratings until identity is confirmed." if rows else "No matching profile found in the bounded ASU search."})
        return result
    chosen = exact[0]
    result.update({"status": "matched", "professor": candidate(chosen)})
    count = number(chosen.get("numRatings"))
    result["statistics"] = {
        "scope": "overall_professor", "rating_count": int(count) if count is not None else None,
        "rating": metric(chosen.get("avgRating")) if count else None,
        "difficulty": metric(chosen.get("avgDifficulty")) if count else None,
        "would_take_again_percent": metric(chosen.get("wouldTakeAgainPercent"), 100) if count else None}
    try:
        fetched, done = client.reviews(chosen["id"], max_pages=max_pages)
    except SourceError:
        result.update({"reviews_status": "unavailable", "course_reviews": [], "general_reviews": []})
        result["caveats"].append("Review retrieval failed; do not infer review themes from aggregate statistics.")
        return result
    deduped = {(r.get("date"), r.get("class"), r.get("comment")): r for r in fetched}
    fetched = sorted(deduped.values(), key=lambda r: clean(r.get("date")), reverse=True)
    specific = [r for r in fetched if course and course_code(r.get("class")) == course_code(course)]
    general = [r for r in fetched if r not in specific]
    # Course evidence is prioritized, with broader evidence labeled separately.
    selected = specific[:max_reviews]
    other = general[:max_reviews - len(selected)]
    result.update({"reviews_status": "ok", "review_pages_complete": done,
                   "reviews_fetched": len(fetched), "course_matches_in_fetched_pages": len(specific),
                   "course_reviews": [review(r, result["professor"]["url"]) for r in selected],
                   "general_reviews": [review(r, result["professor"]["url"]) for r in other]})
    if course and not specific:
        result["caveats"].append("No course-specific reviews found in fetched pages; broader reviews are labeled separately.")
    if not done:
        result["caveats"].append("Only a bounded sample of review pages was fetched; do not describe it as all reviews.")
    return result
