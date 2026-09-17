# FactWindow

[简体中文](README.zh-CN.md)

**Freeze expectations. Compare sourced facts.**

FactWindow is a small local command-line tool for scheduled events. Write down what you expect and what evidence would change your view, freeze that record, then place published facts and sourced answers beside it afterward. The result is a compact Markdown brief that preserves misses, surprises, and questions still awaiting evidence.

The default demo, CLI guidance, and Markdown report use concise Chinese-first bilingual labels. JSON keys and status codes stay in stable English for scripts; human-readable JSON text may be bilingual.

## Try it

Requires Python 3.11 or newer.

```bash
git clone https://github.com/liver-detox/FactWindow.git
cd FactWindow
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install .
factwindow demo
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.

If v0.2.0 is already installed, only run the final command: `factwindow demo`. To upgrade an older installation, open your original clean checkout, activate its environment, then run:

```bash
git pull --ff-only
python3 -m pip install .
factwindow --version
```

The version command should display `0.2.0`. If the checkout contains your own changes, keep them safe and install from a separate clean clone.

Open `factwindow-demo/report.md`. The synthetic demo produces:

```text
| 指标 / Metric | 预期单位 / Expectation unit | 事实单位 / Fact unit | 前值 / Prior | 预期 / Expected | 实际 / Actual | 差值 / Difference | 结果 / Status |
|---|---|---|---:|---:|---:|---:|---|
| 活跃团队数 / active teams | 个团队 / teams | 个团队 / teams | 80 | 100 | 112 | +12 | 高于预期 / Above expectation |
| 发布状态 / launch status | — | — | — | 按计划 / on track | 延期 / delayed | — | 发生变化 / Changed |
```

The report also shows one sourced answer, one question still awaiting evidence, source publication times, and the frozen snapshot digest. Everything in the demo is fictional; its `example.com` links are placeholders and its 2099 timeline uses a simulated clock.

After installation, FactWindow itself makes no network requests and needs no account, API key, or database.

## Use your own event

Follow the [first-event guide](docs/first-event.md#english) to copy the example files into `my-event` and replace the event, future schedule, expectations, questions, and source links. Then, **before the event**:

```bash
factwindow freeze my-event/before.toml --output my-event/before.snapshot.json
```

**After the event and after sources are published**, fill in `my-event/after.toml` and run:

```bash
factwindow compare my-event/before.snapshot.json my-event/after.toml --output my-event/report
```

Open `my-event/report/report.md`. Keep the frozen snapshot for later comparisons. Do not directly run the unedited 2099 example's `after.toml` through `compare` today: normal commands use the real clock, so future facts are rejected. `factwindow demo` is the immediate, simulated walkthrough.

Every fact and answer source needs an HTTPS URL and a timezone-aware publication time between the event time and the report generation time, inclusive. Both files must have the same event ID.

The before file records:

- the event ID, title, scheduled time, and research question;
- one or more expected metrics, with optional prior values and units;
- source links and optional questions with stable IDs;
- optional support/refutation conditions and a review deadline.

The after file records actual values, units, publication times, and optional answers marked `answered`, `pending`, or `conflicting`. Answered and conflicting entries require a reason and at least one dated source. Omitted answers remain pending; original questions stay visible. Optional `interpretation` records your own assessment. Legacy `unknowns` remain unresolved notes; use `questions` for items you want to answer individually.

FactWindow keeps missing facts and extra facts visible. It stops calculation for conflicting units, a unit missing on one side, or incompatible value types. Two numeric values without declared units can still be compared. “Above expectation” describes a numerical relationship; it does not mean a better outcome. See the [input and report specification](docs/spec.md) and [v0.2.0 changes](CHANGELOG.md).

Run `factwindow --help`, `factwindow freeze --help`, or `factwindow compare --help` for command details.

## What it is not

FactWindow does not fetch data, judge whether a source is true, make predictions, provide investment advice, or connect to trading accounts. Answers and interpretation are supplied by the user. The local SHA-256 digest helps associate a report with a snapshot and check consistency; it is not a trusted timestamp or proof that the snapshot existed before the event. It does not authenticate sources.

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

FactWindow uses only the Python standard library at runtime and is licensed under Apache-2.0.
