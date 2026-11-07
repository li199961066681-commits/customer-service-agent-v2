# -*- coding: utf-8 -*-
"""节点 ⑨：兜底回答（other 分支）。

闲聊/超纲问题：礼貌引导回业务，不强行作答。
"""

from app.state import AgentState


def fallback_node(state: AgentState) -> dict:
    return {"reply": "我是客服助手，主要处理订单、退款、物流、发票、保修等问题。请问有什么可以帮您？"}
