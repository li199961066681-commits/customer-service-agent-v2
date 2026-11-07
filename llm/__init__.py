# -*- coding: utf-8 -*-
"""LLM 工厂：只返回真实客户端。

没有 Mock 离线模式：必须配置 LLM_API_KEY（DeepSeek，OpenAI 兼容协议）。
"""

from config import LLM_READY
from llm.base import LLMClient


def create_llm() -> LLMClient:
    if not LLM_READY:
        raise RuntimeError(
            "LLM_API_KEY 未配置：请复制 .env.example 为 .env，填写 LLM_API_KEY。"
        )
    from llm.openai_compat import OpenAICompatLLM
    return OpenAICompatLLM()
