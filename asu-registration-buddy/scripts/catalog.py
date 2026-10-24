"""Normalize ASU records without throwing away additional meeting rows."""
from __future__ import annotations

from datetime import datetime
from html import unescape
import math
import re
from urllib.parse import urlencode

DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
CAMPUSES = {"tempe": "TEMPE", "poly": "POLY", "polytechnic": "POLY",
            "west": "WEST", "west valley": "WEST", "downtown": "DTPHX",
            "downtown phoenix": "DTPHX", "mesa": "MESACITYCR"}


def clean(value):
    if value is None:
        return ""
    return " ".join(unescape(re.sub(r"<[^>]*>", " ", str(value))).split())


def term_code(value):
    value = clean(value).lower()
    match = re.fullmatch(r"(spring|summer|fall)\s+(20\d{2})", value)
    if match:
        return "2" + match[2][2:] + {"spring": "1", "summer": "4", "fall": "7"}[match[1]]
    if re.fullmatch(r"2\d{2}[147]", value):
        return value
    raise ValueError('Specify a semester and year, e.g. "Spring 2027" (or ASU term 2271).')


def term_label(code):
    return {"1": "Spring", "4": "Summer", "7": "Fall"}[code[-1]] + " 20" + code[1:3]


def day_codes(value):
    text = clean(value).lower().replace(",", " ")
    if not text or text in {"tba", "arr", "arranged", "none"}:
        return []
    aliases = {"monday": "m", "mon": "m", "tuesday": "t", "tues": "t", "tue": "t",
               "wednesday": "w", "wed": "w", "thursday": "r", "thurs": "r", "thur": "r", "thu": "r",
               "friday": "f", "fri": "f", "saturday": "s", "sat": "s", "sunday": "u", "sun": "u"}
    for word, code in aliases.items():
        text = re.sub(r"\b" + word + r"\b", code, text)
    text = text.replace("th", "r").replace("tu", "t").replace("su", "u").replace("sa", "s")
    text = re.sub(r"[\s/;-]", "", text)
    if not re.fullmatch(r"[mtwrfsu]+", text):
        return []
    mapping = dict(zip("mtwrfsu", DAYS))
    return [day for day in DAYS if day in {mapping[c] for c in text}]


def date_string(value):
    value = clean(value)
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def clock(value):
    value = clean(value).upper()
    if not value:
        return None
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).strftime("%H:%M")
        except ValueError:
            pass
    return None


def rows(value):
    if isinstance(value, list):
        return value
    return re.split(r"<br\s*/?>", str(value or ""), flags=re.I)


def meetings(raw):
    cl = raw["CLAS"]
    dates = cl.get("MEETINGDATES") or []
    if not isinstance(dates, list):
        dates = []
    starts = rows(cl.get("STARTTIMES") if cl.get("STARTTIMES") is not None else cl.get("STARTTIME"))
    ends = rows(cl.get("ENDTIMES") if cl.get("ENDTIMES") is not None else cl.get("ENDTIME"))
    days = rows(raw.get("DAYLIST") if raw.get("DAYLIST") is not None else cl.get("DAYLIST"))
    count = max(len(dates), len(starts), len(ends), len(days), 1)
    result = []
    for i in range(count):
        # Only section-level STARTDATE/ENDDATE can safely apply to every row.
        pair = dates[i] if i < len(dates) and isinstance(dates[i], list) else []
        start_date = date_string(pair[0]) if len(pair) >= 2 else date_string(cl.get("STARTDATE"))
        end_date = date_string(pair[1]) if len(pair) >= 2 else date_string(cl.get("ENDDATE"))
        start = clock(starts[i]) if i < len(starts) else None
        end = clock(ends[i]) if i < len(ends) else None
        codes = day_codes(days[i]) if i < len(days) else []
        known = bool(start and end and codes and start_date and end_date and start < end and start_date <= end_date)
        result.append({"days": codes, "start": start, "end": end, "start_date": start_date,
                       "end_date": end_date, "status": "scheduled" if known else "unknown"})
    return result


def number(value):
    try:
        value = float(value) if value is not None and str(value).strip() else None
        return value if value is not None and math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def normalize(raw):
    cl = raw["CLAS"]
    subject, catalog = clean(cl.get("SUBJECT")), clean(cl.get("CATALOGNBR"))
    term, class_number = clean(cl.get("STRM")), clean(cl.get("CLASSNBR"))
    seat = raw.get("seatInfo") or {}
    cap = number(seat.get("ENRL_CAP", cl.get("ENRLCAP")))
    enrolled = number(seat.get("ENRL_TOT", cl.get("ENRLTOT")))
    units = clean(cl.get("UNITSRANGE") or raw.get("HOURS") or cl.get("UNITSMINIMUM"))
    credit_values = re.findall(r"\d+(?:\.\d+)?", units)
    credits_min = number(cl.get("UNITSMINIMUM"))
    credits_max = number(cl.get("UNITSMAXIMUM"))
    if credits_min is None and credit_values:
        credits_min = float(credit_values[0])
    if credits_max is None and credit_values:
        credits_max = float(credit_values[-1])
    location = clean(cl.get("LOCATION")).upper()
    mode = clean(cl.get("INSTRUCTIONMODE")).upper()
    modality = {"P": "in-person", "HY": "hybrid", "OL": "online"}.get(mode, "unknown")
    if location in {"ASUONLINE", "ICOURSE"}:
        modality = "online"
    elif location == "ASUSYNC":
        modality = "sync"
    tags = {"gold": [], "maroon": [], "other": []}
    for key, field in (("gold", "GSGOLD"), ("maroon", "GSMAROON"), ("other", "RQMNTDESIGNTN")):
        for source in (raw, cl):
            values = source.get(field) or ""
            if not isinstance(values, list):
                values = re.split(r"[,;/|\s]+", str(values))
            tags[key].extend(clean(v).upper() for v in values if clean(v))
        tags[key] = sorted(set(tags[key]))
    notes = []
    for value in (raw.get("NOTES"), cl.get("NOTES"), cl.get("DESCRLONG"), cl.get("DESCRLONG1")):
        for item in value if isinstance(value, list) else [value]:
            if clean(item) and clean(item) not in notes:
                notes.append(clean(item)[:300])
    component = clean(cl.get("SSRCOMPONENT") or raw.get("SSR"))
    primary_component = clean(cl.get("COMPONENTPRIMARY"))
    instructor_list = cl.get("INSTRUCTORSLIST") or []
    if not isinstance(instructor_list, list):
        instructor_list = [instructor_list]
    return {
        "course": f"{subject} {catalog}", "subject": subject, "number": catalog,
        "title": clean(cl.get("COURSETITLELONG") or cl.get("TITLE"))[:180],
        "term": term, "class_number": class_number, "section": clean(cl.get("CLASSSECTION")),
        "course_id": clean(cl.get("CRSEID")), "session": clean(cl.get("SESSIONCODE")),
        "location": location, "administrative_campus": clean(cl.get("CAMPUS")),
        "population": "asu-online" if location == "ASUONLINE" else "campus",
        "modality": modality, "mode_code": mode,
        "instructors": [clean(n)[:100] for n in instructor_list if clean(n)],
        "credits": units, "credits_min": credits_min, "credits_max": credits_max,
        "open_seats": max(0, int(cap - enrolled)) if cap is not None and enrolled is not None else None,
        "capacity": int(cap) if cap is not None else None,
        "enrollment_status": clean(cl.get("ENRLSTAT")), "class_status": clean(cl.get("CLASSSTAT")),
        "reserved_seats": cl.get("HASACTIVERESERVEDSEATS") in (True, "Y", "T", 1),
        "component": component, "is_primary": not primary_component or component == primary_component,
        "associated_class": clean(cl.get("ASSOCIATEDCLASS")),
        "meetings": meetings(raw), "meeting_timezone": "America/Phoenix",
        "designations": tags, "notes": notes[:3],
        "asu_url": "https://catalog.apps.asu.edu/catalog/classes/classlist?" + urlencode({
            "t": term, "s": subject, "n": catalog, "hon": "F", "promod": "F", "e": "all"}),
    }


def filter_section(section, args):
    if args.subject and section["subject"] != args.subject.upper():
        return False
    if args.course_number and section["number"].upper() != args.course_number.upper():
        return False
    if args.instructor and not any(args.instructor.casefold() in name.casefold() for name in section["instructors"]):
        return False
    if args.population != "all" and section["population"] != args.population:
        return False
    if args.campus and section["location"] != CAMPUSES.get(args.campus.lower(), args.campus.upper()):
        return False
    if args.modality != "any" and section["modality"] != args.modality:
        return False
    if args.session and section["session"] != args.session:
        return False
    if args.open_only and (section["open_seats"] is None or section["open_seats"] <= 0
                           or section["enrollment_status"] != "O" or section["class_status"] != "A"):
        return False
    if not section["is_primary"]:
        return False
    n = re.match(r"\d+", section["number"])
    if args.level:
        lower, upper = {"lower": (100, 299), "upper": (300, 499), "graduate": (500, 999)}.get(
            args.level, (int(args.level) * 100, int(args.level) * 100 + 99) if args.level.isdigit() else (0, 0))
        if not n or not lower <= int(n[0]) <= upper:
            return False
    # A variable-credit course is not promised to deliver a particular fixed credit count.
    if args.min_credits is not None and (section["credits_min"] is None or section["credits_min"] < args.min_credits):
        return False
    if args.max_credits is not None and (section["credits_max"] is None or section["credits_max"] > args.max_credits):
        return False
    if args.designation:
        kind, tag = args.designation.lower().split(":")
        if tag.upper() not in section["designations"][kind]:
            return False
    return True


def preference_check(section, allowed_days=None, after=None, before=None):
    conflicts, unknown = [], False
    for meeting in section["meetings"]:
        if meeting["status"] != "scheduled":
            unknown = True
        if allowed_days and meeting["days"] and not set(meeting["days"]) <= set(allowed_days):
            conflicts.append("meets outside allowed days")
        if after and meeting["start"] and meeting["start"] < after:
            conflicts.append("starts before the earliest allowed time")
        if before and meeting["end"] and meeting["end"] > before:
            conflicts.append("ends after the latest allowed time")
    return {"status": "conflict" if conflicts else "unknown" if unknown else "matches",
            "reasons": sorted(set(conflicts)), "calendar_checked": False}
