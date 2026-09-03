"""Command-line interface for FactWindow."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from .core import (
    FactWindowError,
    compare_facts,
    freeze_before,
    load_toml,
    render_markdown,
    write_snapshot,
)
from .demo_data import AFTER_TOML, BEFORE_TOML


_INPUT_HINT = "提示：请根据上面的字段名检查输入文件，常见问题是时间、来源链接或事件编号。"


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: 错误 / error: {message}\n{_INPUT_HINT}\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="factwindow",
        description=(
            "事前记录预期，事后对照有来源的事实。 / "
            "Freeze expectations, then compare sourced facts."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    demo = commands.add_parser(
        "demo", help="生成完整的虚构示例 / Create a complete synthetic example."
    )
    demo.add_argument(
        "--output", default="factwindow-demo", help="输出目录 / Output directory."
    )

    freeze = commands.add_parser(
        "freeze",
        help=(
            "在事件前固定预期记录 / "
            "Freeze a before-event TOML file before the event."
        ),
    )
    freeze.add_argument(
        "before", help="事前 TOML 文件路径 / Path to the before-event TOML file."
    )
    freeze.add_argument("--output", help="快照 JSON 路径 / Snapshot JSON path.")

    compare = commands.add_parser(
        "compare",
        help=(
            "生成事后对照报告 / "
            "Compare a frozen snapshot with after-event facts."
        ),
    )
    compare.add_argument(
        "snapshot", help="事前快照 JSON 路径 / Path to the frozen snapshot JSON file."
    )
    compare.add_argument(
        "after", help="事后 TOML 文件路径 / Path to the after-event TOML file."
    )
    compare.add_argument(
        "--output", default="factwindow-report", help="输出目录 / Output directory."
    )
    return parser


def _run_demo(output: Path) -> int:
    output.mkdir(parents=True, exist_ok=True)
    before_path = output / "before.toml"
    after_path = output / "after.toml"
    snapshot_path = output / "before.snapshot.json"
    before_path.write_text(BEFORE_TOML, encoding="utf-8")
    after_path.write_text(AFTER_TOML, encoding="utf-8")

    snapshot = freeze_before(
        load_toml(before_path),
        now=datetime.fromisoformat("2099-01-14T12:00:00+00:00"),
    )
    write_snapshot(snapshot, snapshot_path)
    report = compare_facts(
        snapshot,
        load_toml(after_path),
        generated_at=datetime.fromisoformat("2099-01-15T14:00:00+00:00"),
    )
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output / "report.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"示例已准备好 / Demo ready: {output / 'report.md'}")
    return 0


def _run_freeze(before: Path, output: Path | None) -> int:
    target = output or before.with_name(f"{before.stem}.snapshot.json")
    snapshot = freeze_before(load_toml(before))
    write_snapshot(snapshot, target)
    print(f"预期已固定 / Expectations frozen: {target}")
    return 0


def _reject_nonfinite_json(value: str) -> object:
    raise FactWindowError(f"JSON numbers must be finite, not {value}")


def _load_json(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise FactWindowError(
            f"无法读取 JSON 文件 / Cannot read JSON file {path}: "
            "文件必须使用 UTF-8 编码 / file must be UTF-8"
        ) from exc
    except OSError as exc:
        raise FactWindowError(
            f"无法读取 JSON 文件 / Cannot read JSON file {path}: {exc}"
        ) from exc
    try:
        document = json.loads(text, parse_constant=_reject_nonfinite_json)
    except json.JSONDecodeError as exc:
        raise FactWindowError(
            f"无法读取 JSON 文件 / Cannot read JSON file {path}: {exc}"
        ) from exc
    if not isinstance(document, dict):
        raise FactWindowError(
            f"JSON 文件必须包含对象 / JSON file {path} must contain an object"
        )
    return document


def _run_compare(snapshot_path: Path, after_path: Path, output: Path) -> int:
    report = compare_facts(_load_json(snapshot_path), load_toml(after_path))
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output / "report.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"对照报告已生成 / Comparison ready: {output / 'report.md'}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "demo":
            return _run_demo(Path(args.output))
        if args.command == "freeze":
            return _run_freeze(
                Path(args.before), Path(args.output) if args.output else None
            )
        if args.command == "compare":
            return _run_compare(Path(args.snapshot), Path(args.after), Path(args.output))
    except (FactWindowError, OSError, json.JSONDecodeError) as exc:
        print(f"错误 / error: {exc}", file=sys.stderr)
        print(_INPUT_HINT, file=sys.stderr)
        return 2
    raise AssertionError(f"command {args.command!r} is not implemented")
