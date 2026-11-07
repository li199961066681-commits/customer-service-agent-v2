# -*- coding: utf-8 -*-
"""State：LangGraph 状态机的数据模型（Pydantic）。

State 是整个图唯一的「数据流」：每个节点读 State、改 State，
条件路由也只看 State 里的字段。这是 LangGraph 与手写循环最核心的区别。
"""

from typing import Optional

from pydantic import BaseModel, Field


class IntentResult(BaseModel):
    """意图分类节点的结构化输出（LLM 必须以该 schema 返回）。"""

    intent: str = Field(description="faq | action | clarify | human | other 之一")
    confidence: float = Field(ge=0.0, le=1.0, description="模型对分类的置信度 0~1")
    missing_slots: list[str] = Field(default_factory=list,
                                     description="执行所需但缺失的槽位，如 order_id / ticket_id")
    reason: str = Field(default="", description="分类依据，供 Trace 复盘")


class EscalationResult(BaseModel):
    """升级判定节点的输出：三层防御中任一命中即转人工。"""

    escalated: bool = False
    reason: str = Field(default="", description="升级原因")
    layer: str = Field(default="", description="命中的防御层：confidence / self_check / sensitive")


class KbHit(BaseModel):
    """一条知识库检索命中。"""

    id: str
    title: str
    content: str
    score: float  # 相似度 / 打分 0~1
    grounded: bool = True  # 是否达到可作答的置信度门槛


class AgentState(BaseModel):
    """图内全局状态：节点之间唯一的通信通道。"""

    user_input: str = ""                 # 本轮用户输入
    session_id: str = "default"          # 会话标识（短期记忆用）
    turn: int = 0                        # 轮次计数

    messages: list[dict] = Field(default_factory=list)   # 对话历史 [{"role":..., "content":...}]
    intent: Optional[IntentResult] = None                 # 意图分类结果
    route: str = ""                     # 路由去向：faq/action/clarify/human/other
    missing_slots: list[str] = Field(default_factory=list)
    kb_results: list[KbHit] = Field(default_factory=list)  # 检索命中
    tool_result: Optional[str] = None    # 工具执行结果（JSON 字符串）
    draft_reply: Optional[str] = None    # 回答合成节点的拟回复（供升级判定第二层 self-check 校验）
    escalation: Optional[EscalationResult] = None
    reply: Optional[str] = None          # 最终回答
    trace_id: Optional[str] = None       # Trace 追踪号
