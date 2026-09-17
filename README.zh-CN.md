# FactWindow

[English](README.md)

**事前冻结预期，事后对照有来源的事实。**

FactWindow 是一个用于计划事件的小型本地命令行工具。你可以在事件发生前写下预期、问题和改变判断的条件并冻结记录，事件发生后再补充公开事实与有来源的回答。它会生成一份简洁的 Markdown 简报，把落差、意外和仍待证据的问题保留下来。

默认演示、命令提示和 Markdown 报告均采用“中文在前、英文在后”的简短对照。JSON 字段和状态码保持英文，便于程序处理；面向人阅读的 JSON 文字可能为中英双语。

## 立即体验

需要 Python 3.11 或更高版本。

```bash
git clone https://github.com/liver-detox/FactWindow.git
cd FactWindow
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install .
factwindow demo
```

Windows PowerShell 用户可改用 `.venv\Scripts\Activate.ps1` 激活环境。

如果已安装 v0.2.0，只需运行最后一行：`factwindow demo`。从旧版升级时，请进入原来的干净克隆目录，激活原环境后运行：

```bash
git pull --ff-only
python3 -m pip install .
factwindow --version
```

版本命令应显示 `0.2.0`。如果目录中有你自己的修改，请保留它们，另建一个干净克隆目录安装。

打开 `factwindow-demo/report.md`。内置合成示例会生成类似结果：

```text
| 指标 / Metric | 预期单位 / Expectation unit | 事实单位 / Fact unit | 前值 / Prior | 预期 / Expected | 实际 / Actual | 差值 / Difference | 结果 / Status |
|---|---|---|---:|---:|---:|---:|---|
| 活跃团队数 / active teams | 个团队 / teams | 个团队 / teams | 80 | 100 | 112 | +12 | 高于预期 / Above expectation |
| 发布状态 / launch status | — | — | — | 按计划 / on track | 延期 / delayed | — | 发生变化 / Changed |
```

报告还会展示一个有来源的回答、一个仍待证据的问题、来源发布时间和冻结快照摘要。演示内容完全虚构，`example.com` 是占位链接；2099 年的时间线通过模拟时钟运行。

安装完成后，FactWindow 本身不发起网络请求，也不需要账户、API 密钥或数据库。

## 用于自己的事件

按[首次记录自己的事件](docs/first-event.md)说明，将示例复制到 `my-event`，替换事件、未来时间、预期、问题和来源。然后在**事件发生前**运行：

```bash
factwindow freeze my-event/before.toml --output my-event/before.snapshot.json
```

**事件发生且来源发布后**，填写 `my-event/after.toml`，再运行：

```bash
factwindow compare my-event/before.snapshot.json my-event/after.toml --output my-event/report
```

打开 `my-event/report/report.md`。保留冻结快照，后续可用新资料再次对照。不要直接用未经修改的 2099 年示例 `after.toml` 在今天运行 `compare`：普通命令使用真实时钟，会拒绝未来事实。若想立即体验完整流程，请用 `factwindow demo`。

冻结时，事件时间必须仍在未来。每条事实和回答来源都需要 HTTPS 链接及带时区的发布时间，且必须满足“事件时间 ≤ 发布时间 ≤ 报告生成时间”。两个文件中的事件编号必须一致。

事前文件记录：

- 事件编号、标题、计划时间和研究问题；
- 一个或多个预期指标，可带前值和单位；
- 来源链接、可选的带编号问题；
- 可选的支持条件、否定条件和复盘期限。

事后文件记录实际值、单位、来源时间，以及可选的逐题回答：“已有回答”（`answered`）、“仍待证据”（`pending`）、“存在冲突”（`conflicting`）。已有回答和存在冲突都必须附理由和至少一个带时间的来源。未填写的答案自动保持待证据，原题始终保留；可选的 `interpretation` 记录你自己的解读。旧版 `unknowns` 仍作为未解决备注保留，需要逐项回答的内容请使用 `questions`。

缺失事实和额外事实都会保留。单位不同、一侧漏填单位或数值类型不兼容时，该行停止计算；两侧均不填单位的数字仍可比较。“高于预期”仅表示数值关系，并不等于结果更好。详细规则见[输入与报告规范](docs/spec.md)和 [v0.2.0 更新说明](CHANGELOG.md)。

### 常用字段

| 文件字段 | 含义 |
|---|---|
| `event_id` | 事件编号，事前和事后必须相同 |
| `expected` | 预期值 |
| `actual` | 实际值 |
| `prior` | 事前已有值，可以省略 |
| `source_url` | 来源链接 |
| `published_at` | 事实的发布时间 |
| `questions` / `answers` | 事前问题与事后回答，通过问题编号对应 |
| `supports_if` / `refutes_if` | 什么结果支持或否定事前判断，可省略 |
| `review_by` | 复盘期限，必须不早于事件时间，可省略 |
| `interpretation` | 使用者的事后解读，可省略 |

### 常见问题

- 冻结失败：事件时间必须在当前时间之后。
- 时间格式错误：加上时区，例如 `+08:00`。
- 无法对照：确保两个文件的 `event_id` 完全一致。
- 事实来自未来：核对来源发布时间；必须等待来源发布后再生成报告。
- 单位尚未确认：补齐事后单位并核对口径，不要为了通过比较而删除事前单位。
- 暂时没有事实：删除示例事实，在事后文件顶层写 `facts = []`；事件发生后可以生成一份缺失事实、仍待证据的报告。

可运行 `factwindow --help`、`factwindow freeze --help` 或 `factwindow compare --help` 查看命令说明。

## 它不做什么

FactWindow 不抓取数据，不判断来源真假，不做预测或投资建议，也不连接交易账户。回答状态和解读由使用者填写。本地 SHA-256 摘要用于关联报告与快照、检查内容一致性；它不是可信时间戳，不能证明快照确实在事件前存在，也不能认证来源真伪。

## 开发测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

FactWindow 运行时仅使用 Python 标准库，并采用 Apache-2.0 许可证。
