# -*- coding: utf-8 -*-
"""节点 ④：工具调用（action 分支）。

Agent 决定调哪个工具、传什么参数：
1. LLM 结构化输出 {tool, arguments}（真实 LLM 按语义选择）；
2. 从注册表取出工具并执行（统一 JSON 字符串返回）；
3. 结果写入 State.tool_result。

工具选择由 LLM 决定而不是 if-else 硬编码，是「LLM 决策 + 工具执行」的体现。
"""

from app.state import AgentState
from llm import create_llm
from tools.registry import build_tools

_TOOL_SELECT_SYSTEM = (
    "你是客服系统的工具调度器。根据用户诉求选择一个工具并给出参数。\n"
    "可用工具：\n{tools}\n"
    "输出格式（JSON，不许其他内容）：{{\"tool\": \"工具名\", \"arguments\": {{...}}}}\n"
    "规则：查工单用 query_ticket；建工单用 create_ticket；改状态用 update_ticket_status。"
)


def tool_call_node(state: AgentState) -> dict:
    llm = create_llm()
    tools = build_tools()
    schemas = "\n".join(
        f"- {t.name}: {t.description}，参数: {t.parameters.get('properties', {})}"
        for t in tools.values()
    )
    system = _TOOL_SELECT_SYSTEM.format(tools=schemas)
    raw = llm.structured(system, f"用户诉求：{state.user_input}")

    name = raw.get("tool")
    arguments = raw.get("arguments") or {}
    if name not in tools:
        return {"tool_result": f'{{"error": "未知工具 {name}"}}'}

    tool = tools[name]
    try:
        result = tool(**arguments)
    except TypeError as e:
        # 参数不合法：把错误反馈给上层（真实 LLM 场景可据此重试）
        result = '{"error": "参数校验失败: %s"}' % str(e)
    return {"tool_result": result}
