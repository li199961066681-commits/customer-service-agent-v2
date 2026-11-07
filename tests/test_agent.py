# -*- coding: utf-8 -*-
"""单元测试：状态机路由 / 三层防御 / 工具 / 存储 / 检索 / 记忆。

运行：python -m pytest tests -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app.graph import agent
from app.nodes.escalate_check import escalate_check_node
from app.safety import hit_sensitive
from app.state import AgentState, EscalationResult, IntentResult, KbHit
from config import GROUNDED_THRESHOLD, LLM_READY
from memory.long_term import TicketStore
from memory.short_term import ShortTermMemory
from retrieval.search import search
from tools.registry import build_tools

requires_llm = pytest.mark.skipif(not LLM_READY, reason="需要真实 LLM_API_KEY")


# ---------- 1. 状态机路由：五类意图（需要真实 LLM）----------
@requires_llm
def test_route_faq():
    out = AgentState.model_validate(agent.invoke(AgentState(user_input="退款规则是什么")))
    assert out.route == "faq"
    assert out.reply and "【资料" in out.reply


@requires_llm
def test_route_action():
    out = AgentState.model_validate(agent.invoke(AgentState(user_input="帮我查一下工单TK001")))
    assert out.route == "action"
    assert "TK001" in (out.reply or "")


@requires_llm
def test_route_clarify():
    out = AgentState.model_validate(agent.invoke(AgentState(user_input="我要退款")))
    assert out.route == "clarify"
    assert "订单号" in (out.reply or "")


@requires_llm
def test_route_human():
    out = AgentState.model_validate(agent.invoke(AgentState(user_input="你们就是骗子我要投诉")))
    assert out.route == "human"
    assert "人工" in (out.reply or "")


@requires_llm
def test_route_other():
    out = AgentState.model_validate(agent.invoke(AgentState(user_input="今天天气怎么样")))
    assert out.route == "other"


# ---------- 2. 三层防御 ----------
def test_confidence_escalation():
    """层1：faq 分支没有任何 grounded 命中 → 拒答转人工（不依赖 LLM）。"""
    out = escalate_check_node(AgentState(
        user_input="你们支持货到付款吗",
        route="faq",
        kb_results=[],
        draft_reply="抱歉，这个问题我暂时无法确认。",
    ))
    assert out["escalation"].escalated
    assert out["escalation"].layer == "confidence"


@requires_llm
def test_sensitive_escalation():
    """情绪词：走 human 分支无条件转人工。"""
    out = AgentState.model_validate(agent.invoke(AgentState(user_input="太垃圾了我要差评")))
    assert out.route == "human"
    assert "人工" in (out.reply or "")


@requires_llm
def test_self_check_escalation():
    """层2 self_check：拟回复不带引用 → NOT_OK → 转人工。"""
    state = AgentState(
        user_input="退款规则是什么", route="faq",
        kb_results=[KbHit(id="KB01", title="退款规则", content="退款规则内容",
                          score=0.9, grounded=True)],
        draft_reply="您好，可以退款。",  # 无【资料N】引用
    )
    out = escalate_check_node(state)
    assert out["escalation"].escalated
    assert out["escalation"].layer == "self_check"


# ---------- 3. 工具 ----------
def test_tool_query_ticket():
    tools = build_tools()
    res = tools["query_ticket"](ticket_id="TK001")
    assert '"found": true' in res


def test_tool_create_and_update():
    tools = build_tools()
    created = tools["create_ticket"](user_name="测试", title="测试工单")
    import json
    ticket_id = json.loads(created)["id"]
    updated = tools["update_ticket_status"](ticket_id=ticket_id, status="已完成")
    assert '"ok": true' in updated


def test_tool_rag_search():
    tools = build_tools()
    res = tools["rag_search"](query="退款规则")
    assert '"results"' in res


# ---------- 4. 检索 ----------
def test_search_grounded():
    hits = search("退款规则是什么", top_k=3, threshold=GROUNDED_THRESHOLD)
    assert hits and hits[0].id == "KB01"
    assert hits[0].grounded


def test_search_low_similarity():
    hits = search("帮我写一首诗", top_k=3, threshold=GROUNDED_THRESHOLD)
    assert all(not h.grounded for h in hits)


# ---------- 5. 存储 ----------
def test_ticket_store(tmp_path):
    store = TicketStore(tmp_path / "t.db")
    created = store.create_ticket("张三", "订单异常")
    row = store.query_ticket(created["id"])
    assert row and row["status"] == "待处理"
    store.update_ticket_status(created["id"], "已完成")
    assert store.query_ticket(created["id"])["status"] == "已完成"
    q = store.enqueue_escalation(created["id"], "测试升级", {"k": "v"})
    assert q["status"] == "已进入坐席队列"
    assert store.list_queue()
    store.close()


# ---------- 6. 短期记忆 ----------
def test_short_term_memory():
    mem = ShortTermMemory()
    mem.add_user("s1", "你好")
    mem.add_assistant("s1", "您好")
    hist = mem.history("s1")
    assert len(hist) == 2
    assert hist[-1]["role"] == "assistant"
    mem.clear("s1")
    assert mem.history("s1") == []


# ---------- 7. 安全词表（不依赖 LLM）----------
def test_safety_words():
    assert hit_sensitive("你们就是骗子") is True
    assert hit_sensitive("太垃圾了我要差评") is True
    assert hit_sensitive("今天天气怎么样") is False


# ---------- 8. 统一执行入口：只跑一次 / 多轮记忆接线 ----------
def test_run_once_calls_agent_once(monkeypatch):
    """run_once 只调用一次 run_agent，避免 stream + invoke 双执行。"""
    import main

    calls = []

    def fake_run_agent(state, trace=None):
        calls.append(state)
        return AgentState(user_input=state.user_input, reply="ok"), ["fake_node"]

    monkeypatch.setattr(main, "run_agent", fake_run_agent)
    out = main.run_once("帮我建个工单", memory=None, verbose=False)

    assert len(calls) == 1
    assert out.reply == "ok"


@requires_llm
def test_run_once_loads_history():
    """第二轮应带上第一轮的 user/assistant 消息，turn 递增（需要真实 Key）。"""
    from main import run_once

    mem = ShortTermMemory()
    sid = "history-test"
    run_once("我要退款", session_id=sid, memory=mem, verbose=False)
    second = run_once("我的订单号是88888888", session_id=sid, memory=mem, verbose=False)

    assert second.messages, "第二轮 messages 不应为空"
    assert second.messages[-1]["role"] == "assistant"
    assert second.turn >= 2
