# 首次记录自己的事件 / Your first event

这份指南适用于已安装的 FactWindow v0.2.0。只想立即看效果，请运行 `factwindow demo`；该演示使用虚构资料和固定的 2099 年模拟时钟。普通 `freeze` 和 `compare` 使用真实当前时间。

## 中文

### 1. 选一个还没发生的公开事件

选择一个有明确计划时间、后续能取得公开来源的事件。先用少量指标和一两个问题，把完整流程走通。

在项目目录中复制两份示例。macOS/Linux 可运行：

```bash
mkdir -p my-event
cp examples/synthetic/before.toml my-event/before.toml
cp examples/synthetic/after.toml my-event/after.toml
```

Windows 也可以用文件管理器新建 `my-event` 文件夹，将两份文件复制进去。

### 2. 填写事前记录，然后冻结

编辑 `my-event/before.toml`，将全部虚构内容换成自己的记录：

| 要修改的内容 | 填写方式 |
|---|---|
| `event_id`、`title`、`question` | 自定编号、标题和研究问题；事后文件使用相同编号 |
| `scheduled_at` | 真实的未来事件时间，保留引号并写明时区，例如 `+08:00` |
| `expectations` | 预期指标、数值、可选前值、单位和事前 HTTPS 来源 |
| `questions` | 用简短唯一编号记录想在事后回答的问题 |
| `supports_if`、`refutes_if` | 什么结果会支持或否定原判断；可删除不用的字段 |
| `review_by` | 不早于事件的复盘期限，可省略；不会自动提醒 |
| `unknowns` | 保留不需要逐题回答的备注；需要闭合的问题放进 `questions` |

事前文件不应包含事后才知道的结果。`expected = 100` 是数字，`expected = "100"` 是文字，请按实际含义填写。单位不会自动换算，“个团队”和“teams”会被视为不同单位。

准备好后，在事件发生前运行：

```bash
factwindow freeze my-event/before.toml --output my-event/before.snapshot.json
```

保留生成的快照。后续修改 `before.toml` 不会改变已冻结的快照。快照摘要帮助检查内容一致性，不能证明记录在事件前存在。

### 3. 等事件发生，再填公开事实与回答

不要直接沿用演示的实际值、2099 年时间或 `example.com` 链接。等事件发生且来源发布后，编辑 `my-event/after.toml`：

- 将 `event_id` 改为与快照一致。
- 逐项填写 `facts` 的实际值和单位，指标名称须与事前完全一致；多出的指标会显示为额外事实。
- 写明实际使用的 HTTPS 来源及其发布时间。每个时间必须带时区，并满足“事件时间 ≤ 发布时间 ≤ 当前报告生成时间”。
- `answers.question_id` 对应事前问题的 `id`。`answered` 和 `conflicting` 都需要理由及至少一个 `[[answers.sources]]` 来源；`pending` 可不附来源。未填写的答案自动保持待证据。
- 在顶层 `interpretation` 写自己的解读，或删除该字段。数值高于预期不自动代表结果更好。

事件已发生但暂时没有事实时，可将事后文件简化为以下内容，替换事件编号后再运行对照：

```toml
event_id = "YOUR_EVENT_ID"
facts = []
interpretation = "事件已发生，尚未取得可核验的公开事实。"
```

这会保留缺失事实和待证据问题。不要把“未取得证据”填写成零、否定答案或预期落空。

TOML 顶层字段应放在第一个 `[[...]]` 表格之前；否则它们会属于前面的表格。例如 `interpretation` 要放在文件顶部，不能直接追加在最后一个事实之后。

### 4. 对照并复盘

```bash
factwindow compare my-event/before.snapshot.json my-event/after.toml --output my-event/report
```

打开 `my-event/report/report.md`。检查事实及来源时间、两侧单位、逐题回答和未解决事项，再结合事前条件写出自己的结论。若仍缺单位或数值类型不一致，先核实资料并修正事后输入；不要修改冻结预期来迁就实际值。

有新证据后可再次运行对照。使用新的输出目录（如 `my-event/report-2`）可以保留前次报告。程序不会验证来源真伪或自动安排复盘；`review_by` 仅供你查看。

## English

### 1. Choose an upcoming public event

Pick an event with a scheduled time and an expected public source. Start with a few metrics and one or two questions. From the checkout, copy both files in `examples/synthetic` into a new `my-event` directory using the commands above or a file manager.

### 2. Record expectations and freeze before the event

Replace every fictional value in `my-event/before.toml`: event ID, title, research question, actual future schedule with timezone, expected metrics, units, and HTTPS sources. Give each optional question a unique ID. Optional `supports_if`, `refutes_if`, and `review_by` record your criteria and review deadline; the deadline must be at or after the event and does not schedule a reminder. Use `questions` for items you intend to answer; legacy `unknowns` remain unresolved notes.

Keep numeric inputs numeric: `100` and `"100"` have different types. Units match exactly and are not converted. Do not include outcomes only known after the event.

```bash
factwindow freeze my-event/before.toml --output my-event/before.snapshot.json
```

Keep the snapshot. Editing the input TOML does not update it. Its digest checks consistency but does not prove pre-event existence.

### 3. Wait for the event and published evidence

Replace the fictional contents of `my-event/after.toml`. Keep the same event ID and metric names. Enter actual values, units, HTTPS sources, and timezone-aware publication times. Every fact and answer source must satisfy `scheduled_at <= published_at <= generated_at`.

Optional answers refer to frozen question IDs. `answered` and `conflicting` require a reason and at least one `[[answers.sources]]` entry; `pending` can omit sources. Unanswered questions remain pending. Optional top-level `interpretation` records your own assessment; higher numbers are not automatically better outcomes.

If the event has occurred but evidence is unavailable, use the minimal `facts = []` example above with your own event ID and interpretation. Missing evidence is not a zero, a negative answer, or a failed expectation. Put top-level TOML fields before the first `[[...]]` table.

### 4. Compare and review

```bash
factwindow compare my-event/before.snapshot.json my-event/after.toml --output my-event/report
```

Open `my-event/report/report.md`. Check source times, both units, question answers, and unresolved items against your frozen criteria. Resolve unit/type issues from evidence; do not change frozen expectations to fit the outcome. Use a new output directory for each later review if you want to retain earlier reports.

The unedited 2099 demo after-file cannot be compared using today's real clock. Use `factwindow demo` for an immediate simulated walkthrough. FactWindow does not authenticate sources or schedule reviews.
