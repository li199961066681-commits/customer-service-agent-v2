# -*- coding: utf-8 -*-
"""统一执行入口：只跑一次图，同时收集节点轨迹与 Trace。

`agent.stream(..., stream_mode=["updates", "values"])` 会同时吐出：
- updates：{"节点名": 本次增量}，用于节点轨迹 / Trace；
- values ：完整状态快照，最后一帧就是最终 State。

这样避免 `stream` + `invoke` 各跑一遍图（有副作用的工具会执行两次）。
"""

from app.graph import agent
from app.state import AgentState


def to_jsonable(obj):
    """把节点输出转成可 JSON 序列化的结构（Pydantic 模型 → dict）。"""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    return obj


def run_agent(state: AgentState, trace=None) -> tuple[AgentState, list[str]]:
    """执行一次图，返回（最终状态, 节点轨迹）。

    trace 只需要提供 `.span(name, data)`，因此本地 JSONL 和 Langfuse 都能复用。
    """
    node_trace: list[str] = []
    final_state: dict | None = None

    for mode, chunk in agent.stream(state, stream_mode=["updates", "values"]):
        if mode == "updates":
            for node, out in chunk.items():
                node_trace.append(node)
                if trace is not None and isinstance(out, dict):
                    trace.span(node, to_jsonable(out))
        elif mode == "values":
            final_state = chunk

    if final_state is None:
        raise RuntimeError("Agent 没有产生最终状态：请检查图是否有可达的 END")
    return AgentState.model_validate(final_state), node_trace
