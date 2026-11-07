# -*- coding: utf-8 -*-
"""Tool 基类：把「函数 + 说明书」封装成可被 LLM 调用的工具。

- parameters 是 JSON Schema，描述每个参数的约束（类型/必填/说明）
- 调用结果统一转成 JSON 字符串，方便直接写入对话上下文
"""

import json
from typing import Callable


class Tool:
    """一个可被 Agent 调用的工具。"""

    def __init__(self, name: str, description: str, parameters: dict, func: Callable) -> None:
        self.name = name
        self.description = description
        self.parameters = parameters  # JSON Schema 格式
        self.func = func

    def __call__(self, **kwargs) -> str:
        """执行工具，返回 JSON 字符串（统一契约）。"""
        result = self.func(**kwargs)
        if isinstance(result, str):
            # 已是 JSON 字符串则原样返回，否则包装
            try:
                json.loads(result)
                return result
            except json.JSONDecodeError:
                return json.dumps({"result": result}, ensure_ascii=False)
        return json.dumps(result, ensure_ascii=False)

    def to_schema(self) -> dict:
        """供 Prompt 注入 / Langfuse 登记使用的完整工具说明。"""
        return {"name": self.name, "description": self.description,
                "parameters": self.parameters}
