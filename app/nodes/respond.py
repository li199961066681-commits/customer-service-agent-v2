# -*- coding: utf-8 -*-
"""节点 ⑦：回答合成（生成拟回复，待升级判定放行后输出）。

faq   ：LLM 基于检索资料生成，必须带【资料N】引用；
action：基于工具执行结果向用户汇报，同时生成工单小结。
"""

from app.prompts import RESPOND_SYSTEM
from app.state import AgentState
from llm import create_llm


def _format_context(hits) -> str:
    return "\n".join(f"{h.id} {h.title}：{h.content}" for h in hits)


def respond_node(state: AgentState) -> dict:
    llm = create_llm()
    if state.route == "faq":
        context = _format_context(state.kb_results)
        reply = llm.chat([
            {"role": "system", "content": RESPOND_SYSTEM.format(
                context=context or "（未找到相关）", question=state.user_input)},
            {"role": "user", "content": "请生成回复。"},
        ])
    else:
        # action 分支：把工具结果翻译成用户可读的回复
        reply = _humanize_tool_result(state.tool_result)
    return {"draft_reply": reply}


def _humanize_tool_result(tool_result: str | None) -> str:
    """把工具返回的 JSON 转成礼貌、准确的用户话术。"""
    if not tool_result:
        return "处理完成，如需要可继续为您服务。"
    import json
    try:
        data = json.loads(tool_result)
    except json.JSONDecodeError:
        return "处理完成，如需要可继续为您服务。"
    if data.get("found") is False:
        return f"抱歉，未查询到工单 {data.get('error', '')}，请核对工单号后再试。"
    if data.get("ok") is False:
        return f"操作未成功：{data.get('error', '未知原因')}。"
    if "ticket_id" in data and "status" in data:  # update_ticket_status
        return f"已为您更新工单 {data['ticket_id']} 状态为「{data['status']}」。"
    if "id" in data and "created_at" in data:  # create_ticket：新建成功
        who = f"（{data.get('user_name', '')}）" if data.get("user_name") else ""
        return f"已为您创建工单 {data['id']}{who}，当前状态为「{data.get('status', '待处理')}」。问题：{data.get('title', '')}"
    if "id" in data:  # query_ticket
        return f"工单 {data['id']} 当前状态为「{data.get('status', '待处理')}」：{data.get('title', '')}"
    return "处理完成，如需要可继续为您服务。"
