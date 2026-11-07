# -*- coding: utf-8 -*-
"""节点 ⑥：升级判定（三层防御，产品的兜底思维）。

层 1 confidence：检索无 grounded 命中 → 没有依据，拒答并转人工；
层 2 self_check：LLM 质检拟回复（是否引用资料、是否覆盖诉求、有无强行作答）；
层 3 sensitive ：用户输入含敏感/威胁词 → 无条件转人工（只扫用户输入，不扫回复）。

任一命中 → EscalationResult；全部通过 → 拟回复转为最终回复。
"""

from config import GROUNDED_THRESHOLD
from app.prompts import SELF_CHECK_SYSTEM
from app.safety import hit_sensitive
from app.state import AgentState, EscalationResult
from llm import create_llm


def escalate_check_node(state: AgentState) -> dict:
    draft = state.draft_reply or ""

    # ---- 层 1：检索置信度（faq 分支）----
    if state.route == "faq":
        grounded = [h for h in state.kb_results if h.grounded]
        if not grounded:
            return {"escalation": EscalationResult(
                escalated=True, layer="confidence",
                reason=f"知识库未检索到可作答依据（grounded 阈值 {GROUNDED_THRESHOLD}）")}

        # ---- 层 2：LLM self-check（仅 faq：质检「带引用 + 有依据」）----
        context = "\n".join(f"{h.id} {h.title}：{h.content}" for h in state.kb_results) or ""
        if draft and context:
            llm = create_llm()
            raw = llm.chat([
                {"role": "system", "content": SELF_CHECK_SYSTEM.format(
                    question=state.user_input, context=context[:600], reply=draft)},
                {"role": "user", "content": "请给出质检结论。"},
            ])
            if "NOT_OK" in raw:
                return {"escalation": EscalationResult(
                    escalated=True, layer="self_check", reason="拟回复未通过质检：" + raw[:120])}

    # ---- 层 3：敏感词拦截（全分支）----
    # 只扫用户输入，不扫回复：回复中的「投诉/升级」等词是知识库引用，属正常业务用语
    if hit_sensitive(state.user_input):
        return {"escalation": EscalationResult(
            escalated=True, layer="sensitive", reason="命中敏感/情绪词，无条件转人工")}

    # ---- 全部通过：拟回复转正 ----
    return {"reply": draft}
