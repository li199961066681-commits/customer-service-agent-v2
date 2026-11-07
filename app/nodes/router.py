# -*- coding: utf-8 -*-
"""节点 ②：条件路由（conditional_edges 的决策函数）。

LangGraph 的 add_conditional_edges 需要「一个函数 + 分支映射表」：
函数返回哪个 key，就走对应节点。这里把意图直接映射到下一节点。"""

from app.state import AgentState


def route_after_classify(state: AgentState) -> str:
    """按意图分流。返回分支名，与 graph.py 中映射表对齐。"""
    return state.intent.intent if state.intent else "faq"


def route_after_check(state: AgentState) -> str:
    """升级判定后的分流：转人工 or 正常回答。"""
    return "escalate" if state.escalation and state.escalation.escalated else "ok"
