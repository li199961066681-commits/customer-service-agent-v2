# -*- coding: utf-8 -*-
"""客服安全词表：敏感/威胁词 + 情绪词。

这些是业务规则，不属于某个 LLM 实现。放在这里，真实 LLM 版也能复用同一套拦截逻辑。
"""

SENSITIVE_WORDS = ["骗子", "诈骗", "投诉", "曝光", "威胁", "报警", "律师", "起诉", "赔偿损失"]
EMOTION_WORDS = ["气死", "愤怒", "太过分", "垃圾", "差评", "再也不买", "血本无归"]


def hit_sensitive(text: str) -> bool:
    """用户输入是否命中敏感/情绪词。"""
    return any(w in text for w in SENSITIVE_WORDS + EMOTION_WORDS)
