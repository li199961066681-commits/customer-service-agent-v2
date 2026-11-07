# -*- coding: utf-8 -*-
"""评测用例：12 条，覆盖 5 类意图 + 三层防御 + 边界场景。

每条用例判定两点：
- route 正确（走了正确的状态机分支）
- 回复包含关键内容（must_contain 任意命中即算）
"""

TEST_CASES = [
    # ---- faq：知识库检索 ----
    {"id": "E01", "input": "订单超过7天没收到货怎么办", "route": "faq",
     "must_contain": ["【资料", "物流"]},
    {"id": "E02", "input": "退款规则是什么", "route": "faq",
     "must_contain": ["【资料", "退款"]},
    {"id": "E03", "input": "发票怎么开", "route": "faq",
     "must_contain": ["【资料", "发票"]},
    {"id": "E04", "input": "退货要多久", "route": "faq",
     "must_contain": ["【资料", "退货"]},
    # ---- action：工具调用 ----
    {"id": "E05", "input": "帮我查一下工单TK001", "route": "action",
     "must_contain": ["TK001"]},
    {"id": "E06", "input": "帮我改一下工单TK001状态为已完成", "route": "action",
     "must_contain": ["状态"]},
    {"id": "E07", "input": "帮我建个工单，我叫王五，手机坏了", "route": "action",
     "must_contain": ["工单"]},
    # ---- clarify：澄清追问 ----
    {"id": "E08", "input": "我要退款", "route": "clarify",
     "must_contain": ["订单号"]},
    # ---- human：无条件转人工 ----
    {"id": "E09", "input": "你们就是骗子我要投诉曝光你们", "route": "human",
     "must_contain": ["人工"]},
    # ---- other：兜底 ----
    {"id": "E10", "input": "今天天气怎么样", "route": "other",
     "must_contain": ["客服助手"]},
    # ---- 边界：知识库未覆盖的 faq → 检索无依据 → 拒答转人工（层1 confidence）----
    {"id": "E11", "input": "你们支持货到付款吗", "route": "faq",
     "escalate_layer": "confidence", "must_contain": ["人工"]},
    # ---- 边界：情绪词 → 无条件转人工（层3 sensitive / human）----
    {"id": "E12", "input": "太垃圾了我要给你们差评", "route": "human",
     "must_contain": ["人工"]},
]
