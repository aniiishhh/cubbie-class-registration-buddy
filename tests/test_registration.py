"""Behavioral checks for the installable Skill; no live services or Calendar access."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1] / "asu-registration-buddy" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from catalog import clean, clock, day_codes, normalize, number, preference_check, term_code
from professors import professor_evidence
from registration import SampleRMP, emit, fixture, main, parser, save_json, search_sections
from sources import ASUClient, SourceError, request_json


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.raw = fixture()["classes"]

    def test_term_requires_a_year_and_valid_semester(self):
        for value in ("Spring", "next semester", "2272", "Winter 2027", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                term_code(value)
        self.assertEqual(term_code("Spring 2027"), "2271")
        self.assertEqual(term_code("Fall 2026"), "2267")
        self.assertEqual(term_code("Summer 2028"), "2284")

    def test_html_and_entities_are_data_not_markup(self):
        self.assertEqual(clean("T<br/>&nbsp;"), "T")
        self.assertEqual(clean("<b>A &amp; B</b>"), "A & B")

    def test_weekdays_distinguish_tuesday_and_thursday(self):
        self.assertEqual(day_codes("T Th"), ["TUE", "THU"])
        self.assertEqual(day_codes("TTh"), ["TUE", "THU"])
        self.assertEqual(day_codes("MWF"), ["MON", "WED", "FRI"])
        self.assertEqual(day_codes("MON,TUE,WED,THU"), ["MON", "TUE", "WED", "THU"])
        self.assertEqual(day_codes("unknown"), [])

    def test_noon_and_midnight(self):
        self.assertEqual(clock("12:00 AM"), "00:00")
        self.assertEqual(clock("12:00 PM"), "12:00")
        self.assertIsNone(clock("25:00"))

    def test_preserves_second_unknown_hybrid_meeting(self):
        section = normalize(self.raw[0])
        self.assertEqual(len(section["meetings"]), 2)
        self.assertEqual(section["meetings"][0]["days"], ["TUE"])
        self.assertEqual(section["meetings"][1]["status"], "unknown")
        self.assertEqual(preference_check(section)["status"], "unknown")

    def test_secondary_scheduled_meeting_can_break_time_preference(self):
        raw = deepcopy(self.raw[0])
        raw["DAYLIST"] = ["T", "F"]
        raw["CLAS"]["STARTTIMES"] = ["12:00 PM", "8:00 AM"]
        raw["CLAS"]["ENDTIMES"] = ["1:15 PM", "9:00 AM"]
        result = preference_check(normalize(raw), after="10:00")
        self.assertEqual(result["status"], "conflict")

    def test_html_time_rows_work_without_structured_arrays(self):
        raw = deepcopy(self.raw[0])
        raw.pop("DAYLIST")
        raw["CLAS"].pop("STARTTIMES")
        raw["CLAS"].pop("ENDTIMES")
        raw["CLAS"].update({"DAYLIST": "M W<br/>F", "STARTTIME": "10:00 AM<br/>1:00 PM",
                            "ENDTIME": "11:00 AM<br/>2:00 PM"})
        rows = normalize(raw)["meetings"]
        self.assertEqual(rows[0]["days"], ["MON", "WED"])
        self.assertEqual(rows[1]["start"], "13:00")
        self.assertEqual(rows[1]["days"], ["FRI"])

    def test_teaching_location_is_separate_from_administrative_campus(self):
        section = normalize(self.raw[1])
        self.assertEqual(section["administrative_campus"], "TEMPE")
        self.assertEqual(section["location"], "WEST")

    def test_online_is_not_assumed_asynchronous(self):
        section = normalize(self.raw[2])
        self.assertEqual(section["population"], "asu-online")
        self.assertEqual(section["modality"], "online")
        self.assertEqual(section["meetings"][0]["status"], "unknown")

    def test_missing_seat_data_stays_unknown(self):
        raw = deepcopy(self.raw[0])
        raw.pop("seatInfo")
        self.assertIsNone(normalize(raw)["open_seats"])

    def test_missing_dates_or_reversed_times_are_not_certified(self):
        raw = deepcopy(self.raw[1])
        raw["CLAS"]["MEETINGDATES"] = []
        self.assertEqual(normalize(raw)["meetings"][0]["status"], "unknown")
        raw["CLAS"]["MEETINGDATES"] = [["1/11/2027", "4/30/2027"]]
        raw["CLAS"]["ENDTIMES"] = ["8:00 AM"]
        self.assertEqual(normalize(raw)["meetings"][0]["status"], "unknown")

    def test_day_constraint_applies_to_all_weekdays(self):
        section = normalize(self.raw[1])
        self.assertEqual(preference_check(section, ["MON", "WED"])["status"], "conflict")
        self.assertEqual(preference_check(section, ["MON", "WED", "FRI"])["status"], "matches")

    def test_time_boundaries_are_inclusive(self):
        section = normalize(self.raw[1])
        self.assertEqual(preference_check(section, after="09:00", before="09:50")["status"], "matches")
        self.assertEqual(preference_check(section, before="09:49")["status"], "conflict")

    def test_nonfinite_numbers_are_not_valid_source_metrics(self):
        self.assertIsNone(number("nan"))
        self.assertIsNone(number("inf"))


class SearchTests(unittest.TestCase):
    def search(self, *flags):
        return search_sections(parser().parse_args(["search", "--sample", *flags]))

    def test_campus_filter_does_not_use_administrative_campus(self):
        result = self.search("--subject", "CSE", "--course-number", "240", "--campus", "TEMPE")
        self.assertEqual([s["class_number"] for s in result["results"]], ["SAMPLE-101"])

    def test_population_distinguishes_asu_online(self):
        result = self.search("--subject", "CSE", "--course-number", "240", "--population", "campus")
        self.assertEqual(result["matched_sections"], 2)
        result = self.search("--subject", "CSE", "--course-number", "240", "--population", "asu-online")
        self.assertEqual([s["class_number"] for s in result["results"]], ["SAMPLE-103"])

    def test_nonprimary_lab_is_not_another_course_or_credits(self):
        result = self.search("--subject", "BIO", "--course-number", "181")
        self.assertEqual(result["matched_sections"], 1)
        self.assertEqual(result["results"][0]["credits"], "4")

    def test_discovery_does_not_require_course_code(self):
        result = self.search("--subject", "CSE", "--level", "upper", "--keyword", "artificial intelligence",
                             "--min-credits", "3", "--max-credits", "3")
        self.assertEqual(result["results"][0]["course"], "CSE 450")

    def test_discovery_initially_shows_distinct_courses(self):
        result = self.search("--subject", "CSE")
        self.assertEqual(result["matched_sections"], 4)
        self.assertEqual(len({s["course"] for s in result["results"]}), 2)

    def test_live_keyword_uses_supported_plural_parameter(self):
        # Live ASU ignores singular 'keyword' and returns unrelated subject results.
        client = Mock()
        client.search.return_value = ([], {"fetched": 0, "total": 0, "pages": 1, "complete": True})
        args = parser().parse_args(["search", "--term", "Spring 2027", "--subject", "CSE",
                                    "--keyword", "artificial intelligence"])
        with patch("registration.ASUClient", return_value=client):
            search_sections(args)
        params = client.search.call_args.args[0]
        self.assertEqual(params["keywords"], "artificial intelligence")
        self.assertNotIn("keyword", params)

    def test_open_only_excludes_closed_and_unknown_seats(self):
        result = self.search("--subject", "CSE", "--level", "upper", "--open-only")
        self.assertEqual(result["status"], "no_results")

    def test_exact_course_is_not_a_prefix_match(self):
        result = self.search("--subject", "CSE", "--course-number", "241")
        self.assertEqual(result["status"], "no_results")

    def test_time_conflicts_excluded_without_hiding_unknowns(self):
        result = self.search("--subject", "CSE", "--course-number", "240", "--after", "10:00")
        self.assertEqual(result["excluded_by_time_preferences"], 1)
        self.assertEqual(result["matched_sections"], 2)
        self.assertTrue(all(s["preference_check"]["status"] == "unknown" for s in result["results"]))
        self.assertFalse(result["calendar_checked"])

    def test_catalog_systems_not_conflated(self):
        self.assertEqual(self.search("--designation", "gold:SCIT")["matched_sections"], 1)
        self.assertEqual(self.search("--designation", "maroon:SCIT")["matched_sections"], 0)

    def test_samples_do_not_write_student_state(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.json"
            path.write_text("original")
            with self.assertRaises(ValueError):
                self.search("--save", str(path))
            self.assertEqual(path.read_text(), "original")

    def test_live_search_requires_explicit_semester_and_scope(self):
        for args in (["search", "--subject", "CSE"], ["search", "--term", "Spring 2027"]):
            with self.subTest(args=args), self.assertRaises(ValueError):
                search_sections(parser().parse_args(args))

    def test_invalid_filter_combinations_fail_before_network(self):
        for flags in (("--after", "17:00", "--before", "10:00"), ("--min-credits", "nan"),
                      ("--min-credits", "5", "--max-credits", "3"), ("--designation", "HU"),
                      ("--days", "nonsense"), ("--course-number", "240")):
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                self.search(*flags)

    def test_cache_is_private_and_paging_keeps_original_timestamp(self):
        result = self.search("--subject", "CSE", "--course-number", "240")
        result["checked_at"] = "2026-10-24T00:00:00+00:00"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "cache.json"
            save_json(path, {"format": "asu-registration-search-v1", "metadata": result,
                             "display": result["results"], "sections": result["results"]})
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(["page", "--file", str(path), "--offset", "1", "--limit", "1"])
            data = json.loads(output.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(data["checked_at"], result["checked_at"])
            self.assertEqual(data["returned"], 1)
            self.assertTrue(data["cached"])


class EvidenceTests(unittest.TestCase):
    def test_unrelated_fallback_profile_never_wins(self):
        result = professor_evidence(SampleRMP(), "Alex Example", "CSE 240")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["professor"]["teacher_id"], "SAMPLE-TEACHER")
        self.assertEqual(result["statistics"]["scope"], "overall_professor")

    def test_course_reviews_and_general_reviews_are_separate(self):
        result = professor_evidence(SampleRMP(), "Alex Example", "CSE-240")
        self.assertEqual(result["course_matches_in_fetched_pages"], 1)
        self.assertEqual(result["course_reviews"][0]["course"], "CSE240")
        self.assertEqual(result["general_reviews"][0]["course"], "CSE450")
        self.assertFalse(result["review_pages_complete"])

    def test_no_course_reviews_does_not_mean_no_professor_reviews(self):
        result = professor_evidence(SampleRMP(), "Alex Example", "CSE 999")
        self.assertEqual(result["course_reviews"], [])
        self.assertEqual(len(result["general_reviews"]), 2)
        self.assertIn("fetched pages", " ".join(result["caveats"]))

    def test_partial_name_requires_confirmation(self):
        result = professor_evidence(SampleRMP(), "Alex", "CSE240")
        self.assertEqual(result["status"], "needs_confirmation")
        self.assertNotIn("statistics", result)

    def test_duplicate_exact_names_require_confirmation(self):
        client = SampleRMP()
        second = deepcopy(client.data["professors"][0])
        second["id"] = "SAMPLE-SAME-NAME"
        client.data["professors"].append(second)
        self.assertEqual(professor_evidence(client, "Alex Example")["status"], "needs_confirmation")

    def test_wrong_school_identity_is_rejected(self):
        client = SampleRMP()
        client.data["professors"][0]["school"]["id"] = "UNRELATED-SCHOOL"
        result = professor_evidence(client, "Alex Example")
        self.assertNotEqual(result["status"], "matched")

    def test_review_service_failure_retains_aggregate_evidence(self):
        client = SampleRMP()
        client.reviews = Mock(side_effect=SourceError("service unavailable"))
        result = professor_evidence(client, "Alex Example", "CSE240")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["reviews_status"], "unavailable")
        self.assertEqual(result["statistics"]["rating_count"], 20)
        self.assertEqual(result["course_reviews"], [])

    def test_absent_statistics_are_unknown_not_zero_or_bad_ratings(self):
        client = SampleRMP()
        client.data["professors"][0].update({"numRatings": 0, "avgRating": 0, "wouldTakeAgainPercent": -1})
        result = professor_evidence(client, "Alex Example")
        self.assertIsNone(result["statistics"]["rating"])
        self.assertIsNone(result["statistics"]["would_take_again_percent"])

    def test_all_school_search_failures_are_errors_not_no_results(self):
        client = SampleRMP()
        client.professors = Mock(side_effect=SourceError("failed"))
        with self.assertRaises(SourceError):
            professor_evidence(client, "Alex Example")


class SourceTests(unittest.TestCase):
    def client(self):
        value = object.__new__(ASUClient)
        value.session = Mock()
        return value

    def test_scroll_ids_can_stay_constant_while_pages_advance(self):
        base = fixture()["classes"][:3]
        pages = [{"classes": [r], "total": {"value": 3, "relation": "eq"}, "scrollId": "stable"} for r in base]
        with patch("sources.request_json", side_effect=pages) as fetch:
            rows, coverage = self.client().search({"term": "2271"}, 3)
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(len(rows), 3)
        self.assertTrue(coverage["complete"])

    def test_repeated_pages_do_not_loop_forever(self):
        page = {"classes": fixture()["classes"][:1], "total": {"value": 20, "relation": "eq"}, "scrollId": "stable"}
        with patch("sources.request_json", return_value=page) as fetch:
            rows, coverage = self.client().search({"term": "2271"}, 5)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(len(rows), 1)
        self.assertFalse(coverage["complete"])

    def test_page_cap_reports_incomplete_scope(self):
        page = {"classes": fixture()["classes"][:1], "total": {"value": 10000, "relation": "gte"}, "scrollId": "more"}
        with patch("sources.request_json", return_value=page):
            _, coverage = self.client().search({"term": "2271"}, 1)
        self.assertFalse(coverage["complete"])
        self.assertEqual(coverage["total_relation"], "gte")

    def test_source_schema_failure_is_not_an_empty_success(self):
        with patch("sources.request_json", return_value={"unexpected": []}), self.assertRaises(SourceError):
            self.client().search({"term": "2271"})

    def test_graphql_errors_are_not_converted_to_empty_reviews(self):
        session = Mock()
        session.request.return_value.json.return_value = {"errors": [{"message": "sensitive upstream text"}]}
        with self.assertRaises(SourceError) as raised:
            request_json(session, "POST", "https://example.invalid", "RMP")
        self.assertNotIn("sensitive", str(raised.exception))

    def test_http_errors_do_not_expose_request_details(self):
        import requests
        session = Mock()
        response = Mock(status_code=429)
        session.request.side_effect = requests.HTTPError("secret URL details", response=response)
        with self.assertRaises(SourceError) as raised:
            request_json(session, "GET", "https://example.invalid", "ASU")
        self.assertIn("429", str(raised.exception))
        self.assertNotIn("secret", str(raised.exception))


class OutputTests(unittest.TestCase):
    def test_size_limit_preserves_json_and_complete_records(self):
        output = io.StringIO()
        data = {"results": [{"meetings": [{"start": "09:00", "end": "10:00"}], "note": "x" * 3000} for _ in range(4)], "offset": 2}
        with redirect_stdout(output):
            code = emit(data)
        value = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertLess(len(output.getvalue()), 8000)
        self.assertTrue(value["output_limited"])
        self.assertEqual(value["next_offset"], 2 + len(value["results"]))
        self.assertEqual(len(value["results"][0]["note"]), 3000)

    def test_single_huge_record_returns_actionable_error(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = emit({"results": [{"note": "x" * 10000}]})
        self.assertEqual(code, 5)
        self.assertEqual(json.loads(output.getvalue())["status"], "output_too_large")

    def test_invalid_cli_input_is_json_and_nonzero(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["search", "--sample", "--max-pages", "100"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
