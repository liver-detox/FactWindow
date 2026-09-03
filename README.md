# FactWindow

[简体中文](README.zh-CN.md)

**Freeze expectations. Compare sourced facts.**

FactWindow is a small local command-line tool for scheduled events. Write down what you expect before the event, freeze that record, then place published facts beside it afterward. The result is a compact Markdown brief that preserves misses, surprises, and unresolved questions.

The default demo, CLI guidance, and Markdown report use concise Chinese-first bilingual labels. JSON keys and status codes stay in stable English for scripts; human-readable JSON text may be bilingual.

## Try it

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install .
factwindow demo
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.

If FactWindow is already installed, only run the final command: `factwindow demo`.

Open `factwindow-demo/report.md`. The synthetic demo produces:

```text
| 指标 / Metric | 单位 / Unit | 前值 / Prior | 预期 / Expected | 实际 / Actual | 差值 / Difference | 结果 / Status |
|---|---|---:|---:|---:|---:|---|
| 活跃团队数 / active teams | 个团队 / teams | 80 | 100 | 112 | +12 | 高于预期 / Above expectation |
| 发布状态 / launch status | — | — | 按计划 / on track | 延期 / delayed | — | 发生变化 / Changed |
```

After installation, FactWindow itself makes no network requests and needs no account, API key, database, or manual ID copy-back.

## Use your own event

Start from the files in [`examples/synthetic`](examples/synthetic):

```bash
factwindow freeze examples/synthetic/before.toml --output before.snapshot.json
factwindow compare before.snapshot.json examples/synthetic/after.toml --output report
```

Copy both example files, then replace the event details, metrics, values, times, and source links. `freeze` saves the fixed before-event record; `compare` creates the after-event report.

The event time in the before file must still be in the future when you freeze it. After the event, each fact needs an HTTPS source and a publication time at or after the event. The event IDs in both files must match.

The before file records:

- the event ID, title, scheduled time, and research question;
- one or more expected metrics, with optional prior values and units;
- source links and questions that are still unresolved.

The after file records actual values, units, source links, and publication times. FactWindow reports numeric differences, changed text or boolean values, missing facts, extra facts, and unit mismatches without silently discarding them.

Run `factwindow --help`, `factwindow freeze --help`, or `factwindow compare --help` for command details.

## What it is not

FactWindow does not fetch data, judge whether a source is true, make predictions, provide investment advice, or connect to trading accounts. It simply makes a before/after research record easier to inspect.

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

FactWindow uses only the Python standard library at runtime and is licensed under Apache-2.0.
