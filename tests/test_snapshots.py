"""Regression checks for access-denied recovery without false live-data claims."""
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
import json
import tempfile
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "asu-registration-buddy" / "scripts"))
from registration import fixture, main, parser, search_sections
from snapshots import FORMAT, CacheMiss, build_snapshot, load_snapshot, read_snapshot, write_snapshot
from sources import SourceError


def snapshot():
    records = fixture()["classes"][:4]
    return {"format": FORMAT, "source_checked_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "query": {"term": "2271", "subject": "CSE", "campusOrOnlineSelection": "A", "searchType": "all"},
            "source_url": "https://example.invalid/public-catalog", "coverage": {"complete": True, "fetched": 4, "total": 4},
            "classes": records}


class SnapshotTests(unittest.TestCase):
    def search(self, data, *flags):
        args = parser().parse_args(["search", "--cached", "--term", "Spring 2027", "--subject", "CSE", *flags])
        with patch("registration.load_snapshot", return_value=data), patch("registration.ASUClient") as client:
            result = search_sections(args)
            client.assert_not_called()
        return result

    def test_cached_lookup_is_never_marked_live_or_sample(self):
        data = snapshot()
        result = self.search(data, "--course-number", "240")
        self.assertEqual(result["data_mode"], "cached")
        self.assertFalse(result["live_availability_verified"])
        self.assertFalse(result["sample"])
        self.assertIsNone(result["checked_at"])
        self.assertEqual(result["source_checked_at"], data["source_checked_at"])
        self.assertEqual(result["matched_sections"], 3)

    def test_snapshot_for_another_subject_is_not_an_empty_success(self):
        with self.assertRaises(CacheMiss):
            read_snapshot(snapshot(), "2271", "MAT")

    def test_snapshot_for_another_term_is_not_an_empty_success(self):
        with self.assertRaises(CacheMiss):
            read_snapshot(snapshot(), "2267", "CSE")

    def test_missing_subject_does_not_imply_all_asu_is_cached(self):
        with self.assertRaises(CacheMiss):
            read_snapshot(snapshot(), "2271", None)

    def test_absent_course_is_a_valid_result_with_timestamp_and_scope(self):
        result = self.search(snapshot(), "--course-number", "512")
        self.assertEqual(result["status"], "no_results")
        self.assertEqual(result["snapshot_scope"]["subject"], "CSE")
        self.assertIn("source_checked_at", result)
        self.assertFalse(result["live_availability_verified"])

    def test_cached_keywords_are_filtered_locally(self):
        result = self.search(snapshot(), "--keyword", "artificial intelligence")
        self.assertEqual(result["matched_sections"], 1)
        self.assertEqual(result["results"][0]["course"], "CSE 450")

    def test_historical_open_seats_have_an_explicit_caveat(self):
        result = self.search(snapshot(), "--course-number", "240", "--open-only")
        self.assertIn("historical snapshot seat counts", " ".join(result["caveats"]))
        self.assertFalse(result["live_availability_verified"])

    def test_old_snapshot_is_marked_stale(self):
        data = snapshot()
        data["source_checked_at"] = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        self.assertTrue(self.search(data)["cache_stale"])

    def test_future_or_naive_timestamps_are_rejected(self):
        for value in ((datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), "2026-10-24T12:00:00"):
            data = snapshot()
            data["source_checked_at"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                read_snapshot(data, "2271", "CSE")

    def test_records_outside_declared_scope_are_rejected(self):
        data = snapshot()
        data["classes"][0]["CLAS"]["STRM"] = "2267"
        with self.assertRaises(ValueError):
            read_snapshot(data, "2271", "CSE")

    def test_incomplete_refresh_cannot_replace_snapshot(self):
        client = Mock()
        client.search.return_value = (fixture()["classes"][:4], {"complete": False})
        with self.assertRaises(SourceError):
            build_snapshot(client, "2271", "CSE")

    def test_refresh_preserves_all_meeting_rows_but_excludes_unneeded_source_fields(self):
        client = Mock()
        records = deepcopy(fixture()["classes"][:4])
        records[0]["CLAS"]["UNNEEDED_FIELD"] = "discard"
        client.search.return_value = (records, {"complete": True, "total": 4})
        data = build_snapshot(client, "2271", "CSE")
        self.assertEqual(len(data["classes"][0]["CLAS"]["MEETINGDATES"]), 2)
        self.assertNotIn("UNNEEDED_FIELD", data["classes"][0]["CLAS"])

    def test_403_is_structured_and_does_not_silently_use_a_snapshot(self):
        client = Mock()
        client.search.side_effect = SourceError("ASU blocked", service="ASU Class Search", http_status=403)
        output = io.StringIO()
        with patch("registration.ASUClient", return_value=client), redirect_stdout(output):
            code = main(["search", "--term", "Spring 2027", "--subject", "CSE"])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 3)
        self.assertEqual(result["http_status"], 403)
        self.assertIn("--cached", result["next_step"])
        self.assertEqual(client.search.call_count, 1)

    def test_full_semester_snapshot_supports_other_subjects(self):
        data = snapshot()
        del data["query"]["subject"]
        data["classes"].extend(fixture()["classes"][4:])
        args = parser().parse_args(["search", "--cached", "--term", "Spring 2027", "--subject", "BIO"])
        with patch("registration.load_snapshot", return_value=data):
            result = search_sections(args)
        self.assertTrue(result["all_subjects"])
        self.assertEqual(result["snapshot_subject_count"], 2)
        self.assertEqual(result["matched_sections"], 1)
        self.assertEqual(result["results"][0]["course"], "BIO 181")

    def test_full_snapshot_allows_discovery_without_a_subject(self):
        data = snapshot()
        del data["query"]["subject"]
        args = parser().parse_args(["search", "--cached", "--term", "Spring 2027", "--keyword", "intelligence"])
        with patch("registration.load_snapshot", return_value=data):
            result = search_sections(args)
        self.assertEqual(result["results"][0]["course"], "CSE 450")

    def test_full_snapshot_still_rejects_a_different_semester(self):
        data = snapshot()
        del data["query"]["subject"]
        with self.assertRaises(CacheMiss):
            read_snapshot(data, "2267", "BIO")

    def test_compressed_snapshot_round_trip(self):
        data = snapshot()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalog.json.gz"
            write_snapshot(path, data)
            self.assertEqual(load_snapshot(path), data)
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_corrupt_compressed_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalog.json.gz"
            path.write_bytes(b"not gzip")
            with self.assertRaises(OSError):
                load_snapshot(path)

    def test_whole_semester_refresh_preserves_other_subjects(self):
        client = Mock()
        records = fixture()["classes"]
        client.search.return_value = (records, {"complete": True, "total": len(records)})
        data = build_snapshot(client, "2271")
        self.assertNotIn("subject", data["query"])
        self.assertEqual({r["CLAS"]["SUBJECT"] for r in data["classes"]}, {"CSE", "BIO"})

    def test_only_explicit_challenge_header_identifies_browser_challenge(self):
        for headers, expected in [({"server": "cloudflare"}, "access_denied"),
                                  ({"server": "cloudflare", "cf-mitigated": "challenge"}, "browser_challenge")]:
            client = Mock()
            client.search.side_effect = SourceError("Denied", service="ASU", http_status=403, response_headers=headers)
            output = io.StringIO()
            with patch("registration.ASUClient", return_value=client), redirect_stdout(output):
                code = main(["search", "--term", "Spring 2027", "--subject", "CSE"])
            result = json.loads(output.getvalue())
            self.assertEqual(code, 3)
            self.assertEqual(result["error_code"], expected)
            self.assertIn("--cached", result["next_step"])

    def test_failed_atomic_write_preserves_previous_export(self):
        original = snapshot()
        changed = deepcopy(original)
        changed["source_checked_at"] = datetime.now(timezone.utc).isoformat()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalog.json.gz"
            write_snapshot(path, original)
            with patch("snapshots.os.replace", side_effect=OSError("simulated write failure")), self.assertRaises(OSError):
                write_snapshot(path, changed)
            self.assertEqual(load_snapshot(path), original)
            self.assertEqual(list(Path(folder).iterdir()), [path])


if __name__ == "__main__":
    unittest.main()
