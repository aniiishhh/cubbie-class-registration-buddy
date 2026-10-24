"""Public-source clients adapted from the user's Class_Helper ASU and RMP clients.

No Cubbie/Google credentials or local Class_Helper imports are needed.
"""
from __future__ import annotations

from collections.abc import Mapping
import time

ASU_BASE = "https://eadvs-cscc-catalog-api.apps.asu.edu/catalog-microservices/api/v1"
RMP_BASE = "https://www.ratemyprofessors.com"
TIMEOUT = (5, 20)


class SourceError(RuntimeError):
    def __init__(self, message, *, service=None, http_status=None, response_headers=None):
        super().__init__(message)
        self.service = service
        self.http_status = http_status
        self.response_headers = response_headers or {}


def request_json(session, method, url, service, **kwargs):
    import requests
    response = None
    try:
        response = session.request(method, url, timeout=TIMEOUT, **kwargs)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        # Retain a small response-header allowlist, never request credentials,
        # cookies, full response bodies or URLs containing arbitrary query data.
        error_response = getattr(exc, "response", None)
        status = getattr(error_response, "status_code", None)
        observed = error_response if error_response is not None else response
        headers = getattr(observed, "headers", {})
        safe_headers = {}
        if isinstance(headers, Mapping):
            allowed = {"server", "via", "content-type", "cf-ray", "cf-mitigated", "retry-after"}
            safe_headers = {str(k).lower(): " ".join(str(v).split())[:180]
                            for k, v in headers.items() if str(k).lower() in allowed}
        detail = f"HTTP {status}" if status else type(exc).__name__
        raise SourceError(f"{service} is unavailable ({detail}); no result was inferred.",
                          service=service, http_status=status, response_headers=safe_headers) from None
    if isinstance(data, dict) and (data.get("errors") or data.get("error")):
        raise SourceError(f"{service} returned an API error; no result was inferred.")
    return data


class ASUClient:
    def __init__(self):
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json", "Authorization": "Bearer null",
            "Origin": "https://catalog.apps.asu.edu", "Referer": "https://catalog.apps.asu.edu/",
            "User-Agent": "Mozilla/5.0 ASURegistrationBuddy/1.0",
        })

    def search(self, params, max_pages=3, page_delay=0):
        query = {"campusOrOnlineSelection": "A", "honors": "F", "promod": "F",
                 "searchType": "all", "refine": "Y", **params}
        rows, seen, cursor = [], set(), None
        total, relation, pages = None, "unknown", 0
        complete = False
        for _ in range(max_pages):
            if cursor:
                query["scrollId"] = cursor
            data = request_json(self.session, "GET", f"{ASU_BASE}/search/classes", "ASU Class Search", params=query)
            if not isinstance(data, dict) or not isinstance(data.get("classes"), list):
                raise SourceError("ASU Class Search returned an unexpected response.")
            pages += 1
            count = data.get("total", {})
            if isinstance(count, dict):
                total = count.get("value", total)
                relation = count.get("relation", relation)
            page = data["classes"]
            new_rows = 0
            for raw in page:
                if not isinstance(raw, dict) or not isinstance(raw.get("CLAS"), dict):
                    raise SourceError("ASU Class Search returned a malformed section.")
                cl = raw["CLAS"]
                key = (str(cl.get("STRM")), str(cl.get("CLASSNBR")))
                if not key[1] or key[1] == "None":
                    raise SourceError("ASU Class Search returned a section without an identifier.")
                if key not in seen:
                    rows.append(raw)
                    seen.add(key)
                    new_rows += 1
            if (isinstance(total, int) and relation == "eq" and len(rows) >= total) or not page:
                complete = True
                break
            next_cursor = data.get("scrollId")
            # Elasticsearch may reuse the same scroll ID across different pages.
            if not next_cursor or not new_rows:
                break
            cursor = next_cursor
            if page_delay:
                time.sleep(page_delay)
        return rows, {"fetched": len(rows), "total": total, "total_relation": relation,
                      "pages": pages, "complete": complete}

    def course_detail(self, term, subject, number, course_id):
        data = request_json(self.session, "GET", f"{ASU_BASE}/search/courses", "ASU course details",
                            params={"term": term, "subject": subject, "catalogNbr": number,
                                    "course_id": course_id, "refine": "Y"})
        if not isinstance(data, list):
            raise SourceError("ASU course details returned an unexpected response.")
        return data

    def subjects(self, term):
        data = request_json(self.session, "GET", f"{ASU_BASE}/search/subjects", "ASU subjects",
                            params={"term": term, "sl": "Y"})
        if not isinstance(data, list):
            raise SourceError("ASU subjects returned an unexpected response.")
        return data


class RMPClient:
    def __init__(self):
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0", "Accept": "application/json",
            "Referer": RMP_BASE + "/", "Origin": RMP_BASE,
            # Public header used by the existing Class_Helper client, not a student secret.
            "Authorization": "Basic dGVzdDp0ZXN0",
        })
        try:
            response = self.session.get(RMP_BASE + "/", timeout=TIMEOUT)
            response.raise_for_status()
        except requests.RequestException:
            raise SourceError("Rate My Professors is unavailable; ASU results can still be used.") from None

    def graphql(self, query, variables):
        data = request_json(self.session, "POST", RMP_BASE + "/graphql", "Rate My Professors",
                            json={"query": query, "variables": variables})
        if not isinstance(data, dict) or not isinstance(data.get("data"), dict):
            raise SourceError("Rate My Professors returned an unexpected response.")
        return data["data"]

    def schools(self):
        data = self.graphql("""query($query: String!) {
          newSearch { schools(query: {text: $query}) {
            edges {node {id name city state}}
          }}
        }""", {"query": "Arizona State University"})
        try:
            nodes = [edge["node"] for edge in data["newSearch"]["schools"]["edges"]]
            if not all(isinstance(node, dict) and node.get("id") and node.get("name") for node in nodes):
                raise TypeError
            return nodes
        except (KeyError, TypeError):
            raise SourceError("Rate My Professors school search changed format.") from None

    def professors(self, school_id, name, max_pages=2):
        query = """query($count: Int!, $cursor: String, $query: TeacherSearchQuery!) {
          search: newSearch {teachers(query: $query, first: $count, after: $cursor) {
            edges {node {id legacyId firstName lastName department avgRating numRatings
              wouldTakeAgainPercent avgDifficulty school {id name}}}
            pageInfo {hasNextPage endCursor}
          }}
        }"""
        results, cursor, complete = {}, "", False
        for _ in range(max_pages):
            data = self.graphql(query, {"count": 20, "cursor": cursor,
                "query": {"text": name, "schoolID": school_id, "fallback": False}})
            try:
                page = data["search"]["teachers"]
                for edge in page["edges"]:
                    node = edge["node"]
                    if not isinstance(node, dict) or not node.get("id") or not str(node.get("legacyId", "")).isdigit():
                        raise TypeError
                    # The source's school filter is verified again before attaching evidence.
                    if isinstance(node.get("school"), dict) and node["school"].get("id") == school_id:
                        results[node["id"]] = node
                info = page["pageInfo"]
                if not info.get("hasNextPage"):
                    complete = True
                    break
                if not info.get("endCursor") or info["endCursor"] == cursor:
                    break
                cursor = info["endCursor"]
            except (KeyError, TypeError):
                raise SourceError("Rate My Professors professor search changed format.") from None
        return list(results.values()), complete

    def reviews(self, teacher_id, max_pages=2):
        query = """query($id: ID!, $count: Int!, $cursor: String!) {
          node(id: $id) {... on Teacher {
            ratings(first: $count, after: $cursor) {
              edges {node {comment ratingTags date class helpfulRating clarityRating
                difficultyRating grade attendanceMandatory wouldTakeAgain isForOnlineClass}}
              pageInfo {hasNextPage endCursor}
            }
          }}
        }"""
        results, cursor, complete = [], "", False
        for _ in range(max_pages):
            data = self.graphql(query, {"id": teacher_id, "count": 20, "cursor": cursor})
            try:
                page = data["node"]["ratings"]
                results.extend(edge["node"] for edge in page["edges"])
                info = page["pageInfo"]
                if not info.get("hasNextPage"):
                    complete = True
                    break
                if not info.get("endCursor") or info["endCursor"] == cursor:
                    break
                cursor = info["endCursor"]
            except (KeyError, TypeError):
                raise SourceError("Rate My Professors reviews changed format.") from None
        return results, complete
