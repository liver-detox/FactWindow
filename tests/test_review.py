from __future__ import annotations

import copy
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone

from factwindow.core import (
    FactWindowError, compare_facts, freeze_before, render_markdown, verify_snapshot,
)
from tests.test_compare import after_event, frozen_event
from tests.test_freeze import before_event


FROZEN = datetime(2040, 1, 14, 12, tzinfo=timezone.utc)
EVENT = datetime(2040, 1, 15, 13, tzinfo=timezone.utc)
GENERATED = datetime(2040, 1, 15, 14, tzinfo=timezone.utc)


def rehash(snapshot: dict) -> dict:
    payload = {key: value for key, value in snapshot.items() if key != 'content_sha256'}
    snapshot['content_sha256'] = hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False,
    ).encode('utf-8')).hexdigest()
    return snapshot


def review_snapshot() -> dict:
    before = before_event()
    before.update(
        questions=[{'id': 'coverage', 'text': 'Which regions are supported?'},
                   {'id': 'retention', 'text': 'Was retention disclosed?'}],
        supports_if='Adoption grows with disclosed retention.',
        refutes_if='The launch is cancelled.',
        review_by='2040-01-16T13:00:00+00:00',
    )
    return freeze_before(before, now=FROZEN)


def answer(status: str = 'answered') -> dict:
    return {
        'question_id': 'coverage', 'status': status, 'reason': 'The release names six regions.',
        'sources': [{'source_url': 'https://example.com/regions',
                     'published_at': '2040-01-15T13:05:00+00:00'}],
    }


class EvidenceWindowTests(unittest.TestCase):
    def test_future_fact_is_rejected_with_actionable_chinese_error(self) -> None:
        after = after_event()
        after['facts'][0]['published_at'] = '2040-01-15T14:00:01+00:00'
        with self.assertRaisesRegex(FactWindowError, '发布时间.*报告生成时间'):
            compare_facts(frozen_event(), after, generated_at=GENERATED)

    def test_empty_report_before_event_is_rejected(self) -> None:
        with self.assertRaisesRegex(FactWindowError, '事件.*尚未发生'):
            compare_facts(frozen_event(), {'event_id': 'EVT-DEMO-001', 'facts': []},
                          generated_at=EVENT - timedelta(seconds=1))

    def test_empty_report_at_event_preserves_missing_facts_and_questions(self) -> None:
        report = compare_facts(review_snapshot(), {'event_id': 'EVT-DEMO-001', 'facts': []},
                               generated_at=EVENT)
        self.assertEqual(report['rows'][0]['status'], 'missing')
        self.assertEqual([item['status'] for item in report['questions']], ['pending', 'pending'])
        self.assertIn('Regional mix is not yet disclosed.', report['unresolved'])

    def test_facts_list_must_be_explicit(self) -> None:
        for bad in [None, {}, '']:
            with self.subTest(bad=bad), self.assertRaisesRegex(FactWindowError, 'facts.*列表'):
                compare_facts(frozen_event(), {'event_id': 'EVT-DEMO-001', 'facts': bad},
                              generated_at=GENERATED)

    def test_same_instant_boundaries_accept_different_timezones(self) -> None:
        after = after_event()
        after['facts'][0]['published_at'] = '2040-01-15T21:00:00+08:00'
        report = compare_facts(frozen_event(), after, generated_at=EVENT)
        self.assertEqual(report['rows'][0]['status'], 'above')
        after['facts'][0]['published_at'] = '2040-01-15T09:00:00-05:00'
        self.assertEqual(compare_facts(frozen_event(), after, generated_at=GENERATED)
                         ['rows'][0]['difference'], 12)

    def test_equivalent_timezone_before_event_is_rejected(self) -> None:
        after = after_event()
        after['facts'][0]['published_at'] = '2040-01-15T20:59:59+08:00'
        with self.assertRaisesRegex(FactWindowError, 'published_at.*event'):
            compare_facts(frozen_event(), after, generated_at=GENERATED)

    def test_v1_snapshot_is_read_without_migrating_or_rehashing_it(self) -> None:
        snapshot = frozen_event()
        snapshot['schema_version'] = 'factwindow.snapshot.v1'
        snapshot['event'].pop('questions', None)
        rehash(snapshot)
        saved = copy.deepcopy(snapshot)
        self.assertIs(verify_snapshot(snapshot), snapshot)
        report = compare_facts(snapshot, after_event(), generated_at=GENERATED)
        self.assertEqual(snapshot, saved)
        self.assertEqual(report['schema_version'], 'factwindow.report.v2')
        self.assertEqual(report['snapshot_sha256'], snapshot['content_sha256'])

    def test_rehashed_snapshot_with_invalid_freeze_time_is_rejected(self) -> None:
        for schema in ['factwindow.snapshot.v1', 'factwindow.snapshot.v2']:
            for time in [EVENT, GENERATED]:
                with self.subTest(schema=schema, time=time):
                    snapshot = frozen_event()
                    snapshot.update(schema_version=schema, frozen_at=time.isoformat())
                    rehash(snapshot)
                    with self.assertRaisesRegex(FactWindowError, '冻结时间.*事件时间'):
                        verify_snapshot(snapshot)

    def test_sources_show_publication_times_and_snapshot_limits(self) -> None:
        report = compare_facts(review_snapshot(), after_event(), generated_at=GENERATED)
        markdown = render_markdown(report)
        self.assertIn(report['snapshot_sha256'], markdown)
        self.assertIn('2040-01-15T13:05:00+00:00', markdown)
        self.assertIn('不能证明', markdown)
        self.assertIn('事前', markdown)
        self.assertIn('来源', markdown)


class ComparisonSafetyTests(unittest.TestCase):
    def test_unrepresentable_difference_has_metric_and_corrective_guidance(self) -> None:
        for expected, actual in [(-1e308, 1e308), (10 ** 1000, 1.0)]:
            with self.subTest(expected_type=type(expected).__name__):
                before = before_event()
                after = after_event()
                before['expectations'][0]['expected'] = expected
                after['facts'][0]['actual'] = actual
                with self.assertRaisesRegex(FactWindowError, 'active_teams.*数值范围.*单位'):
                    compare_facts(freeze_before(before, now=FROZEN), after,
                                  generated_at=GENERATED)

    def test_malformed_https_hosts_have_source_field_error(self) -> None:
        for url in ['https://[invalid', 'https://[::gg]']:
            with self.subTest(url=url):
                before = before_event()
                before['expectations'][0]['source_url'] = url
                with self.assertRaisesRegex(FactWindowError, 'source_url.*来源链接'):
                    freeze_before(before, now=FROZEN)
                after = after_event()
                after['facts'][0]['source_url'] = url
                with self.assertRaisesRegex(FactWindowError, 'source_url.*来源链接'):
                    compare_facts(frozen_event(), after, generated_at=GENERATED)

    def test_one_missing_unit_never_produces_a_difference(self) -> None:
        for missing_side in ['expectation', 'fact']:
            with self.subTest(side=missing_side):
                before = before_event()
                after = after_event()
                if missing_side == 'expectation':
                    before['expectations'][0].pop('unit')
                else:
                    after['facts'][0].pop('unit')
                row = compare_facts(freeze_before(before, now=FROZEN), after,
                                    generated_at=GENERATED)['rows'][0]
                self.assertEqual(row['status'], 'unit_unconfirmed')
                self.assertIsNone(row['difference'])
                self.assertIsNone(row[f'{missing_side}_unit'])
                self.assertIsNone(row['unit'])

    def test_both_units_missing_still_allows_numeric_comparison(self) -> None:
        before = before_event()
        after = after_event()
        before['expectations'][0].pop('unit')
        after['facts'][0].pop('unit')
        row = compare_facts(freeze_before(before, now=FROZEN), after,
                            generated_at=GENERATED)['rows'][0]
        self.assertEqual(row['status'], 'above')
        self.assertEqual(row['difference'], 12)

    def test_incompatible_types_are_visible_and_unresolved(self) -> None:
        for expected, actual in [(100, '100'), ('100', 100), (False, 0), (True, 'true')]:
            with self.subTest(expected=expected, actual=actual):
                before = before_event()
                after = after_event()
                before['expectations'][0]['expected'] = expected
                after['facts'][0]['actual'] = actual
                report = compare_facts(freeze_before(before, now=FROZEN), after,
                                       generated_at=GENERATED)
                row = report['rows'][0]
                self.assertEqual(row['status'], 'type_mismatch')
                self.assertIsNone(row['difference'])
                self.assertEqual(row['expected'], expected)
                self.assertEqual(row['actual'], actual)
                self.assertTrue(any('类型不一致' in item for item in report['unresolved']))

    def test_int_and_float_are_compatible(self) -> None:
        after = after_event()
        after['facts'][0]['actual'] = 100.0
        row = compare_facts(frozen_event(), after, generated_at=GENERATED)['rows'][0]
        self.assertEqual(row['status'], 'matched')
        self.assertEqual(row['difference'], 0)

    def test_conflicting_units_are_preserved_in_json_and_markdown(self) -> None:
        after = after_event()
        after['facts'][0]['unit'] = 'users'
        report = compare_facts(frozen_event(), after, generated_at=GENERATED)
        row = report['rows'][0]
        self.assertEqual((row['expectation_unit'], row['fact_unit']), ('teams', 'users'))
        self.assertIsNone(row['unit'])
        self.assertIn('预期单位', render_markdown(report))
        self.assertIn('事实单位', render_markdown(report))


class QuestionReviewTests(unittest.TestCase):
    def test_before_judgment_criteria_are_frozen_and_reported(self) -> None:
        snapshot = review_snapshot()
        self.assertEqual(snapshot['schema_version'], 'factwindow.snapshot.v2')
        report = compare_facts(snapshot, after_event(), generated_at=GENERATED)
        for field in ['supports_if', 'refutes_if', 'review_by']:
            self.assertEqual(report[field], snapshot['event'][field])
            self.assertIn(report[field], render_markdown(report))

    def test_review_by_cannot_precede_event_and_must_have_timezone(self) -> None:
        for invalid in ['2040-01-15T12:59:59+00:00', '2040-01-16T13:00:00', '', 5]:
            with self.subTest(invalid=invalid):
                before = before_event()
                before['review_by'] = invalid
                with self.assertRaisesRegex(FactWindowError, 'review_by'):
                    freeze_before(before, now=FROZEN)
        before = before_event()
        before['review_by'] = '2040-01-15T21:00:00+08:00'
        self.assertIn('review_by', freeze_before(before, now=FROZEN)['event'])

    def test_questions_require_unique_ids_and_nonempty_text(self) -> None:
        for questions in [None, ['x'], [{'id': 'a', 'text': ''}],
                          [{'id': 'a', 'text': 'x'}, {'id': ' a ', 'text': 'y'}]]:
            with self.subTest(questions=questions):
                before = before_event()
                before['questions'] = questions
                with self.assertRaisesRegex(FactWindowError, 'questions'):
                    freeze_before(before, now=FROZEN)

    def test_answered_question_closes_only_itself_and_preserves_original(self) -> None:
        snapshot = review_snapshot()
        original = copy.deepcopy(snapshot)
        after = after_event()
        after['answers'] = [answer()]
        report = compare_facts(snapshot, after, generated_at=GENERATED)
        coverage, retention = report['questions']
        self.assertEqual(coverage['text'], snapshot['event']['questions'][0]['text'])
        self.assertEqual(coverage['status'], 'answered')
        self.assertEqual(retention['status'], 'pending')
        self.assertFalse(any('Which regions' in item for item in report['unresolved']))
        self.assertTrue(any('Was retention disclosed?' in item for item in report['unresolved']))
        self.assertIn('Regional mix is not yet disclosed.', report['unresolved'])
        self.assertEqual(snapshot, original)
        markdown = render_markdown(report)
        self.assertIn('https://example.com/regions', markdown)
        self.assertIn('The release names six regions.', markdown)

    def test_pending_and_conflicting_answers_stay_unresolved(self) -> None:
        for status in ['pending', 'conflicting']:
            with self.subTest(status=status):
                after = after_event()
                after['answers'] = [answer(status)]
                report = compare_facts(review_snapshot(), after, generated_at=GENERATED)
                self.assertTrue(any('Which regions' in item for item in report['unresolved']))
                self.assertEqual(report['questions'][0]['status'], status)

    def test_answers_must_reference_unique_frozen_question_ids(self) -> None:
        unknown = answer()
        unknown['question_id'] = 'not-frozen'
        for answers in [[unknown], [answer(), answer()]]:
            with self.subTest(answers=answers):
                after = after_event()
                after['answers'] = answers
                with self.assertRaisesRegex(FactWindowError, 'question_id'):
                    compare_facts(review_snapshot(), after, generated_at=GENERATED)

    def test_answer_validation_preserves_evidence_requirements(self) -> None:
        for changes, field in [({'status': 'closed'}, 'status'), ({'reason': ''}, 'reason'),
                               ({'sources': []}, 'sources'), ({'sources': None}, 'sources')]:
            with self.subTest(changes=changes):
                after = after_event()
                after['answers'] = [dict(answer(), **changes)]
                with self.assertRaisesRegex(FactWindowError, field):
                    compare_facts(review_snapshot(), after, generated_at=GENERATED)
        after = after_event()
        after['answers'] = [dict(answer('pending'), sources=[])]
        self.assertEqual(compare_facts(review_snapshot(), after, generated_at=GENERATED)
                         ['questions'][0]['sources'], [])

    def test_answer_sources_obey_the_same_window_and_https_requirements(self) -> None:
        for field, invalid in [('published_at', '2040-01-15T12:59:59+00:00'),
                               ('published_at', '2040-01-15T14:00:01+00:00'),
                               ('published_at', '2040-01-15T13:05:00'),
                               ('source_url', 'http://example.com/regions')]:
            with self.subTest(field=field, invalid=invalid):
                after = after_event()
                after['answers'] = [answer()]
                after['answers'][0]['sources'][0][field] = invalid
                with self.assertRaisesRegex(FactWindowError, field):
                    compare_facts(review_snapshot(), after, generated_at=GENERATED)

    def test_conflicting_answer_without_source_is_rejected(self) -> None:
        after = after_event()
        after['answers'] = [dict(answer('conflicting'), sources=[])]
        with self.assertRaisesRegex(FactWindowError, 'sources'):
            compare_facts(review_snapshot(), after, generated_at=GENERATED)

    def test_interpretation_is_explicitly_user_authored_and_does_not_change_status(self) -> None:
        after = after_event()
        after['interpretation'] = 'More users may increase service costs.'
        report = compare_facts(review_snapshot(), after, generated_at=GENERATED)
        self.assertEqual(report['rows'][0]['status'], 'above')
        self.assertEqual(report['interpretation'], after['interpretation'])
        self.assertIn('使用者解读', render_markdown(report))
        self.assertIn(after['interpretation'], render_markdown(report))

    def test_rehashed_invalid_question_metadata_is_not_trusted(self) -> None:
        for field, value in [('questions', [{'id': 'x', 'text': ''}]),
                             ('supports_if', []), ('refutes_if', ''),
                             ('review_by', '2040-01-14T12:00:00+00:00')]:
            with self.subTest(field=field):
                snapshot = review_snapshot()
                snapshot['event'][field] = value
                rehash(snapshot)
                with self.assertRaisesRegex(FactWindowError, field):
                    verify_snapshot(snapshot)


if __name__ == '__main__':
    unittest.main()
