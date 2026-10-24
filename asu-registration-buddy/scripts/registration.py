#!/usr/bin/env python3
"""Small JSON CLI for Cubbie. Calendar stays entirely with Cubbie's native abilities."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import sys

from catalog import (CAMPUSES, clean, clock, day_codes, filter_section, normalize,
                     preference_check, term_code, term_label)
from professors import professor_evidence
from sources import ASUClient, RMPClient, SourceError
from snapshots import CacheMiss, build_snapshot, read_snapshot

ROOT = Path(__file__).resolve().parent.parent
MAX_OUTPUT = 7800


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def load_json(path):
    path = Path(path).expanduser()
    if path.stat().st_size > 2_000_000:
        raise ValueError("Input JSON is too large (maximum 2 MB).")
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, value):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=True)
    path.chmod(0o600)


def emit(value):
    """Stay below Cubbie's read limit without ever cutting JSON or meeting rows."""
    while True:
        if "results" in value:
            value["returned"] = len(value["results"])
            value["next_offset"] = value.get("offset", 0) + value["returned"]
        encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
        if len(encoded) <= MAX_OUTPUT or len(value.get("results", [])) <= 1:
            break
        value["results"].pop()
        value["output_limited"] = True
    if len(encoded) > MAX_OUTPUT:
        # No silently truncated evidence: ask for a smaller bounded request.
        print(json.dumps({"status": "output_too_large", "message": "Narrow the query or request fewer reviews; full records were not printed."}))
        return 5
    print(encoded)
    return 0


def bounded_int(low, high):
    def parse(value):
        try:
            value = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError("Expected an integer.") from None
        if not low <= value <= high:
            raise argparse.ArgumentTypeError(f"Must be between {low} and {high}.")
        return value
    return parse


def parser():
    result = Parser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True, parser_class=Parser)
    search = sub.add_parser("search", help="Search ASU sections, with explicit preference filtering.")
    search.add_argument("--term", help='Required live: "Spring 2027" or 2271; never defaults to a semester.')
    search.add_argument("--subject")
    search.add_argument("--course-number")
    search.add_argument("--keyword")
    search.add_argument("--instructor")
    search.add_argument("--population", choices=["all", "campus", "asu-online"], default="all")
    search.add_argument("--campus", help="Teaching location, e.g. TEMPE, WEST, POLY or DTPHX.")
    search.add_argument("--modality", choices=["any", "in-person", "hybrid", "online", "sync"], default="any")
    search.add_argument("--session")
    search.add_argument("--level", choices=["lower", "upper", "graduate", "1", "2", "3", "4", "5", "6", "7", "8", "9"])
    search.add_argument("--min-credits", type=float)
    search.add_argument("--max-credits", type=float)
    search.add_argument("--designation", help="Explicit catalog tag, e.g. gold:HUAD or maroon:HU; not degree verification.")
    search.add_argument("--open-only", action="store_true")
    search.add_argument("--days", help="Allowed days; all known meetings must fit, e.g. MON,TUE,WED,THU.")
    search.add_argument("--after", help="Earliest class start, 24-hour HH:MM in America/Phoenix.")
    search.add_argument("--before", help="Latest class end, 24-hour HH:MM in America/Phoenix.")
    search.add_argument("--limit", type=bounded_int(1, 5), default=3)
    search.add_argument("--max-pages", type=bounded_int(1, 5), default=3)
    search.add_argument("--offset", type=bounded_int(0, 10000), default=0)
    search.add_argument("--save", help="Optional private file for paging fetched candidates without more network calls.")
    mode = search.add_mutually_exclusive_group()
    mode.add_argument("--sample", action="store_true")
    mode.add_argument("--cached", action="store_true", help="Explicit bundled public snapshot; never a live seat check.")
    refresh = sub.add_parser("refresh-snapshot", help="Maintainer command: refresh a complete public subject snapshot.")
    refresh.add_argument("--term", required=True)
    refresh.add_argument("--subject", required=True)
    refresh.add_argument("--max-pages", type=bounded_int(1, 20), default=10)
    page = sub.add_parser("page", help="Read another page from a saved search.")
    page.add_argument("--file", required=True)
    page.add_argument("--offset", type=bounded_int(0, 10000), default=0)
    page.add_argument("--limit", type=bounded_int(1, 5), default=3)
    for command in ("detail", "subjects"):
        item = sub.add_parser(command)
        item.add_argument("--term")
        item.add_argument("--sample", action="store_true")
        if command == "detail":
            item.add_argument("--subject")
            item.add_argument("--course-number")
            item.add_argument("--course-id")
        else:
            item.add_argument("--query", default="", help="Filter subject code or description.")
    prof = sub.add_parser("professor", help="Resolve an ASU instructor and fetch bounded RMP evidence.")
    prof.add_argument("--name")
    prof.add_argument("--course", default="")
    prof.add_argument("--campus", default="")
    prof.add_argument("--school-id")
    prof.add_argument("--teacher-id", help="Only use after confirming a candidate returned by this name search.")
    prof.add_argument("--max-pages", type=bounded_int(1, 3), default=2)
    prof.add_argument("--max-reviews", type=bounded_int(1, 6), default=4)
    prof.add_argument("--sample", action="store_true")
    return result


def fixture():
    return load_json(ROOT / "assets" / "sample_sources.json")


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def search_sections(args):
    term = term_code(args.term or ("Spring 2027" if args.sample else ""))
    if args.sample and args.save:
        raise ValueError("Sample mode never writes saved searches; omit --save.")
    if not (args.subject or args.keyword or args.designation or args.sample):
        raise ValueError("Provide a course, subject, interest keyword or specific catalog designation.")
    if args.subject and not re.fullmatch(r"[A-Za-z]{2,5}", args.subject):
        raise ValueError("Use a subject code such as CSE; subjects --query can look up names.")
    if args.course_number and (not args.subject or not re.fullmatch(r"\d{3}[A-Za-z]?", args.course_number)):
        raise ValueError("A course number needs a subject and three digits, optionally a suffix; use --level for a range.")
    if args.session:
        args.session = args.session.upper()
    if args.designation and not re.fullmatch(r"(?:gold|maroon|other):[A-Za-z0-9]+", args.designation):
        raise ValueError("Specify a designation as gold:CODE, maroon:CODE or other:CODE.")
    if any(v is not None and (not math.isfinite(v) or v < 0 or v > 30) for v in (args.min_credits, args.max_credits)):
        raise ValueError("Credit filters must be between 0 and 30.")
    if args.min_credits is not None and args.max_credits is not None and args.min_credits > args.max_credits:
        raise ValueError("Minimum credits cannot exceed maximum credits.")
    after, before = clock(args.after), clock(args.before)
    if (args.after and after is None) or (args.before and before is None) or (after and before and after >= before):
        raise ValueError("Use valid same-day time bounds, with earliest start before latest end.")
    allowed = day_codes(args.days)
    if args.days and not allowed:
        raise ValueError("Use valid allowed days, e.g. MON,TUE,WED,THU.")
    params = {"term": term, "campusOrOnlineSelection": "O" if args.population == "asu-online" else "A"}
    for field, key in (("subject", "subject"), ("course_number", "catalogNbr"), ("keyword", "keywords"),
                       ("instructor", "instructorName"), ("session", "session")):
        if getattr(args, field):
            params[key] = getattr(args, field).upper() if field != "keyword" and field != "instructor" else getattr(args, field)
    if args.campus:
        params["campus"] = CAMPUSES.get(args.campus.lower(), args.campus.upper())
    if args.open_only:
        params["searchType"] = "open"
    cache_info = None
    if args.cached:
        raw, coverage, cache_info = read_snapshot(load_json(ROOT / "assets" / "catalog_snapshot.json"), term, args.subject)
        if args.keyword:
            raw = [r for r in raw if args.keyword.casefold() in clean(
                r["CLAS"].get("COURSETITLELONG") or r["CLAS"].get("TITLE")).casefold()]
    elif args.sample:
        raw = fixture()["classes"]
        if args.keyword:
            raw = [r for r in raw if args.keyword.casefold() in clean(r["CLAS"].get("TITLE")).casefold()]
        coverage = {"fetched": len(raw), "total": len(raw), "pages": 0, "complete": True, "scope": "fictional sample only"}
    else:
        raw, coverage = ASUClient().search(params, args.max_pages)
    matches, excluded = [], 0
    for row in raw:
        section = normalize(row)
        if section["term"] != term or not filter_section(section, args):
            continue
        section["preference_check"] = preference_check(section, allowed, after, before)
        if section["preference_check"]["status"] == "conflict":
            excluded += 1
            continue
        matches.append(section)
    matches.sort(key=lambda s: (s["open_seats"] is None or s["open_seats"] <= 0 or s["enrollment_status"] != "O" or s["class_status"] != "A",
                                s["preference_check"]["status"] == "unknown"))
    # Discovery initially shows different courses; keep every section in the saved file.
    display, seen = [], set()
    for section in matches:
        if args.course_number or section["course"] not in seen:
            display.append(section)
            seen.add(section["course"])
    dates = [(m["start_date"], m["end_date"]) for s in matches for m in s["meetings"]
             if m["start_date"] and m["end_date"]]
    result = {"status": "ok" if matches else "no_results", "sample": args.sample,
              "checked_at": None if args.sample or args.cached else timestamp(), "term": term_label(term),
              "data_mode": "cached" if args.cached else "sample" if args.sample else "live",
              "live_availability_verified": not (args.sample or args.cached),
              "coverage": coverage, "matched_sections": len(matches), "display_candidates": len(display),
              "excluded_by_time_preferences": excluded, "calendar_checked": False,
              "calendar_window": {"start": min(a for a, b in dates), "end_inclusive": max(b for a, b in dates),
                                  "timezone": "America/Phoenix"} if dates else None,
              "caveats": ["Seat counts do not establish enrollment eligibility.",
                          "Verify required linked components and enrollment restrictions on ASU.",
                          "Cubbie must check Calendar using its existing Calendar abilities."]}
    if args.sample:
        result["caveats"].insert(0, "FICTIONAL SAMPLE: not current classes, ratings or availability.")
    if cache_info:
        result.update(cache_info)
        result["caveats"].insert(0, "CACHED CATALOG: report source_checked_at; current seats, instructors and listings may have changed. Not a live check.")
        if args.keyword:
            result["caveats"].append("Cached keyword search matches course titles only, not full descriptions.")
        if args.open_only:
            result["caveats"].append("Open-only filtering used historical snapshot seat counts; current open seats are unverified.")
    if not coverage["complete"]:
        result["caveats"].append("Search coverage is capped; these are not necessarily all matching sections.")
    saved = {"format": "asu-registration-search-v1", "metadata": result,
             "sections": matches, "display": display}
    if args.save:
        save_json(args.save, saved)
        result["saved_file"] = str(Path(args.save).expanduser())
    result["offset"] = args.offset
    result["results"] = display[args.offset:args.offset + args.limit]
    return result


class SampleRMP:
    def __init__(self):
        self.data = fixture()

    def schools(self):
        return self.data["schools"]

    def professors(self, school_id, name, max_pages=2):
        return [p for p in self.data["professors"] if p["school"]["id"] == school_id], True

    def reviews(self, teacher_id, max_pages=2):
        return self.data["reviews"], False


def main(argv=None):
    try:
        args = parser().parse_args(argv)
        if args.command == "search":
            value = search_sections(args)
        elif args.command == "refresh-snapshot":
            subject = args.subject.upper()
            if not re.fullmatch(r"[A-Z]{2,5}", subject):
                raise ValueError("Provide a valid subject code.")
            data = build_snapshot(ASUClient(), term_code(args.term), subject, args.max_pages)
            path = ROOT / "assets" / "catalog_snapshot.json"
            save_json(path, data)
            value = {"status": "refreshed", "snapshot": str(path), "source_checked_at": data["source_checked_at"],
                     "query": data["query"], "coverage": data["coverage"]}
        elif args.command == "page":
            data = load_json(args.file)
            if data.get("format") != "asu-registration-search-v1":
                raise ValueError("Expected a saved registration search file.")
            value = dict(data["metadata"])
            value.update({"offset": args.offset, "results": data["display"][args.offset:args.offset + args.limit],
                          "saved_file": str(Path(args.file).expanduser()), "cached": True})
            value["caveats"] = value["caveats"] + ["Cached search: re-run live search before relying on seats."]
        elif args.command == "professor":
            name = args.name or ("Alex Example" if args.sample else "")
            if not name.strip():
                raise ValueError("Provide the instructor's name from the ASU listing.")
            value = professor_evidence(SampleRMP() if args.sample else RMPClient(), name, args.course,
                                       args.campus, args.school_id, args.teacher_id, args.max_pages, args.max_reviews)
            value.update({"sample": args.sample, "checked_at": None if args.sample else timestamp()})
            if args.sample:
                value["caveats"].insert(0, "FICTIONAL SAMPLE: not real professor evidence.")
        else:
            term = term_code(args.term or ("Spring 2027" if args.sample else ""))
            if args.command == "subjects":
                data = fixture()["subjects"] if args.sample else ASUClient().subjects(term)
                results = [{"code": clean(s.get("CODE")), "name": clean(s.get("DESCR"))} for s in data
                           if args.query.casefold() in (clean(s.get("CODE")) + " " + clean(s.get("DESCR"))).casefold()]
                value = {"status": "ok", "sample": args.sample, "term": term_label(term),
                         "matched": len(results), "results": results[:40]}
            else:
                if not args.sample and not all((args.subject, args.course_number, args.course_id)):
                    raise ValueError("Provide subject, course number and course ID from search results.")
                data = fixture()["course_details"] if args.sample else ASUClient().course_detail(
                    term, args.subject.upper(), args.course_number.upper(), args.course_id)
                details = []
                for course in data[:3]:
                    requirements = [clean(c.get("INFO", {}).get("ENROLLREQ")) for c in course.get("COLLEGEMAP", [])]
                    details.append({"description": clean(course.get("DESCRLONG"))[:1600],
                                    "prerequisites_and_restrictions": [r[:1200] for r in requirements if r]})
                value = {"status": "ok" if details else "no_results", "sample": args.sample,
                         "checked_at": None if args.sample else timestamp(), "results": details,
                         "caveat": "Listed requirements are not a personalized eligibility or degree audit."}
        return emit(value)
    except SourceError as exc:
        error = {"status": "source_unavailable", "message": str(exc),
                 "service": exc.service, "http_status": exc.http_status,
                 "response_headers": exc.response_headers}
        if exc.http_status == 403:
            error["next_step"] = "Use Cubbie's actual browser on the official website; do not retry blocked requests or bypass access controls. ASU search may use --cached for covered subjects, clearly labeled as historical data."
        emit(error)
        return 3
    except CacheMiss as exc:
        emit({"status": "cache_miss", "message": str(exc)})
        return 6
    except ModuleNotFoundError:
        emit({"status": "setup_required", "message": "Run the pinned package Setup commands in SKILL.md."})
        return 4
    except (ValueError, OSError, KeyError, TypeError) as exc:
        emit({"status": "invalid_input", "message": str(exc)[:300]})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
