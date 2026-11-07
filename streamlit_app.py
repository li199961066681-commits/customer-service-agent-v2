# -*- coding: utf-8 -*-
"""Web 对话界面（Streamlit）。

- 主入口：浏览器里直接对话，不需要在 cmd 里输入问题
- 没有 LLM_API_KEY 时直接阻断，不输出任何假回答
- 每轮展示：意图、节点轨迹、检索命中、升级判定
"""

import uuid

import streamlit as st

from config import LLM_MODEL, LLM_READY

st.set_page_config(page_title="客服工单处理 Agent", page_icon="🤖", layout="wide")

if not LLM_READY:
    st.error("未配置 LLM_API_KEY，Agent 无法回答。")
    st.markdown("请用记事本打开项目根目录的 `.env`，填写你自己的 DeepSeek Key：")
    st.code("LLM_API_KEY=sk-你的Key", language="ini")
    st.info("保存后重新双击“启动网页.bat”。没有 Key 时不会启动对话，也不会输出假回答。")
    st.stop()

from app.runner import run_agent
from app.state import AgentState
from memory.short_term import ShortTermMemory
from observable.langfuse import create_trace

st.title("客服工单处理 Agent")
st.caption("LangGraph 状态机 · 真实 DeepSeek · 只基于知识库回答，超出范围转人工")

# ---------- 会话状态 ----------
if "memory" not in st.session_state:
    st.session_state.memory = ShortTermMemory()
if "session_id" not in st.session_state:
    st.session_state.session_id = f"web-{uuid.uuid4().hex[:8]}"
if "history" not in st.session_state:
    st.session_state.history = st.session_state.memory.history(st.session_state.session_id)

mem = st.session_state.memory
sid = st.session_state.session_id
history = st.session_state.history

# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("运行状态")
    st.success(f"模型：{LLM_MODEL}")
    st.write("短期记忆：", "Redis" if mem.using_redis else "进程内 dict（Redis 未启动）")
    st.caption(f"session: {sid}")
    if st.button("清空会话"):
        mem.clear(sid)
        st.session_state.history = []
        st.session_state.session_id = f"web-{uuid.uuid4().hex[:8]}"
        st.rerun()
    st.divider()
    st.markdown("**回答规则**")
    st.markdown("- 只使用 8 条知识库资料\n- 必须有【资料N】引用\n- 没依据/情绪激烈 → 转人工")

# ---------- 历史消息 ----------
for msg in history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------- 输入 ----------
prompt = st.chat_input("请输入您的问题，例如：退款规则是什么")
if prompt:
    prompt = prompt.strip()
    if not prompt:
        st.stop()

    # 先取历史（不含本轮），再写当前用户消息
    prior = mem.history(sid)
    mem.add_user(sid, prompt)

    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    state = AgentState(
        user_input=prompt,
        session_id=sid,
        messages=prior,
        turn=len(prior) // 2 + 1,
    )
    trace = create_trace("客服对话", sid)
    try:
        with st.spinner("Agent 正在处理..."):
            out, node_trace = run_agent(state, trace)
    except Exception as e:
        st.error(f"调用失败：{e}")
        st.info("请检查 .env 的 LLM_API_KEY、网络，或 DeepSeek 账户余额。")
        st.stop()
    finally:
        trace.end()

    reply = out.reply or "（本轮没有生成回复）"
    mem.add_assistant(sid, reply)
    st.session_state.history.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)

    with st.expander("查看本轮决策 / 检索 / 升级"):
        st.write("**节点轨迹**：", " → ".join(node_trace))
        if out.intent:
            st.write("**意图**：", out.intent.intent,
                     "｜置信度：", out.intent.confidence,
                     "｜依据：", out.intent.reason)
        if out.escalation and out.escalation.escalated:
            st.warning(f"已转人工｜层：{out.escalation.layer}｜原因：{out.escalation.reason}")
        if out.kb_results:
            st.write("**检索命中**")
            st.table([
                {"资料": h.id, "标题": h.title, "分数": h.score, "可作答": h.grounded}
                for h in out.kb_results
            ])
