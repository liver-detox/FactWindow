"""Small fictional inputs used by ``factwindow demo``."""

BEFORE_TOML = '''event_id = "EVT-DEMO-001"
title = "虚构产品更新 / Fictional product update"
scheduled_at = "2099-01-15T13:00:00+00:00"
question = "实际活跃团队数是否超过预期？ / Did active teams exceed the expectation?"
unknowns = ["季节性影响尚未评估。 / Seasonal effects have not been assessed."]
supports_if = "活跃团队数超过100个团队，且统计口径可比。 / Active teams exceed 100 on a comparable basis."
refutes_if = "可比口径下活跃团队数不超过100个团队。 / Active teams do not exceed 100 on a comparable basis."
review_by = "2099-01-22T13:00:00+00:00"

[[questions]]
id = "launch-reason"
text = "若发布延期，原因是什么？ / If the launch is delayed, what is the reason?"

[[questions]]
id = "regional-mix"
text = "活跃团队的地区分布是什么？ / What is the regional mix of active teams?"

[[expectations]]
metric = "活跃团队数 / active teams"
prior = 80
expected = 100
unit = "个团队 / teams"
source_url = "https://example.com/before-event-note"

[[expectations]]
metric = "发布状态 / launch status"
expected = "按计划 / on track"
source_url = "https://example.com/before-event-note"
'''

AFTER_TOML = '''event_id = "EVT-DEMO-001"
interpretation = "活跃团队数超过预期，但发布延期；地区分布仍待证据。以上均为虚构演示。 / Active teams exceeded the expectation, but the launch was delayed; regional mix still awaits evidence. This is entirely fictional."

[[facts]]
metric = "活跃团队数 / active teams"
actual = 112
unit = "个团队 / teams"
source_url = "https://example.com/official-update"
published_at = "2099-01-15T13:05:00+00:00"

[[facts]]
metric = "发布状态 / launch status"
actual = "延期 / delayed"
source_url = "https://example.com/official-update"
published_at = "2099-01-15T13:05:00+00:00"

[[answers]]
question_id = "launch-reason"
status = "answered"
reason = "虚构公告说明，发布因兼容性检查尚未完成而延期。 / The fictional announcement says incomplete compatibility checks delayed the launch."

[[answers.sources]]
source_url = "https://example.com/fictional-launch-note"
published_at = "2099-01-15T13:05:00+00:00"

[[answers]]
question_id = "regional-mix"
status = "pending"
reason = "虚构公告未披露地区分布，仍待后续资料。 / The fictional announcement does not disclose regional mix; further evidence is needed."
'''
