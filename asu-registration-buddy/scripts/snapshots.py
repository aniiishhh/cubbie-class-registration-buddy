"""Explicit public catalog snapshots; never pretend a cached lookup is live."""
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import tempfile
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


def build_snapshot(client, term, subject=None, max_pages=150):
    query = {"term": term, "campusOrOnlineSelection": "A", "searchType": "all",
             "honors": "F", "promod": "F", "refine": "Y"}
    if subject:
        query["subject"] = subject
    records, coverage = client.search(query, max_pages, page_delay=0.1)
    if not coverage.get("complete"):
        raise SourceError("Snapshot refresh was incomplete; the existing snapshot was not replaced.")
    compact = []
    for record in records:
        cl = record["CLAS"]
        if str(cl.get("STRM")) != term or not cl.get("SUBJECT") or (subject and cl.get("SUBJECT") != subject):
            raise SourceError("Snapshot refresh returned an unexpected semester or subject.")
        compact.append({"CLAS": {k: v for k, v in cl.items() if k in CLASS_FIELDS},
                        **{k: v for k, v in record.items() if k in ROOT_FIELDS}})
    return {"format": FORMAT, "source_checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "query": query, "source_url": ASU_BASE + "/search/classes?" + urlencode(query),
            "coverage": coverage, "classes": compact}


def load_snapshot(path):
    path = Path(path)
    if path.stat().st_size > 8_000_000:
        raise ValueError("Snapshot file exceeds the 8 MB compressed-size limit.")
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as handle:
        raw = handle.read(96_000_001)
    if len(raw) > 96_000_000:
        raise ValueError("Snapshot exceeds the 96 MB decompressed-size limit.")
    return json.loads(raw)


def write_snapshot(path, data):
    """Write an export atomically so a failed refresh leaves the prior one intact."""
    path = Path(path)
    encoded = json.dumps(data, ensure_ascii=True, separators=(",", ":")).encode()
    if len(encoded) > 96_000_000:
        raise ValueError("Snapshot exceeds the decompressed-size limit.")
    compressed = gzip.compress(encoded, mtime=0)
    if len(compressed) > 8_000_000:
        raise ValueError("Snapshot exceeds the compressed-size limit.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(compressed)
        os.replace(temp_path, path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def read_snapshot(data, term, subject, now=None):
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError("Unexpected catalog snapshot format.")
    query = data.get("query", {})
    if query.get("term") != term or (query.get("subject") and (not subject or query["subject"] != subject.upper())):
        raise CacheMiss("The bundled snapshot does not cover this semester/subject. No empty result was inferred; request a refreshed export or use an available official source.")
    if query.get("campusOrOnlineSelection") != "A" or query.get("searchType") != "all":
        raise ValueError("A catalog snapshot must contain unrestricted catalog results.")
    checked = datetime.fromisoformat(data["source_checked_at"])
    if checked.tzinfo is None:
        raise ValueError("Snapshot timestamp must include its timezone.")
    age = ((now or datetime.now(timezone.utc)) - checked).total_seconds()
    if age < -300:
        raise ValueError("Snapshot timestamp is in the future.")
    if not isinstance(data.get("classes"), list) or not isinstance(data.get("coverage"), dict):
        raise ValueError("Snapshot records or coverage are invalid.")
    for record in data["classes"]:
        cl = record.get("CLAS", {}) if isinstance(record, dict) else {}
        if (not isinstance(cl, dict) or str(cl.get("STRM")) != term or not cl.get("SUBJECT")
                or (query.get("subject") and cl.get("SUBJECT") != query["subject"])):
            raise ValueError("Snapshot contains records outside its declared scope.")
    return data["classes"], dict(data["coverage"]), {
        "source_checked_at": data["source_checked_at"], "cache_age_hours": round(max(0, age) / 3600, 2),
        "cache_stale": age > 86400, "source_url": data["source_url"], "snapshot_scope": query,
        "all_subjects": not bool(query.get("subject")),
        "snapshot_subject_count": len({r["CLAS"]["SUBJECT"] for r in data["classes"]}),
    }
