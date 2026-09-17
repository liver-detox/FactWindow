from __future__ import annotations

import os
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "factwindow", *args],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


class CliTests(unittest.TestCase):
    def test_version_identifies_installed_release(self) -> None:
        result = run_cli("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "factwindow 0.2.0")

    def test_top_level_and_freeze_help_are_useful(self) -> None:
        top = run_cli("--help")
        freeze = run_cli("freeze", "--help")

        self.assertEqual(top.returncode, 0, top.stderr)
        self.assertIn("Freeze expectations, then compare sourced facts.", top.stdout)
        self.assertIn("demo", top.stdout)
        self.assertIn("freeze", top.stdout)
        self.assertIn("compare", top.stdout)
        self.assertEqual(freeze.returncode, 0, freeze.stderr)
        self.assertIn("before-event TOML", freeze.stdout)

    def test_top_level_help_is_bilingual(self) -> None:
        result = run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("事前记录预期，事后对照有来源的事实。", result.stdout)
        self.assertIn("Freeze expectations, then compare sourced facts.", result.stdout)

    def test_subcommand_help_is_bilingual(self) -> None:
        top = run_cli("--help")
        freeze = run_cli("freeze", "--help")
        compare = run_cli("compare", "--help")

        self.assertIn("生成完整的虚构示例", top.stdout)
        self.assertIn("在事件前固定预期记录", top.stdout)
        self.assertIn("生成事后对照报告", top.stdout)
        self.assertIn("事前 TOML 文件路径", freeze.stdout)
        self.assertIn("事后 TOML 文件路径", compare.stdout)

    def test_demo_creates_complete_synthetic_example(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "demo"

            result = run_cli("demo", "--output", str(output))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("report.md", result.stdout)
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {
                    "before.toml",
                    "before.snapshot.json",
                    "after.toml",
                    "report.md",
                    "report.json",
                },
            )
            self.assertIn(
                "虚构产品更新 / Fictional product update",
                (output / "report.md").read_text(encoding="utf-8"),
            )

    def test_demo_report_content_is_bilingual(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "demo"

            result = run_cli("demo", "--output", str(output))
            report = (output / "report.md").read_text(encoding="utf-8")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("虚构产品更新 / Fictional product update", report)
            self.assertIn("活跃团队数 / active teams", report)
            self.assertIn("按计划 / on track", report)
            self.assertIn("延期 / delayed", report)

    def test_demo_json_keeps_stable_english_status_codes(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "demo"

            result = run_cli("demo", "--output", str(output))
            report = json.loads((output / "report.json").read_text(encoding="utf-8"))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                [row["status"] for row in report["rows"]], ["above", "changed"]
            )

    def test_demo_success_message_is_bilingual(self) -> None:
        with TemporaryDirectory() as directory:
            result = run_cli("demo", "--output", str(Path(directory) / "demo"))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("示例已准备好 / Demo ready", result.stdout)

    def test_freeze_future_event_but_do_not_compare_before_it(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            before = root / "before.toml"
            after = root / "after.toml"
            snapshot = root / "artifacts" / "before.snapshot.json"
            report_dir = root / "artifacts" / "report"
            before.write_text(
                '''event_id = "EVT-QUICK-001"
title = "Fictional service update"
scheduled_at = "2099-02-01T10:00:00+00:00"
question = "Was the published target reached?"

[[expectations]]
metric = "completed_trials"
expected = 10
unit = "trials"
source_url = "https://example.com/plan"
''',
                encoding="utf-8",
            )
            after.write_text(
                '''event_id = "EVT-QUICK-001"

[[facts]]
metric = "completed_trials"
actual = 12
unit = "trials"
source_url = "https://example.com/result"
published_at = "2099-02-01T10:05:00+00:00"
''',
                encoding="utf-8",
            )

            freeze = run_cli("freeze", str(before), "--output", str(snapshot))
            compare = run_cli(
                "compare", str(snapshot), str(after), "--output", str(report_dir)
            )

            self.assertEqual(freeze.returncode, 0, freeze.stderr)
            self.assertTrue(snapshot.is_file())
            self.assertEqual(compare.returncode, 2, compare.stderr)
            self.assertIn("generated_at", compare.stderr)
            self.assertFalse(report_dir.exists())
            self.assertIn("预期已固定 / Expectations frozen", freeze.stdout)

    def test_compare_reads_a_snapshot_created_by_version_011(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            after = root / "after.toml"
            after.write_text('''event_id = "EVT-LEGACY-001"
[[facts]]
metric = "completed_trials"
actual = 12
unit = "trials"
source_url = "https://example.com/result"
published_at = "2000-02-01T10:05:00+00:00"
''', encoding="utf-8")
            output = root / "report"
            result = run_cli("compare", str(ROOT / "tests/fixtures/snapshot-v1.json"),
                             str(after), "--output", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((output / "report.json").read_text())
            self.assertEqual(report["schema_version"], "factwindow.report.v2")
            self.assertEqual(report["rows"][0]["difference"], 2)
            self.assertIn("对照报告已生成 / Comparison ready", result.stdout)

    def test_future_source_is_rejected_without_creating_report(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            after = root / "after.toml"
            after.write_text('''event_id = "EVT-LEGACY-001"
[[facts]]
metric = "completed_trials"
actual = 12
unit = "trials"
source_url = "https://example.com/result"
published_at = "2099-02-01T10:05:00+00:00"
''', encoding="utf-8")
            output = root / "report"
            result = run_cli("compare", str(ROOT / "tests/fixtures/snapshot-v1.json"),
                             str(after), "--output", str(output))
            self.assertEqual(result.returncode, 2)
            self.assertIn("published_at", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(output.exists())

    def test_malformed_toml_has_short_actionable_error(self) -> None:
        with TemporaryDirectory() as directory:
            broken = Path(directory) / "broken.toml"
            broken.write_text("event_id =", encoding="utf-8")

            result = run_cli("freeze", str(broken))

            self.assertEqual(result.returncode, 2)
            self.assertIn("error:", result.stderr)
            self.assertIn("无法读取 TOML 文件", result.stderr)
            self.assertIn("TOML", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_input_error_includes_a_plain_chinese_hint(self) -> None:
        with TemporaryDirectory() as directory:
            broken = Path(directory) / "broken.toml"
            broken.write_text("event_id =", encoding="utf-8")

            result = run_cli("freeze", str(broken))

            self.assertEqual(result.returncode, 2)
            self.assertIn("提示：", result.stderr)
            self.assertIn("请根据上面的字段名检查输入文件", result.stderr)

    def test_missing_command_argument_includes_chinese_hint(self) -> None:
        result = run_cli("freeze")

        self.assertEqual(result.returncode, 2)
        self.assertIn("before", result.stderr)
        self.assertIn("提示：", result.stderr)
        self.assertIn("请根据上面的字段名检查输入文件", result.stderr)

    def test_non_utf8_toml_has_short_actionable_error(self) -> None:
        with TemporaryDirectory() as directory:
            broken = Path(directory) / "broken.toml"
            broken.write_bytes(b"\xff\xfe\x00")

            result = run_cli("freeze", str(broken))

            self.assertEqual(result.returncode, 2)
            self.assertIn("无法读取 TOML 文件", result.stderr)
            self.assertIn("error:", result.stderr)
            self.assertIn("UTF-8", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_compare_rejects_tampered_snapshot_with_digest_message(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "demo"
            self.assertEqual(run_cli("demo", "--output", str(output)).returncode, 0)
            snapshot_path = output / "before.snapshot.json"
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            snapshot["event"]["expectations"][0]["expected"] = 999
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

            result = run_cli(
                "compare",
                str(snapshot_path),
                str(output / "after.toml"),
                "--output",
                str(output / "report-2"),
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("digest", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_compare_rejects_non_utf8_snapshot_with_short_error(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "demo"
            self.assertEqual(run_cli("demo", "--output", str(output)).returncode, 0)
            snapshot_path = output / "before.snapshot.json"
            snapshot_path.write_bytes(b"\xff\xfe\x00")

            result = run_cli(
                "compare",
                str(snapshot_path),
                str(output / "after.toml"),
                "--output",
                str(output / "report-2"),
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("无法读取 JSON 文件", result.stderr)
            self.assertIn("UTF-8", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_compare_rejects_nonfinite_json_number(self) -> None:
        with TemporaryDirectory() as directory:
            snapshot_path = Path(directory) / "before.snapshot.json"
            snapshot_path.write_text('{"value": NaN}', encoding="utf-8")

            result = run_cli(
                "compare",
                str(snapshot_path),
                str(Path(directory) / "after.toml"),
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("finite", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_compare_rejects_event_id_mismatch_with_clear_message(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "demo"
            self.assertEqual(run_cli("demo", "--output", str(output)).returncode, 0)
            after_path = output / "after.toml"
            after_path.write_text(
                after_path.read_text(encoding="utf-8").replace(
                    'event_id = "EVT-DEMO-001"',
                    'event_id = "EVT-DIFFERENT-001"',
                ),
                encoding="utf-8",
            )

            result = run_cli(
                "compare",
                str(output / "before.snapshot.json"),
                str(after_path),
                "--output",
                str(output / "report-2"),
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("event_id", result.stderr)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
