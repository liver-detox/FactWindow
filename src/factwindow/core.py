"""Core before/after event comparison behavior for FactWindow."""

from __future__ import annotations

import hashlib
import json
import math
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class FactWindowError(ValueError):
    """An input cannot be turned into a FactWindow artifact."""


def _parse_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise FactWindowError(f"{field} must be an ISO-8601 date and time with a timezone")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise FactWindowError(
            f"{field} must be an ISO-8601 date and time with a timezone"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FactWindowError(f"{field} must include a timezone, such as +00:00")
    return parsed


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FactWindowError(f"{field} must be a non-empty string")
    return value.strip()


def _https_url(value: Any, field: str) -> str:
    url = _text(value, field)
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise FactWindowError(f"{field} must be a complete https:// URL")
    return url


def _scalar(value: Any, field: str) -> str | int | float | bool:
    if not isinstance(value, (str, int, float, bool)):
        raise FactWindowError(f"{field} must be a number, string, or boolean")
    if isinstance(value, float) and not math.isfinite(value):
        raise FactWindowError(f"{field} must be a finite number")
    return value


def _digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_toml(path: Path) -> dict[str, Any]:
    """Load a UTF-8 TOML mapping with a user-facing error."""

    try:
        with path.open("rb") as handle:
            document = tomllib.load(handle)
    except UnicodeDecodeError as exc:
        raise FactWindowError(
            f"无法读取 TOML 文件 / Cannot read TOML file {path}: "
            "文件必须使用 UTF-8 编码 / file must be UTF-8"
        ) from exc
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise FactWindowError(
            f"无法读取 TOML 文件 / Cannot read TOML file {path}: {exc}"
        ) from exc
    if not isinstance(document, dict):
        raise FactWindowError(
            f"TOML 文件必须包含字段映射 / "
            f"TOML file {path} must contain a mapping"
        )
    return document


def write_snapshot(snapshot: dict[str, Any], path: Path) -> None:
    """Write a snapshot as readable JSON, creating its parent directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def freeze_before(document: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Validate and freeze a before-event document into a digested snapshot."""

    if not isinstance(document, dict):
        raise FactWindowError("before-event document must be a mapping")
    current = datetime.now(timezone.utc) if now is None else now
    if not isinstance(current, datetime):
        raise FactWindowError("now must be a datetime with a timezone")
    if current.tzinfo is None or current.utcoffset() is None:
        raise FactWindowError("now must include a timezone")
    current = current.astimezone(timezone.utc)
    scheduled = _parse_datetime(document.get("scheduled_at"), "scheduled_at")
    if scheduled <= current:
        raise FactWindowError("scheduled_at must be later than the freeze time")

    expectations = document.get("expectations")
    if not isinstance(expectations, list) or not expectations:
        raise FactWindowError("expectations must contain at least one item")
    normalized_expectations: list[dict[str, Any]] = []
    seen_metrics: set[str] = set()
    for index, item in enumerate(expectations):
        if not isinstance(item, dict):
            raise FactWindowError(f"expectations[{index}] must be a mapping")
        metric = _text(item.get("metric"), f"expectations[{index}].metric")
        if metric in seen_metrics:
            raise FactWindowError(
                f"expectations metric {metric!r} must be unique"
            )
        seen_metrics.add(metric)
        normalized = dict(item)
        normalized["metric"] = metric
        normalized["expected"] = _scalar(
            item.get("expected"), f"expectations[{index}].expected"
        )
        if "prior" in item:
            normalized["prior"] = _scalar(
                item["prior"], f"expectations[{index}].prior"
            )
        if "unit" in item:
            normalized["unit"] = _text(
                item["unit"], f"expectations[{index}].unit"
            )
        normalized["source_url"] = _https_url(
            item.get("source_url"), f"expectations[{index}].source_url"
        )
        normalized_expectations.append(normalized)

    unknowns = document.get("unknowns", [])
    if not isinstance(unknowns, list) or not all(
        isinstance(item, str) and item.strip() for item in unknowns
    ):
        raise FactWindowError("unknowns must be a list of non-empty strings")

    event = {
        "event_id": _text(document.get("event_id"), "event_id"),
        "title": _text(document.get("title"), "title"),
        "scheduled_at": scheduled.isoformat(),
        "question": _text(document.get("question"), "question"),
        "unknowns": [item.strip() for item in unknowns],
        "expectations": normalized_expectations,
    }
    snapshot = {
        "schema_version": "factwindow.snapshot.v1",
        "frozen_at": current.isoformat(),
        "event": event,
    }
    snapshot["content_sha256"] = _digest(snapshot)
    return snapshot


def verify_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return a snapshot after confirming its schema and content digest."""

    if not isinstance(snapshot, dict):
        raise FactWindowError("snapshot must be a JSON object")
    if snapshot.get("schema_version") != "factwindow.snapshot.v1":
        raise FactWindowError("snapshot schema_version must be factwindow.snapshot.v1")
    expected = snapshot.get("content_sha256")
    if not isinstance(expected, str):
        raise FactWindowError("snapshot digest is missing")
    payload = {key: value for key, value in snapshot.items() if key != "content_sha256"}
    if _digest(payload) != expected:
        raise FactWindowError("snapshot digest does not match its content")

    _parse_datetime(snapshot.get("frozen_at"), "snapshot.frozen_at")
    event = snapshot.get("event")
    if not isinstance(event, dict):
        raise FactWindowError("snapshot.event must be an object")
    _text(event.get("event_id"), "snapshot.event.event_id")
    _text(event.get("title"), "snapshot.event.title")
    _parse_datetime(event.get("scheduled_at"), "snapshot.event.scheduled_at")
    _text(event.get("question"), "snapshot.event.question")
    unknowns = event.get("unknowns", [])
    if not isinstance(unknowns, list) or not all(
        isinstance(item, str) and item.strip() for item in unknowns
    ):
        raise FactWindowError(
            "snapshot.event.unknowns must be a list of non-empty strings"
        )
    expectations = event.get("expectations")
    if not isinstance(expectations, list) or not expectations:
        raise FactWindowError(
            "snapshot.event.expectations must contain at least one item"
        )
    seen_metrics: set[str] = set()
    for index, item in enumerate(expectations):
        field = f"snapshot.event.expectations[{index}]"
        if not isinstance(item, dict):
            raise FactWindowError(f"{field} must be an object")
        metric = _text(item.get("metric"), f"{field}.metric")
        if metric in seen_metrics:
            raise FactWindowError(f"{field}.metric must be unique")
        seen_metrics.add(metric)
        _scalar(item.get("expected"), f"{field}.expected")
        if "prior" in item:
            _scalar(item["prior"], f"{field}.prior")
        if "unit" in item:
            _text(item["unit"], f"{field}.unit")
        _https_url(item.get("source_url"), f"{field}.source_url")
    return snapshot


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def compare_facts(
    snapshot: dict[str, Any],
    after: dict[str, Any],
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Compare a verified before-event snapshot with sourced after-event facts."""

    verify_snapshot(snapshot)
    event = snapshot["event"]
    if not isinstance(after, dict):
        raise FactWindowError("after-event document must be a mapping")
    after_event_id = _text(after.get("event_id"), "event_id")
    if after_event_id != event["event_id"]:
        raise FactWindowError(
            f"event_id must match frozen event {event['event_id']!r}"
        )
    generated = datetime.now(timezone.utc) if generated_at is None else generated_at
    if not isinstance(generated, datetime):
        raise FactWindowError("generated_at must be a datetime with a timezone")
    if generated.tzinfo is None or generated.utcoffset() is None:
        raise FactWindowError("generated_at must include a timezone")
    generated = generated.astimezone(timezone.utc)

    facts = after.get("facts")
    if not isinstance(facts, list) or not facts:
        raise FactWindowError("facts must contain at least one item")
    normalized_facts: list[dict[str, Any]] = []
    seen_fact_metrics: set[str] = set()
    for index, item in enumerate(facts):
        if not isinstance(item, dict):
            raise FactWindowError(f"facts[{index}] must be a mapping")
        metric = _text(item.get("metric"), f"facts[{index}].metric")
        if metric in seen_fact_metrics:
            raise FactWindowError(f"facts metric {metric!r} must be unique")
        seen_fact_metrics.add(metric)
        normalized = dict(item)
        normalized["metric"] = metric
        normalized["actual"] = _scalar(
            item.get("actual"), f"facts[{index}].actual"
        )
        if "unit" in item:
            normalized["unit"] = _text(item["unit"], f"facts[{index}].unit")
        normalized["source_url"] = _https_url(
            item.get("source_url"), f"facts[{index}].source_url"
        )
        normalized_facts.append(normalized)
    scheduled = _parse_datetime(event["scheduled_at"], "scheduled_at")
    for fact in normalized_facts:
        published = _parse_datetime(
            fact.get("published_at"), f"facts.{fact['metric']}.published_at"
        )
        if published < scheduled:
            raise FactWindowError(
                f"facts.{fact['metric']}.published_at cannot be before the event"
            )
        fact["published_at"] = published.isoformat()
    facts_by_metric = {item["metric"]: item for item in normalized_facts}

    rows: list[dict[str, Any]] = []
    unresolved = list(event.get("unknowns", []))
    for expectation in event["expectations"]:
        metric = expectation["metric"]
        fact = facts_by_metric.get(metric)
        if fact is None:
            rows.append(
                {
                    "metric": metric,
                    "unit": expectation.get("unit"),
                    "prior": expectation.get("prior"),
                    "expected": expectation["expected"],
                    "actual": None,
                    "difference": None,
                    "status": "missing",
                    "expectation_source_url": expectation["source_url"],
                    "fact_source_url": None,
                    "published_at": None,
                }
            )
            unresolved.append(
                f"未提供 {metric} 的事实。 / No fact supplied for {metric}."
            )
            continue
        expected = expectation["expected"]
        actual = fact["actual"]
        expectation_unit = expectation.get("unit")
        fact_unit = fact.get("unit")
        units_conflict = bool(
            expectation_unit and fact_unit and expectation_unit != fact_unit
        )
        difference = (
            actual - expected
            if not units_conflict and _is_number(expected) and _is_number(actual)
            else None
        )
        if units_conflict:
            status = "unit_mismatch"
            unresolved.append(
                f"单位不一致：{metric} 的预期单位为 {expectation_unit}，"
                f"事实单位为 {fact_unit}。 / "
                f"Unit mismatch for {metric}: {expectation_unit} vs {fact_unit}."
            )
        elif difference is not None:
            status = "above" if difference > 0 else "below" if difference < 0 else "matched"
        else:
            status = (
                "matched"
                if type(actual) is type(expected) and actual == expected
                else "changed"
            )
        rows.append(
            {
                "metric": metric,
                "unit": expectation.get("unit") or fact.get("unit"),
                "prior": expectation.get("prior"),
                "expected": expected,
                "actual": actual,
                "difference": difference,
                "status": status,
                "expectation_source_url": expectation["source_url"],
                "fact_source_url": fact["source_url"],
                "published_at": fact["published_at"],
            }
        )

    expected_metrics = {item["metric"] for item in event["expectations"]}
    for fact in normalized_facts:
        metric = fact["metric"]
        if metric in expected_metrics:
            continue
        rows.append(
            {
                "metric": metric,
                "unit": fact.get("unit"),
                "prior": None,
                "expected": None,
                "actual": fact["actual"],
                "difference": None,
                "status": "unplanned",
                "expectation_source_url": None,
                "fact_source_url": fact["source_url"],
                "published_at": fact["published_at"],
            }
        )

    return {
        "schema_version": "factwindow.report.v1",
        "generated_at": generated.isoformat(),
        "event_id": event["event_id"],
        "title": event["title"],
        "scheduled_at": event["scheduled_at"],
        "question": event["question"],
        "frozen_at": snapshot["frozen_at"],
        "rows": rows,
        "unresolved": unresolved,
    }


def _display(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).replace("\n", " ").replace("|", "\\|")


def _difference_display(value: Any) -> str:
    if value is None:
        return "—"
    if _is_number(value) and value > 0:
        return f"+{value}"
    return str(value)


_STATUS_LABELS = {
    "above": "高于预期 / Above expectation",
    "below": "低于预期 / Below expectation",
    "matched": "符合预期 / Matched",
    "changed": "发生变化 / Changed",
    "missing": "缺少事实 / Missing",
    "unplanned": "事前未列入 / Unplanned",
    "unit_mismatch": "单位不一致 / Unit mismatch",
}


def _status_display(value: Any) -> str:
    return _STATUS_LABELS.get(value, _display(value))


def render_markdown(report: dict[str, Any]) -> str:
    """Render a FactWindow report as compact, human-readable Markdown."""

    lines = [
        f"# {report['title']}",
        "",
        f"> {report['question']}",
        "",
        f"- 事件编号 / Event: `{report['event_id']}`",
        f"- 计划时间 / Scheduled: `{report['scheduled_at']}`",
        f"- 预期冻结时间 / Expectations frozen: `{report['frozen_at']}`",
        f"- 报告生成时间 / Report generated: `{report['generated_at']}`",
        "",
        "## 对照结果 / Comparison",
        "",
        "| 指标 / Metric | 单位 / Unit | 前值 / Prior | 预期 / Expected | 实际 / Actual | 差值 / Difference | 结果 / Status |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in report["rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _display(row["metric"]),
                    _display(row["unit"]),
                    _display(row["prior"]),
                    _display(row["expected"]),
                    _display(row["actual"]),
                    _difference_display(row["difference"]),
                    _status_display(row["status"]),
                ]
            )
            + " |"
        )

    lines.extend(["", "## 来源 / Sources", ""])
    for row in report["rows"]:
        if row["expectation_source_url"]:
            lines.append(
                f"- 预期来源 / Expectation source: "
                f"[{row['metric']}]({row['expectation_source_url']})"
            )
        if row["fact_source_url"]:
            lines.append(
                f"- 事实来源 / Fact source: "
                f"[{row['metric']}]({row['fact_source_url']})"
            )

    lines.extend(["", "## 未解决问题 / Unresolved", ""])
    if report["unresolved"]:
        lines.extend(f"- {item}" for item in report["unresolved"])
    else:
        lines.append("- 暂无 / None recorded.")
    return "\n".join(lines) + "\n"
