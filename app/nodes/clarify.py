# -*- coding: utf-8 -*-
"""节点 ⑤：澄清追问（clarify 分支）。

缺槽位（如 order_id）时反问用户，而不是瞎猜或强行执行。
"""

from app.state import AgentState


def clarify_node(state: AgentState) -> dict:
    missing = (state.intent.missing_slots if state.intent else []) or ["相关信息"]
    slots = "、".join(missing)
    reply = (
        f"为了更快帮您处理，还需要您补充以下信息：{slots}。"
        f"（例如：您的订单号是多少？）"
    )
    return {"reply": reply}
