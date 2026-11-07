# -*- coding: utf-8 -*-
"""节点 ①：意图分类（LLM 结构化输出）。

LLM 是决策者：它把用户输入映射为 {intent, confidence, missing_slots, reason}，
路由节点只看 intent 字段决定去向。
"""

from app.prompts import CLASSIFY_SYSTEM
from app.state import AgentState, IntentResult
from llm import create_llm


def classify_intent(state: AgentState) -> dict:
    llm = create_llm()
    history = "\n".join(f"{m['role']}: {m['content']}" for m in state.messages[-6:])
    user = f"对话历史：\n{history or '（无）'}\n\n用户最新发言：{state.user_input}"
    raw = llm.structured(CLASSIFY_SYSTEM, user)

    # Pydantic 校验：字段缺失/类型错误时宽容兜底为 faq（不崩溃）
    try:
        intent = IntentResult.model_validate(raw)
    except Exception:
        intent = IntentResult(intent="faq", confidence=0.5,
                              missing_slots=[], reason=f"结构化输出解析失败，原文: {raw}")
    return {"intent": intent, "route": intent.intent}
