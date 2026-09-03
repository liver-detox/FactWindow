from __future__ import annotations

import hashlib
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from factwindow.core import (
    FactWindowError,
    freeze_before,
    load_toml,
    verify_snapshot,
    write_snapshot,
)


def before_event() -> dict:
    return {
        "event_id": "EVT-DEMO-001",
        "title": "Northstar Labs product update",
        "scheduled_at": "2040-01-15T13:00:00+00:00",
        "question": "Did customer adoption exceed the published target?",
        "unknowns": ["Regional mix is not yet disclosed."],
        "expectations": [
            {
                "metric": "active_teams",
                "prior": 80,
                "expected": 100,
                "unit": "teams",
                "source_url": "https://example.com/before-event-note",
            }
        ],
    }


class FreezeTests(unittest.TestCase):
    def test_valid_before_event_freezes(self) -> None:
        before = before_event()
        now = datetime(2040, 1, 14, 12, 0, tzinfo=timezone.utc)

        snapshot = freeze_before(before, now=now)

        self.assertEqual(snapshot["schema_version"], "factwindow.snapshot.v1")
        self.assertEqual(snapshot["frozen_at"], "2040-01-14T12:00:00+00:00")
        self.assertEqual(snapshot["event"]["event_id"], "EVT-DEMO-001")
        self.assertEqual(snapshot["event"]["expectations"][0]["expected"], 100)
        self.assertEqual(len(snapshot["content_sha256"]), 64)

    def test_event_must_be_later_than_freeze_time(self) -> None:
        before = before_event()
        before["scheduled_at"] = "2040-01-14T11:59:59+00:00"

        with self.assertRaisesRegex(FactWindowError, "scheduled_at.*later"):
            freeze_before(
                before,
                now=datetime(2040, 1, 14, 12, 0, tzinfo=timezone.utc),
            )

    def test_duplicate_expectation_metric_is_rejected(self) -> None:
        before = before_event()
        before["expectations"].append(dict(before["expectations"][0]))

        with self.assertRaisesRegex(FactWindowError, "expectations.*active_teams.*unique"):
            freeze_before(
                before,
                now=datetime(2040, 1, 14, 12, 0, tzinfo=timezone.utc),
            )

    def test_expectation_source_must_use_https(self) -> None:
        before = before_event()
        before["expectations"][0]["source_url"] = "http://example.com/note"

        with self.assertRaisesRegex(FactWindowError, "source_url.*https://"):
            freeze_before(
                before,
                now=datetime(2040, 1, 14, 12, 0, tzinfo=timezone.utc),
            )

    def test_tampered_snapshot_is_rejected(self) -> None:
        snapshot = freeze_before(
            before_event(),
            now=datetime(2040, 1, 14, 12, 0, tzinfo=timezone.utc),
        )
        snapshot["event"]["expectations"][0]["expected"] = 999

        with self.assertRaisesRegex(FactWindowError, "digest"):
            verify_snapshot(snapshot)

    def test_rehashed_malformed_snapshot_is_rejected_cleanly(self) -> None:
        snapshot = freeze_before(
            before_event(),
            now=datetime(2040, 1, 14, 12, 0, tzinfo=timezone.utc),
        )
        snapshot["event"].pop("expectations")
        payload = {
            key: value for key, value in snapshot.items() if key != "content_sha256"
        }
        snapshot["content_sha256"] = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()

        with self.assertRaisesRegex(FactWindowError, "snapshot.event.expectations"):
            verify_snapshot(snapshot)

    def test_toml_input_and_snapshot_output_round_trip(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            before_path = root / "before.toml"
            before_path.write_text(
                """event_id = "EVT-DEMO-001"
title = "Northstar Labs product update"
scheduled_at = "2040-01-15T13:00:00+00:00"
question = "Did customer adoption exceed the published target?"
unknowns = ["Regional mix is not yet disclosed."]

[[expectations]]
metric = "active_teams"
prior = 80
expected = 100
unit = "teams"
source_url = "https://example.com/before-event-note"
""",
                encoding="utf-8",
            )
            snapshot_path = root / "nested" / "before.snapshot.json"

            snapshot = freeze_before(
                load_toml(before_path),
                now=datetime(2040, 1, 14, 12, 0, tzinfo=timezone.utc),
            )
            write_snapshot(snapshot, snapshot_path)

            self.assertTrue(snapshot_path.is_file())
            self.assertIn('"schema_version": "factwindow.snapshot.v1"', snapshot_path.read_text())

    def test_expected_value_must_be_scalar(self) -> None:
        before = before_event()
        before["expectations"][0]["expected"] = {"not": "a scalar"}

        with self.assertRaisesRegex(FactWindowError, "expected.*number, string, or boolean"):
            freeze_before(
                before,
                now=datetime(2040, 1, 14, 12, 0, tzinfo=timezone.utc),
            )

    def test_prior_value_must_be_scalar_when_present(self) -> None:
        before = before_event()
        before["expectations"][0]["prior"] = [80]

        with self.assertRaisesRegex(FactWindowError, "prior.*number, string, or boolean"):
            freeze_before(
                before,
                now=datetime(2040, 1, 14, 12, 0, tzinfo=timezone.utc),
            )

    def test_unit_must_be_text_when_present(self) -> None:
        before = before_event()
        before["expectations"][0]["unit"] = 1

        with self.assertRaisesRegex(FactWindowError, "unit.*non-empty string"):
            freeze_before(
                before,
                now=datetime(2040, 1, 14, 12, 0, tzinfo=timezone.utc),
            )

    def test_scheduled_at_requires_timezone(self) -> None:
        before = before_event()
        before["scheduled_at"] = "2040-01-15T13:00:00"

        with self.assertRaisesRegex(FactWindowError, "scheduled_at.*timezone"):
            freeze_before(
                before,
                now=datetime(2040, 1, 14, 12, 0, tzinfo=timezone.utc),
            )

    def test_injected_freeze_time_requires_timezone(self) -> None:
        with self.assertRaisesRegex(FactWindowError, "now.*timezone"):
            freeze_before(
                before_event(),
                now=datetime(2040, 1, 14, 12, 0),
            )

    def test_injected_freeze_time_must_be_a_datetime(self) -> None:
        with self.assertRaisesRegex(FactWindowError, "now.*datetime"):
            freeze_before(before_event(), now="2040-01-14T12:00:00+00:00")

    def test_false_freeze_time_is_not_treated_as_missing(self) -> None:
        with self.assertRaisesRegex(FactWindowError, "now.*datetime"):
            freeze_before(before_event(), now=False)


if __name__ == "__main__":
    unittest.main()
