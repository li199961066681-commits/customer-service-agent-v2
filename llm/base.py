# -*- coding: utf-8 -*-
"""LLM 客户端抽象：整个项目只依赖这两个接口。

- chat()        ：自由文本对话（回答合成、self-check）
- structured()  ：要求模型按指定 JSON schema 输出（意图分类）

任何真实模型（DeepSeek / OpenAI / 其他兼容服务）只要实现这两个方法即可接入，
这就是「LLM 可插拔」的落点。"""

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """所有 LLM 实现的统一接口。"""

    @abstractmethod
    def chat(self, messages: list[dict], temperature: float | None = None) -> str:
        """普通对话：输入消息列表，返回文本。"""

    @abstractmethod
    def structured(self, system: str, user: str) -> dict:
        """结构化输出：返回可被 json.loads 的 dict（由实现保证 JSON 规范）。"""
