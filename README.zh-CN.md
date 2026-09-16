# FactWindow

[English](README.md)

**事前冻结预期，事后对照有来源的事实。**

FactWindow 是一个用于计划事件的小型本地命令行工具。你可以在事件发生前写下预期并冻结记录，事件发生后再把公开事实放到旁边。它会生成一份简洁的 Markdown 简报，把落差、意外和未解决问题都保留下来。

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

如果已经安装过 FactWindow，只需运行最后一行：`factwindow demo`。

打开 `factwindow-demo/report.md`。内置合成示例会生成类似结果：

```text
| 指标 / Metric | 单位 / Unit | 前值 / Prior | 预期 / Expected | 实际 / Actual | 差值 / Difference | 结果 / Status |
|---|---|---:|---:|---:|---:|---|
| 活跃团队数 / active teams | 个团队 / teams | 80 | 100 | 112 | +12 | 高于预期 / Above expectation |
| 发布状态 / launch status | — | — | 按计划 / on track | 延期 / delayed | — | 发生变化 / Changed |
```

安装完成后，FactWindow 本身不发起网络请求，也不需要账户、API 密钥、数据库或手动复制编号。

## 用于自己的事件

可以从 [`examples/synthetic`](examples/synthetic) 中的文件开始：

```bash
factwindow freeze examples/synthetic/before.toml --output before.snapshot.json
factwindow compare before.snapshot.json examples/synthetic/after.toml --output report
```

复制这两个示例文件，再替换事件信息、指标、数值、时间和来源链接即可。`freeze` 负责固定事前记录，`compare` 负责生成事后对照报告。

冻结时，事前文件中的事件时间必须仍在未来。事件发生后，每条事实都需要 HTTPS 来源，以及不早于事件时间的发布时间。两个文件中的事件编号必须一致。

事前文件记录：

- 事件编号、标题、计划时间和研究问题；
- 一个或多个预期指标，可带前值和单位；
- 来源链接和尚未解决的问题。

事后文件记录实际值、单位、来源链接和发布时间。FactWindow 会显示数值差异、文本或布尔值变化、缺失事实、额外事实和单位不一致，不会把它们悄悄丢掉。

### 常用字段

| 文件字段 | 含义 |
|---|---|
| `event_id` | 事件编号，事前和事后必须相同 |
| `expected` | 预期值 |
| `actual` | 实际值 |
| `prior` | 事前已有值，可以省略 |
| `source_url` | 来源链接 |
| `published_at` | 事实的发布时间 |

### 常见问题

- 冻结失败：事件时间必须在当前时间之后。
- 时间格式错误：加上时区，例如 `+08:00`。
- 无法对照：确保两个文件的 `event_id` 完全一致。

可运行 `factwindow --help`、`factwindow freeze --help` 或 `factwindow compare --help` 查看命令说明。

## 它不做什么

FactWindow 不抓取数据，不判断来源真假，不做预测或投资建议，也不连接交易账户。它只负责把事前与事后的研究记录清楚地并排呈现。

## 开发测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

FactWindow 运行时仅使用 Python 标准库，并采用 Apache-2.0 许可证。
