# -*- coding: utf-8 -*-
"""LangGraph 状态机构建：8 个执行节点 + 2 处条件路由 + 入口。

     START
       │
       ▼
  ① classify_intent ──conditional──► faq    → ③ rag_search ─┐
       │                            action  → ④ tool_call  ─┤
       │                            clarify → ⑤ clarify → END
       │                            human   → ⑧ escalate_human → END
       │                            other   → ⑨ fallback → END
       │                                                      ▼
       │                                              ⑦ respond（生成拟回复）
       │                                                      ▼
       │                                              ⑥ escalate_check ─conditional─► escalate → ⑧ escalate_human → END
       │                                                      │
       │                                                      └─ ok → 输出回复 → END
"""

from langgraph.graph import END, START, StateGraph

from app.nodes.classify_intent import classify_intent
from app.nodes.clarify import clarify_node
from app.nodes.escalate_check import escalate_check_node
from app.nodes.escalate_human import escalate_human_node
from app.nodes.fallback import fallback_node
from app.nodes.rag_search import rag_search_node
from app.nodes.respond import respond_node
from app.nodes.router import route_after_check, route_after_classify
from app.nodes.tool_call import tool_call_node
from app.state import AgentState


def build_graph():
    g = StateGraph(AgentState)

    # 注册 8 个执行节点（条件路由不是 node）
    g.add_node("classify_intent", classify_intent)
    g.add_node("rag_search", rag_search_node)
    g.add_node("tool_call", tool_call_node)
    g.add_node("clarify", clarify_node)
    g.add_node("fallback", fallback_node)
    g.add_node("respond", respond_node)
    g.add_node("escalate_check", escalate_check_node)
    g.add_node("escalate_human", escalate_human_node)

    # 入口
    g.add_edge(START, "classify_intent")

    # ② 条件路由：意图 → 分支
    g.add_conditional_edges(
        "classify_intent",
        route_after_classify,
        {
            "faq": "rag_search",
            "action": "tool_call",
            "clarify": "clarify",
            "human": "escalate_human",
            "other": "fallback",
        },
    )

    # 检索/工具 → 回答合成
    g.add_edge("rag_search", "respond")
    g.add_edge("tool_call", "respond")

    # 简单分支直接结束
    g.add_edge("clarify", END)
    g.add_edge("fallback", END)

    # 回答合成 → 升级判定 → 分流
    g.add_edge("respond", "escalate_check")
    g.add_conditional_edges(
        "escalate_check",
        route_after_check,
        {"escalate": "escalate_human", "ok": END},
    )
    g.add_edge("escalate_human", END)

    return g.compile()


agent = build_graph()
