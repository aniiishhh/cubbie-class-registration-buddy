"""Regression coverage for the legacy ASU URLs that loaded indefinitely."""
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "asu-registration-buddy" / "scripts"))
from catalog import class_search_url, normalize
from registration import fixture


class ASULinkTests(unittest.TestCase):
    def test_uses_current_asu_query_names(self):
        parts = urlsplit(class_search_url("2271", "CSE", "575"))
        query = parse_qs(parts.query)
        self.assertEqual(parts.netloc, "catalog.apps.asu.edu")
        self.assertEqual(parts.path, "/catalog/classes/classlist")
        self.assertEqual(query["term"], ["2271"])
        self.assertEqual(query["subject"], ["CSE"])
        self.assertEqual(query["catalogNbr"], ["575"])
        self.assertEqual(query["honors"], ["F"])
        self.assertEqual(query["searchType"], ["all"])
        self.assertFalse({"t", "s", "n", "hon", "e"} & query.keys())

    def test_section_fragment_matches_asu_ui(self):
        url = class_search_url("Spring 2027", "CSE", "575", "14703", "125131")
        self.assertEqual(urlsplit(url).fragment, "detailsOpen=14703-125131")

    def test_online_program_is_preserved(self):
        query = parse_qs(urlsplit(class_search_url("2271", "CSE", "575", population="asu-online")).query)
        self.assertEqual(query["campusOrOnlineSelection"], ["O"])

    def test_missing_or_untrusted_identifiers_get_a_course_search_link(self):
        for class_number, course_id in [(None, None), ("SAMPLE-101", "SAMPLE-C240"), ("1#other", "125131")]:
            self.assertEqual(urlsplit(class_search_url("2271", "CSE", "240", class_number, course_id)).fragment, "")

    def test_invalid_course_or_term_gets_the_official_landing_page(self):
        for values in [("next semester", "CSE", "575"), ("2271", "", "575"), ("2271", "CSE", "unknown")]:
            self.assertEqual(class_search_url(*values), "https://catalog.apps.asu.edu/catalog/classes")

    def test_normalized_results_include_section_and_course_links(self):
        raw = fixture()["classes"][0]
        raw["CLAS"].update({"CLASSNBR": "14703", "CRSEID": "125131"})
        section = normalize(raw)
        self.assertEqual(urlsplit(section["asu_url"]).fragment, "detailsOpen=14703-125131")
        self.assertEqual(urlsplit(section["asu_search_url"]).fragment, "")


if __name__ == "__main__":
    unittest.main()
