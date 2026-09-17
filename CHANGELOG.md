# Changelog

## 0.2.0 — 2026-09-17

### 中文

- 报告拒绝尚未发布的事实和回答来源，要求事件时间 ≤ 来源发布时间 ≤ 报告生成时间；事件前不能生成事后报告。
- 显示来源发布时间、冻结快照摘要和两侧单位。一侧漏填单位时标记 `unit_unconfirmed`，类型不兼容时标记 `type_mismatch`，均停止该行计算。
- 新增可选的带编号事前问题与有来源的逐题回答。未填写的答案保持待证据；已有回答保留原题并从未解决清单移出；冲突答案仍列为未解决。
- 新增可选的支持条件、否定条件、复盘期限和使用者解读，不自动判断投资意义或假设是否成立。
- 事件已发生但暂无资料时，允许 `facts = []` 生成缺失事实报告。
- 更新中英文说明和独立虚构演示，新增首次记录自己的事件指南。
- 对数值差值溢出和畸形来源链接给出字段错误，避免报告生成时崩溃。
- 新增 `--version`，并配置 Python 3.11 / 3.14 的自动测试及安装演示。

新冻结写入 `factwindow.snapshot.v2`；继续读取 v1 快照，不修改旧快照。新报告为 `factwindow.report.v2`，程序读取方应适配新增状态、两侧单位字段和问题回答字段。旧输入中未来的来源时间现在会被拒绝；一侧缺单位和异类型数值不再进行普通比较。

来源时间与内容均由使用者提供，未验证来源真伪。快照摘要只关联记录并检查一致性，不能证明记录在事件前存在。

### English

- Reject future-dated facts and answer sources: event time ≤ source publication time ≤ report generation time. Reports cannot be generated before the event.
- Display source publication times, the frozen snapshot digest, and both units. Stop row calculation for a one-sided unit omission (`unit_unconfirmed`) or incompatible value categories (`type_mismatch`).
- Add optional frozen question IDs and sourced answers. Omitted answers stay pending. Answered questions preserve their original text but leave the unresolved list; conflicting answers remain unresolved.
- Add optional support/refutation conditions, a review deadline, and user interpretation without automatic hypothesis scoring or investment judgments.
- Accept `facts = []` after the event to report that facts are still missing.
- Refresh the bilingual documentation and independently fictional demo; add a first-event guide.
- Report field errors for overflowing numeric differences and malformed source URLs instead of crashing during report generation.
- Add `--version` and automated tests plus installation demos on Python 3.11 and 3.14.

New freezes use `factwindow.snapshot.v2`; v1 snapshots remain readable and are not rewritten. New reports use `factwindow.report.v2`. Consumers should handle new statuses, separate unit fields, and question answers. Previously accepted future-dated evidence is now rejected. One-sided unit omissions and incompatible types no longer produce normal comparisons.

Source times and content are user-supplied and unverified. A snapshot digest associates records and checks consistency; it does not prove pre-event existence or source truth.
