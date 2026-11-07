# -*- coding: utf-8 -*-
"""OpenAICompatLLM：通过 OpenAI 兼容协议调用真实大模型（如 DeepSeek）。

- 未配置 LLM_API_KEY 时构造会抛出 ValueError，避免空跑。
- 若需对接非 OpenAI 兼容的服务，仅需修改本文件内部实现。
"""

from openai import OpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TEMPERATURE
from llm.base import LLMClient


class OpenAICompatLLM(LLMClient):
    """DeepSeek / OpenAI 兼容协议的真实模型客户端。"""

    def __init__(self) -> None:
        if not LLM_API_KEY:
            raise ValueError(
                "LLM_API_KEY 未配置：请复制 .env.example 为 .env，填写 LLM_API_KEY。"
            )
        self._client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
            timeout=45.0,      # 防止网络抖动时 Web 一直转圈
            max_retries=1,     # 最多重试一次，失败后让页面显示错误
        )
        self.model = LLM_MODEL

    def chat(self, messages: list[dict], temperature: float | None = None) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature if temperature is not None else LLM_TEMPERATURE,
        )
        return resp.choices[0].message.content or ""

    def structured(self, system: str, user: str) -> dict:
        """强制 JSON 输出：json_object 模式 + 宽容解析兜底。"""
        import json

        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=LLM_TEMPERATURE,
        )
        raw = resp.choices[0].message.content or ""
        # 去掉可能的代码块围栏后解析
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").removeprefix("json").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # 极少数失败：把原文包进字典返回，由上层 Pydantic 校验兜底
            return {"raw": raw}
