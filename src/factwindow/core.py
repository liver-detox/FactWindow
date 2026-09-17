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
        raise FactWindowError(
            f"{field} 必须填写带时区的日期时间 / "
            f"{field} must be an ISO-8601 date and time with a timezone"
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise FactWindowError(
            f"{field} 必须填写带时区的日期时间 / "
            f"{field} must be an ISO-8601 date and time with a timezone"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FactWindowError(
            f"{field} 必须包含时区，例如 +08:00 / "
            f"{field} must include a timezone, such as +00:00"
        )
    return parsed


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FactWindowError(
            f"{field} 必须填写非空文本 / {field} must be a non-empty string"
        )
    return value.strip()


def _https_url(value: Any, field: str) -> str:
    url = _text(value, field)
    error = (
        f"{field} 必须填写完整有效的 https:// 来源链接 / "
        f"{field} must be a complete valid https:// URL"
    )
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise FactWindowError(error) from exc
    if parsed.scheme != "https" or not parsed.netloc:
        raise FactWindowError(error)
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


def _review_metadata(
    document: dict[str, Any], scheduled: datetime, *, prefix: str = ""
) -> dict[str, Any]:
    """Validate optional frozen questions and the author's judgment criteria."""

    metadata: dict[str, Any] = {}
    if "questions" in document:
        questions = document["questions"]
        if not isinstance(questions, list):
            raise FactWindowError(
                f"{prefix}questions 必须为问题列表 / questions must be a list"
            )
        normalized = []
        seen: set[str] = set()
        for index, item in enumerate(questions):
            field = f"{prefix}questions[{index}]"
            if not isinstance(item, dict):
                raise FactWindowError(f"{field} 必须包含 id 和 text / must be a mapping")
            question_id = _text(item.get("id"), f"{field}.id")
            if question_id in seen:
                raise FactWindowError(
                    f"{field}.id 问题编号不能重复 / question id must be unique"
                )
            seen.add(question_id)
            normalized.append({
                "id": question_id,
                "text": _text(item.get("text"), f"{field}.text"),
            })
        metadata["questions"] = normalized
    for field in ("supports_if", "refutes_if"):
        if field in document:
            metadata[field] = _text(document[field], f"{prefix}{field}")
    if "review_by" in document:
        review_by = _parse_datetime(document["review_by"], f"{prefix}review_by")
        if review_by < scheduled:
            raise FactWindowError(
                f"{prefix}review_by 验证期限不能早于事件时间 / "
                "review_by cannot be before the event"
            )
        metadata["review_by"] = review_by.isoformat()
    return metadata


def _published_source(
    item: dict[str, Any], field: str, scheduled: datetime, generated: datetime
) -> dict[str, str]:
    source_url = _https_url(item.get("source_url"), f"{field}.source_url")
    published = _parse_datetime(item.get("published_at"), f"{field}.published_at")
    if published < scheduled:
        raise FactWindowError(
            f"{field}.published_at 发布时间不能早于事件时间 / "
            f"{field}.published_at cannot be before the event"
        )
    if published > generated:
        raise FactWindowError(
            f"{field}.published_at 发布时间不能晚于报告生成时间 / "
            f"{field}.published_at cannot be after generated_at"
        )
    return {"source_url": source_url, "published_at": published.isoformat()}


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
        raise FactWindowError(
            "scheduled_at 事件时间必须晚于冻结时间 / "
            "scheduled_at must be later than the freeze time"
        )

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
    event.update(_review_metadata(document, scheduled))
    snapshot = {
        "schema_version": "factwindow.snapshot.v2",
        "frozen_at": current.isoformat(),
        "event": event,
    }
    snapshot["content_sha256"] = _digest(snapshot)
    return snapshot


def verify_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return a snapshot after confirming its schema and content digest."""

    if not isinstance(snapshot, dict):
        raise FactWindowError("snapshot must be a JSON object")
    if snapshot.get("schema_version") not in (
        "factwindow.snapshot.v1", "factwindow.snapshot.v2"
    ):
        raise FactWindowError(
            "snapshot schema_version must be factwindow.snapshot.v1 or factwindow.snapshot.v2"
        )
    expected = snapshot.get("content_sha256")
    if not isinstance(expected, str):
        raise FactWindowError("snapshot digest is missing")
    payload = {key: value for key, value in snapshot.items() if key != "content_sha256"}
    if _digest(payload) != expected:
        raise FactWindowError("snapshot digest does not match its content")

    frozen = _parse_datetime(snapshot.get("frozen_at"), "snapshot.frozen_at")
    event = snapshot.get("event")
    if not isinstance(event, dict):
        raise FactWindowError("snapshot.event must be an object")
    _text(event.get("event_id"), "snapshot.event.event_id")
    _text(event.get("title"), "snapshot.event.title")
    scheduled = _parse_datetime(event.get("scheduled_at"), "snapshot.event.scheduled_at")
    if frozen >= scheduled:
        raise FactWindowError(
            "snapshot.frozen_at 冻结时间必须早于事件时间 / "
            "snapshot.frozen_at must be before scheduled_at"
        )
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
    _review_metadata(event, scheduled, prefix="snapshot.event.")
    return snapshot


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _question_reviews(
    event: dict[str, Any], after: dict[str, Any], scheduled: datetime, generated: datetime
) -> list[dict[str, Any]]:
    questions = event.get("questions", [])
    questions_by_id = {item["id"]: item for item in questions}
    answers = after.get("answers", [])
    if not isinstance(answers, list):
        raise FactWindowError("answers 必须为回答列表 / answers must be a list")
    answers_by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(answers):
        field = f"answers[{index}]"
        if not isinstance(item, dict):
            raise FactWindowError(f"{field} 必须为回答对象 / must be a mapping")
        question_id = _text(item.get("question_id"), f"{field}.question_id")
        if question_id not in questions_by_id:
            raise FactWindowError(
                f"{field}.question_id {question_id!r} 未在快照中冻结 / "
                "question_id must refer to a frozen question"
            )
        if question_id in answers_by_id:
            raise FactWindowError(
                f"{field}.question_id 不能重复回答同一问题 / question_id must be unique"
            )
        status = item.get("status")
        if status not in ("answered", "pending", "conflicting"):
            raise FactWindowError(
                f"{field}.status 必须填写 answered、pending 或 conflicting / "
                "status must be answered, pending, or conflicting"
            )
        reason = _text(item.get("reason"), f"{field}.reason")
        sources = item.get("sources", [])
        if not isinstance(sources, list):
            raise FactWindowError(f"{field}.sources 必须为来源列表 / sources must be a list")
        if status in ("answered", "conflicting") and not sources:
            raise FactWindowError(
                f"{field}.sources 已回答或存在冲突时至少需要一项来源 / "
                "answered or conflicting status requires at least one source"
            )
        normalized_sources = []
        for source_index, source in enumerate(sources):
            source_field = f"{field}.sources[{source_index}]"
            if not isinstance(source, dict):
                raise FactWindowError(f"{source_field} 必须为来源对象 / must be a mapping")
            normalized_sources.append(
                _published_source(source, source_field, scheduled, generated)
            )
        answers_by_id[question_id] = {
            "status": status, "reason": reason, "sources": normalized_sources,
        }
    return [
        {
            "id": question["id"], "text": question["text"],
            **answers_by_id.get(question["id"], {
                "status": "pending",
                "reason": "尚未提供回答。 / No answer supplied yet.",
                "sources": [],
            }),
        }
        for question in questions
    ]


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
    scheduled = _parse_datetime(event["scheduled_at"], "scheduled_at")
    if generated < scheduled:
        raise FactWindowError(
            "generated_at 所对应的事件尚未发生，请在事件发生后生成报告 / "
            "generated_at cannot be before the event"
        )

    facts = after.get("facts")
    if not isinstance(facts, list):
        raise FactWindowError(
            "facts 必须为事实列表；尚无材料时填写 facts = [] / "
            "facts must be a list; use facts = [] when evidence is not yet available"
        )
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
        normalized.update(_published_source(item, f"facts[{index}]", scheduled, generated))
        normalized_facts.append(normalized)
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
                    "unit": None,
                    "expectation_unit": expectation.get("unit"),
                    "fact_unit": None,
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
        unit_unconfirmed = (expectation_unit is None) != (fact_unit is None)
        numbers = _is_number(expected) and _is_number(actual)
        types_conflict = not numbers and type(expected) is not type(actual)
        difference = None
        if not units_conflict and not unit_unconfirmed and numbers:
            difference_error = (
                f"{metric} 的差值超出可表示的数值范围，请核对原始值，"
                "并为两侧使用相同的较大计量单位。 / "
                f"Difference for {metric} is outside the representable numeric range; "
                "check the values and use the same larger measurement unit on both sides."
            )
            try:
                difference = actual - expected
            except OverflowError as exc:
                raise FactWindowError(difference_error) from exc
            if isinstance(difference, float) and not math.isfinite(difference):
                raise FactWindowError(difference_error)
        if units_conflict:
            status = "unit_mismatch"
            unresolved.append(
                f"单位不一致：{metric} 的预期单位为 {expectation_unit}，"
                f"事实单位为 {fact_unit}。 / "
                f"Unit mismatch for {metric}: {expectation_unit} vs {fact_unit}."
            )
        elif unit_unconfirmed:
            status = "unit_unconfirmed"
            unresolved.append(
                f"单位尚未确认：{metric} 仅有一侧填写单位，请核对后补齐。 / "
                f"Unit unconfirmed for {metric}: only one side specifies a unit."
            )
        elif types_conflict:
            status = "type_mismatch"
            unresolved.append(
                f"类型不一致：{metric} 的预期与事实类型不同，请核对原始值。 / "
                f"Type mismatch for {metric}: expected {type(expected).__name__}, "
                f"actual {type(actual).__name__}."
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
                "unit": expectation_unit if expectation_unit == fact_unit else None,
                "expectation_unit": expectation_unit,
                "fact_unit": fact_unit,
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
                "unit": None,
                "expectation_unit": None,
                "fact_unit": fact.get("unit"),
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

    questions = _question_reviews(event, after, scheduled, generated)
    for question in questions:
        if question["status"] != "answered":
            unresolved.append(
                f"[{question['id']}] {question['text']} — "
                f"{_ANSWER_LABELS[question['status']]}：{question['reason']}"
            )
    report = {
        "schema_version": "factwindow.report.v2",
        "generated_at": generated.isoformat(),
        "event_id": event["event_id"],
        "title": event["title"],
        "scheduled_at": event["scheduled_at"],
        "question": event["question"],
        "frozen_at": snapshot["frozen_at"],
        "snapshot_sha256": snapshot["content_sha256"],
        "rows": rows,
        "questions": questions,
        "unresolved": unresolved,
    }
    for field in ("supports_if", "refutes_if", "review_by"):
        if field in event:
            report[field] = event[field]
    if "interpretation" in after:
        report["interpretation"] = _text(after["interpretation"], "interpretation")
    return report


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
    "unit_unconfirmed": "单位尚未确认 / Unit unconfirmed",
    "type_mismatch": "类型不一致 / Type mismatch",
}


_ANSWER_LABELS = {
    "answered": "已有回答 / Answered",
    "pending": "仍待证据 / Pending",
    "conflicting": "存在冲突 / Conflicting",
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
        f"- 对应快照摘要 / Snapshot SHA-256: `{report['snapshot_sha256']}`",
        "",
        "摘要用于关联快照和检查内容一致性，不能证明记录在事前存在，也不能证明来源真伪。 / "
        "The digest links the snapshot and checks content consistency; it does not prove "
        "pre-event existence or source authenticity.",
        "",
    ]
    criteria = [
        ("supports_if", "支持原判断的条件 / Supports if"),
        ("refutes_if", "推翻原判断的条件 / Refutes if"),
        ("review_by", "验证期限 / Review by"),
    ]
    if any(field in report for field, _ in criteria):
        lines.extend(["## 事前判断标准 / Frozen judgment criteria", ""])
        lines.extend(
            f"- {label}: {report[field]}"
            for field, label in criteria if field in report
        )
        lines.append("")
    lines.extend([
        "## 对照结果 / Comparison",
        "",
        "高于或低于预期仅描述数值关系，含义由使用者结合事前标准判断。 / "
        "Above or below describes the numerical comparison; the author interprets its meaning.",
        "",
        "| 指标 / Metric | 预期单位 / Expectation unit | 事实单位 / Fact unit | 前值 / Prior | 预期 / Expected | 实际 / Actual | 差值 / Difference | 结果 / Status |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ])
    for row in report["rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _display(row["metric"]),
                    _display(row["expectation_unit"]),
                    _display(row["fact_unit"]),
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
                f"[{row['metric']}]({row['fact_source_url']}) — "
                f"发布时间 / Published: `{row['published_at']}`"
            )

    if report["questions"]:
        lines.extend([
            "", "## 问题回答 / Question review", "",
            "回答状态由使用者填写，工具检查字段和时间，不验证来源是否支持回答。 / "
            "The author supplies each status; the tool checks fields and times, "
            "not whether a source supports the answer.",
        ])
        for question in report["questions"]:
            lines.extend([
                "", f"### [{question['id']}] {question['text']}", "",
                f"- 状态 / Status: {_ANSWER_LABELS[question['status']]}",
                f"- 理由 / Reason: {question['reason']}",
            ])
            for source in question["sources"]:
                lines.append(
                    f"- 回答来源 / Answer source: [来源 / Source]({source['source_url']}) — "
                    f"发布时间 / Published: `{source['published_at']}`"
                )
    if "interpretation" in report:
        lines.extend(["", "## 使用者解读 / Author interpretation", "", report["interpretation"]])

    lines.extend(["", "## 未解决问题 / Unresolved", ""])
    if report["unresolved"]:
        lines.extend(f"- {item}" for item in report["unresolved"])
    else:
        lines.append("- 暂无 / None recorded.")
    return "\n".join(lines) + "\n"
