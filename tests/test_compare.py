from __future__ import annotations

import unittest
from datetime import datetime, timezone

from factwindow.core import FactWindowError, compare_facts, freeze_before, render_markdown


def frozen_event(expectations: list[dict] | None = None) -> dict:
    before = {
        "event_id": "EVT-DEMO-001",
        "title": "Northstar Labs product update",
        "scheduled_at": "2040-01-15T13:00:00+00:00",
        "question": "Did customer adoption exceed the published target?",
        "unknowns": ["Regional mix is not yet disclosed."],
        "expectations": expectations
        or [
            {
                "metric": "active_teams",
                "prior": 80,
                "expected": 100,
                "unit": "teams",
                "source_url": "https://example.com/before-event-note",
            }
        ],
    }
    return freeze_before(
        before,
        now=datetime(2040, 1, 14, 12, 0, tzinfo=timezone.utc),
    )


def after_event(facts: list[dict] | None = None) -> dict:
    return {
        "event_id": "EVT-DEMO-001",
        "facts": facts
        or [
            {
                "metric": "active_teams",
                "actual": 112,
                "unit": "teams",
                "source_url": "https://example.com/official-update",
                "published_at": "2040-01-15T13:05:00+00:00",
            }
        ],
    }


class CompareTests(unittest.TestCase):
    def test_numeric_fact_is_compared(self) -> None:
        report = compare_facts(
            frozen_event(),
            after_event(),
            generated_at=datetime(2040, 1, 15, 14, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(report["schema_version"], "factwindow.report.v1")
        self.assertEqual(
            report["rows"],
            [
                {
                    "metric": "active_teams",
                    "unit": "teams",
                    "prior": 80,
                    "expected": 100,
                    "actual": 112,
                    "difference": 12,
                    "status": "above",
                    "expectation_source_url": "https://example.com/before-event-note",
                    "fact_source_url": "https://example.com/official-update",
                    "published_at": "2040-01-15T13:05:00+00:00",
                }
            ],
        )

    def test_changed_text_fact_is_visible(self) -> None:
        snapshot = frozen_event(
            [
                {
                    "metric": "launch_status",
                    "expected": "on_track",
                    "source_url": "https://example.com/before-event-note",
                }
            ]
        )
        after = after_event(
            [
                {
                    "metric": "launch_status",
                    "actual": "delayed",
                    "source_url": "https://example.com/official-update",
                    "published_at": "2040-01-15T13:05:00+00:00",
                }
            ]
        )

        report = compare_facts(
            snapshot,
            after,
            generated_at=datetime(2040, 1, 15, 14, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(report["rows"][0]["difference"], None)
        self.assertEqual(report["rows"][0]["status"], "changed")

    def test_boolean_and_number_are_not_treated_as_the_same_value(self) -> None:
        snapshot = frozen_event(
            [
                {
                    "metric": "feature_enabled",
                    "expected": False,
                    "source_url": "https://example.com/before-event-note",
                }
            ]
        )
        after = after_event(
            [
                {
                    "metric": "feature_enabled",
                    "actual": 0,
                    "source_url": "https://example.com/official-update",
                    "published_at": "2040-01-15T13:05:00+00:00",
                }
            ]
        )

        report = compare_facts(
            snapshot,
            after,
            generated_at=datetime(2040, 1, 15, 14, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(report["rows"][0]["status"], "changed")

    def test_missing_expected_metric_remains_unresolved(self) -> None:
        after = after_event(
            [
                {
                    "metric": "release_channel",
                    "actual": "public",
                    "source_url": "https://example.com/official-update",
                    "published_at": "2040-01-15T13:05:00+00:00",
                }
            ]
        )

        report = compare_facts(
            frozen_event(),
            after,
            generated_at=datetime(2040, 1, 15, 14, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(report["rows"][0]["metric"], "active_teams")
        self.assertEqual(report["rows"][0]["status"], "missing")
        self.assertTrue(
            any(
                "No fact supplied for active_teams." in item
                for item in report["unresolved"]
            )
        )
        self.assertTrue(
            any("未提供 active_teams 的事实" in item for item in report["unresolved"])
        )

    def test_unplanned_fact_is_not_discarded(self) -> None:
        after = after_event()
        after["facts"].append(
            {
                "metric": "support_regions",
                "actual": 6,
                "unit": "regions",
                "source_url": "https://example.com/official-update",
                "published_at": "2040-01-15T13:05:00+00:00",
            }
        )

        report = compare_facts(
            frozen_event(),
            after,
            generated_at=datetime(2040, 1, 15, 14, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(report["rows"][1]["metric"], "support_regions")
        self.assertEqual(report["rows"][1]["status"], "unplanned")
        self.assertEqual(report["rows"][1]["actual"], 6)
        self.assertIn("事前未列入 / Unplanned", render_markdown(report))

    def test_event_id_must_match_frozen_event(self) -> None:
        after = after_event()
        after["event_id"] = "EVT-OTHER"

        with self.assertRaisesRegex(FactWindowError, "event_id.*EVT-DEMO-001"):
            compare_facts(
                frozen_event(),
                after,
                generated_at=datetime(2040, 1, 15, 14, 0, tzinfo=timezone.utc),
            )

    def test_duplicate_fact_metric_is_rejected(self) -> None:
        after = after_event()
        after["facts"].append(dict(after["facts"][0]))

        with self.assertRaisesRegex(FactWindowError, "facts.*active_teams.*unique"):
            compare_facts(
                frozen_event(),
                after,
                generated_at=datetime(2040, 1, 15, 14, 0, tzinfo=timezone.utc),
            )

    def test_fact_cannot_be_published_before_event(self) -> None:
        after = after_event()
        after["facts"][0]["published_at"] = "2040-01-15T12:59:59+00:00"

        with self.assertRaisesRegex(FactWindowError, "published_at.*event"):
            compare_facts(
                frozen_event(),
                after,
                generated_at=datetime(2040, 1, 15, 14, 0, tzinfo=timezone.utc),
            )

    def test_fact_publication_requires_timezone(self) -> None:
        after = after_event()
        after["facts"][0]["published_at"] = "2040-01-15T13:05:00"

        with self.assertRaisesRegex(FactWindowError, "published_at.*timezone"):
            compare_facts(
                frozen_event(),
                after,
                generated_at=datetime(2040, 1, 15, 14, 0, tzinfo=timezone.utc),
            )

    def test_fact_source_must_use_https(self) -> None:
        after = after_event()
        after["facts"][0]["source_url"] = "http://example.com/official-update"

        with self.assertRaisesRegex(FactWindowError, "source_url.*https://"):
            compare_facts(
                frozen_event(),
                after,
                generated_at=datetime(2040, 1, 15, 14, 0, tzinfo=timezone.utc),
            )

    def test_actual_value_must_be_scalar(self) -> None:
        after = after_event()
        after["facts"][0]["actual"] = [112]

        with self.assertRaisesRegex(FactWindowError, "actual.*number, string, or boolean"):
            compare_facts(
                frozen_event(),
                after,
                generated_at=datetime(2040, 1, 15, 14, 0, tzinfo=timezone.utc),
            )

    def test_unit_mismatch_is_unresolved_without_blocking_report(self) -> None:
        after = after_event()
        after["facts"][0]["unit"] = "users"

        report = compare_facts(
            frozen_event(),
            after,
            generated_at=datetime(2040, 1, 15, 14, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(report["rows"][0]["status"], "unit_mismatch")
        self.assertIsNone(report["rows"][0]["difference"])
        self.assertTrue(
            any(
                "Unit mismatch for active_teams: teams vs users." in item
                for item in report["unresolved"]
            )
        )
        self.assertTrue(
            any("单位不一致" in item for item in report["unresolved"])
        )

    def test_generated_at_requires_timezone(self) -> None:
        with self.assertRaisesRegex(FactWindowError, "generated_at.*timezone"):
            compare_facts(
                frozen_event(),
                after_event(),
                generated_at=datetime(2040, 1, 15, 14, 0),
            )

    def test_generated_at_must_be_a_datetime(self) -> None:
        with self.assertRaisesRegex(FactWindowError, "generated_at.*datetime"):
            compare_facts(
                frozen_event(),
                after_event(),
                generated_at="2040-01-15T14:00:00+00:00",
            )

    def test_false_generated_at_is_not_treated_as_missing(self) -> None:
        with self.assertRaisesRegex(FactWindowError, "generated_at.*datetime"):
            compare_facts(
                frozen_event(),
                after_event(),
                generated_at=False,
            )

    def test_markdown_report_shows_comparison_sources_and_unknowns(self) -> None:
        report = compare_facts(
            frozen_event(),
            after_event(),
            generated_at=datetime(2040, 1, 15, 14, 0, tzinfo=timezone.utc),
        )

        markdown = render_markdown(report)

        self.assertIn("# Northstar Labs product update", markdown)
        self.assertIn("Did customer adoption exceed the published target?", markdown)
        self.assertIn(
            "| active_teams | teams | 80 | 100 | 112 | +12 | 高于预期 / Above expectation |",
            markdown,
        )
        self.assertIn(
            "事实来源 / Fact source: [active_teams](https://example.com/official-update)",
            markdown,
        )
        self.assertIn("- Regional mix is not yet disclosed.", markdown)

    def test_markdown_report_has_plain_bilingual_labels(self) -> None:
        report = compare_facts(
            frozen_event(),
            after_event(),
            generated_at=datetime(2040, 1, 15, 14, 0, tzinfo=timezone.utc),
        )

        markdown = render_markdown(report)

        self.assertIn("## 对照结果 / Comparison", markdown)
        self.assertIn("指标 / Metric", markdown)
        self.assertIn("预期 / Expected", markdown)
        self.assertIn("实际 / Actual", markdown)
        self.assertIn("高于预期 / Above expectation", markdown)
        self.assertIn("事实来源 / Fact source", markdown)
        self.assertIn("## 未解决问题 / Unresolved", markdown)


if __name__ == "__main__":
    unittest.main()
