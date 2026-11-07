# -*- coding: utf-8 -*-
"""节点 ⑧：转人工（human 分支 + 升级判定命中）。

把 对话历史 + 实体 + 升级原因 打包，写入 SQLite 坐席队列，
并给用户一个体面的转人工回复（兜底能力 = 产品思维）。
"""

from app.state import AgentState
from memory.long_term import TicketStore


def escalate_human_node(state: AgentState) -> dict:
    store = TicketStore()
    escalation = state.escalation
    reason = escalation.reason if escalation else "用户诉求需人工介入"
    layer = escalation.layer if escalation else "intent_classify"

    payload = {
        "user_input": state.user_input,
        "intent": state.intent.model_dump() if state.intent else None,
        "tool_result": state.tool_result,
        "escalation_layer": layer,
    }
    store.enqueue_escalation("UNKNOWN", reason, payload)

    reply = (
        "非常抱歉给您带来不好的体验。您的问题已升级给人工专员处理"
        "（已进入坐席队列，专员会在 24 小时内联系您）。请问还有其他可以帮您的吗？"
    )
    return {"reply": reply}
