"""Explicit public catalog snapshots; never pretend a cached lookup is live."""
from datetime import datetime, timezone
from urllib.parse import urlencode

from sources import ASU_BASE, SourceError

FORMAT = "asu-public-catalog-snapshot-v1"
CLASS_FIELDS = {
    "STRM", "SUBJECT", "CATALOGNBR", "CLASSNBR", "CRSEID", "CLASSSECTION", "SESSIONCODE",
    "TITLE", "COURSETITLELONG", "SHORT_DESC", "CLASSDESCR", "STARTDATE", "ENDDATE",
    "STARTTIME", "ENDTIME", "STARTTIMES", "ENDTIMES", "MEETINGDATES", "DAYLIST",
    "CAMPUS", "LOCATION", "INSTRUCTIONMODE", "INSTRUCTORSLIST", "UNITSRANGE",
    "UNITSMINIMUM", "UNITSMAXIMUM", "SSRCOMPONENT", "COMPONENTPRIMARY", "ASSOCIATEDCLASS",
    "ENRLCAP", "ENRLTOT", "ENRLSTAT", "CLASSSTAT", "HASACTIVERESERVEDSEATS",
    "RQMNTDESIGNTN", "GSGOLD", "GSMAROON", "DESCRLONG", "DESCRLONG1", "NOTES",
}
ROOT_FIELDS = {"DAYLIST", "seatInfo", "NOTES", "GSGOLD", "GSMAROON", "RQMNTDESIGNTN", "HOURS", "SSR"}


class CacheMiss(ValueError):
    pass


def build_snapshot(client, term, subject, max_pages=10):
    query = {"term": term, "subject": subject, "campusOrOnlineSelection": "A", "searchType": "all"}
    records, coverage = client.search(query, max_pages)
    if not coverage.get("complete"):
        raise SourceError("Snapshot refresh was incomplete; the existing snapshot was not replaced.")
    compact = []
    for record in records:
        cl = record["CLAS"]
        if str(cl.get("STRM")) != term or cl.get("SUBJECT") != subject:
            raise SourceError("Snapshot refresh returned an unexpected semester or subject.")
        compact.append({"CLAS": {k: v for k, v in cl.items() if k in CLASS_FIELDS},
                        **{k: v for k, v in record.items() if k in ROOT_FIELDS}})
    return {"format": FORMAT, "source_checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "query": query, "source_url": ASU_BASE + "/search/classes?" + urlencode(query),
            "coverage": coverage, "classes": compact}


def read_snapshot(data, term, subject, now=None):
    if data.get("format") != FORMAT:
        raise ValueError("Unexpected catalog snapshot format.")
    query = data.get("query", {})
    if not subject or query.get("term") != term or query.get("subject") != subject.upper():
        raise CacheMiss("The bundled snapshot does not cover this semester/subject. Use the official ASU browser search; no empty result was inferred.")
    if query.get("campusOrOnlineSelection") != "A" or query.get("searchType") != "all":
        raise ValueError("A subject snapshot must contain unrestricted catalog results.")
    checked = datetime.fromisoformat(data["source_checked_at"])
    if checked.tzinfo is None:
        raise ValueError("Snapshot timestamp must include its timezone.")
    age = ((now or datetime.now(timezone.utc)) - checked).total_seconds()
    if age < -300:
        raise ValueError("Snapshot timestamp is in the future.")
    if not isinstance(data.get("classes"), list) or not isinstance(data.get("coverage"), dict):
        raise ValueError("Snapshot records or coverage are invalid.")
    for record in data["classes"]:
        if str(record.get("CLAS", {}).get("STRM")) != term or record.get("CLAS", {}).get("SUBJECT") != subject.upper():
            raise ValueError("Snapshot contains records outside its declared scope.")
    return data["classes"], dict(data["coverage"]), {
        "source_checked_at": data["source_checked_at"], "cache_age_hours": round(max(0, age) / 3600, 2),
        "cache_stale": age > 86400, "source_url": data["source_url"], "snapshot_scope": query,
    }
