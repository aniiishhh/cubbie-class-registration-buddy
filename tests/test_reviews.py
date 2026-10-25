"""Full-history RMP retrieval and full-text paging, without live requests."""
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'asu-registration-buddy' / 'scripts'))
from professors import professor_evidence, summarize_corpus
from registration import SampleRMP, main, save_json
from sources import RMPClient, SourceError


def response(ids, more=False, cursor='next', total=4):
    return {'node': {'numRatings': total, 'ratings': {
        'edges': [{'node': {'id': value, 'comment': value}} for value in ids],
        'pageInfo': {'hasNextPage': more, 'endCursor': cursor}}}}


class ReviewPaginationTests(unittest.TestCase):
    def client(self, responses):
        client = object.__new__(RMPClient)
        client.graphql = Mock(side_effect=responses)
        return client

    def test_fetches_until_exhausted_and_follows_cursor(self):
        client = self.client([response(['1', '2'], True), response(['3', '4'])])
        rows, complete = client.reviews('teacher')
        self.assertTrue(complete)
        self.assertEqual([r['id'] for r in rows], ['1', '2', '3', '4'])
        self.assertEqual(client.graphql.call_args_list[1].args[1]['cursor'], 'next')
        self.assertEqual(client.last_review_coverage['pages_fetched'], 2)
        self.assertEqual(client.last_review_coverage['reported_total'], 4)
        self.assertEqual(client.last_review_coverage['stop_reason'], 'complete')

    def test_page_cap_does_not_claim_completeness(self):
        client = self.client([response(['1'], True)])
        rows, complete = client.reviews('teacher', max_pages=1)
        self.assertEqual(len(rows), 1)
        self.assertFalse(complete)
        self.assertEqual(client.last_review_coverage['stop_reason'], 'page_limit')

    def test_time_budget_preserves_fetched_pages(self):
        client = self.client([response(['1'], True)])
        with patch('sources.time.monotonic', side_effect=[0, 0, 61, 61]):
            rows, complete = client.reviews('teacher', time_budget=60)
        self.assertEqual(len(rows), 1)
        self.assertFalse(complete)
        self.assertEqual(client.graphql.call_count, 1)
        self.assertEqual(client.last_review_coverage['stop_reason'], 'time_budget')

    def test_repeating_cursor_stops_without_infinite_requests(self):
        client = self.client([response(['1'], True), response(['2'], True)])
        rows, complete = client.reviews('teacher')
        self.assertFalse(complete)
        self.assertEqual(len(rows), 2)
        self.assertEqual(client.last_review_coverage['stop_reason'], 'pagination_stalled')

    def test_later_source_failure_retains_partial_reviews(self):
        client = self.client([response(['1'], True), SourceError('unavailable')])
        rows, complete = client.reviews('teacher')
        self.assertEqual(len(rows), 1)
        self.assertFalse(complete)
        self.assertEqual(client.last_review_coverage['stop_reason'], 'source_error')

    def test_first_source_failure_is_not_empty_success(self):
        client = self.client([SourceError('unavailable')])
        with self.assertRaises(SourceError):
            client.reviews('teacher')

    def test_malformed_later_page_retains_only_valid_pages(self):
        malformed = response(['2'])
        malformed['node']['ratings']['pageInfo'] = None
        client = self.client([response(['1'], True), malformed])
        rows, complete = client.reviews('teacher')
        self.assertEqual([r['id'] for r in rows], ['1'])
        self.assertFalse(complete)
        self.assertEqual(client.last_review_coverage['stop_reason'], 'format_error')


class CorpusTests(unittest.TestCase):
    def test_corpus_retains_full_text_and_deduplicates_review_ids(self):
        client = SampleRMP()
        rows = deepcopy(client.data['reviews'])
        rows[0].update({'id': 'first', 'comment': 'full text ' * 150})
        client.reviews = Mock(return_value=([*rows, deepcopy(rows[0])], True))
        client.last_review_coverage = {'reported_total': 99, 'complete': True}
        result = professor_evidence(client, 'Alex Example', 'CSE240', max_reviews=1,
                                    review_pages=70, include_corpus=True)
        self.assertEqual(result['reviews_fetched'], len(rows))
        self.assertEqual(result['corpus_summary']['reviews_counted'], len(rows))
        corpus = result['review_corpus']
        first = next(r for r in corpus['reviews'] if r['id'] == 'first')
        self.assertEqual(first['comment'], rows[0]['comment'].strip())
        self.assertGreater(len(first['comment']), 450)
        self.assertLessEqual(len(result['course_reviews'][0]['excerpt']), 450)
        self.assertIn('differs', ' '.join(result['caveats']))
        client.reviews.assert_called_once_with('SAMPLE-TEACHER', max_pages=70)

    def test_aggregates_cover_all_reviews_not_only_overview_excerpts(self):
        rows = [{'class': 'CSE240' if i % 2 else 'CSE450', 'date': f'2026-01-{i+1:02}',
                 'ratingTags': 'Tough grader--Clear lectures', 'clarityRating': 4,
                 'difficultyRating': 3} for i in range(20)]
        summary = summarize_corpus(rows)
        self.assertEqual(summary['reviews_counted'], 20)
        self.assertEqual(summary['top_course_counts'], {'CSE450': 10, 'CSE240': 10})
        self.assertEqual(summary['tag_counts']['Tough grader'], 20)
        self.assertEqual(summary['date_range'], ['2026-01-01', '2026-01-20'])

    def test_review_cli_writes_private_corpus_and_removes_it_from_overview(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'reviews.json'
            output = io.StringIO()
            with patch('registration.RMPClient', return_value=SampleRMP()), redirect_stdout(output):
                code = main(['professor', '--name', 'Alex Example', '--save-reviews', str(path)])
            self.assertEqual(code, 0)
            overview = json.loads(output.getvalue())
            corpus = json.loads(path.read_text())
            self.assertNotIn('review_corpus', overview)
            self.assertEqual(overview['reviews_file'], str(path))
            self.assertIsNotNone(corpus['checked_at'])
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_batch_reading_covers_all_text_without_cutting_records(self):
        comments = [f'Review {i}: ' + 'evidence ' * 300 for i in range(12)]
        corpus = {'format': 'classcue-rmp-reviews-v1', 'professor': {'name': 'Example'},
                  'coverage': {'pagination_complete': True}, 'checked_at': 'original',
                  'reviews': [{'id': str(i), 'comment': comment} for i, comment in enumerate(comments)]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'corpus.json'
            save_json(path, corpus)
            offset, read = 0, []
            while offset < len(comments):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = main(['review-page', '--file', str(path), '--offset', str(offset), '--limit', '10'])
                self.assertEqual(code, 0)
                self.assertLessEqual(len(output.getvalue().strip()), 7800)
                page = json.loads(output.getvalue())
                self.assertEqual(page['checked_at'], 'original')
                self.assertGreater(page['next_offset'], offset)
                read.extend(r['comment'] for r in page['results'])
                offset = page['next_offset']
            self.assertEqual(read, comments)

    def test_sample_cannot_create_a_review_corpus(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'corpus.json'
            with redirect_stdout(io.StringIO()):
                code = main(['professor', '--sample', '--save-reviews', str(path)])
            self.assertEqual(code, 2)
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
