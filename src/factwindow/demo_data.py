"""Small fictional inputs used by ``factwindow demo``."""

BEFORE_TOML = '''event_id = "EVT-DEMO-001"
title = "虚构产品更新 / Fictional product update"
scheduled_at = "2099-01-15T13:00:00+00:00"
question = "实际活跃团队数是否超过预期？ / Did active teams exceed the expectation?"
unknowns = ["地区分布尚未披露。 / Regional mix is not yet disclosed."]

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
'''
