# -*- coding: utf-8 -*-
"""可观测性：全链路 Trace。

- LangfuseTrace：配置 Key 后上传到 Langfuse（评分表「必选其一」）
- LocalTrace   ：未配置时降级为本地 JSONL 日志（trace_log.jsonl），
                 同样记录 输入/决策/工具/耗时，可被评测与复盘读取
- 对外统一接口：create_trace() -> ctx，ctx.span(step, data)，ctx.end()
"""

import json
import time
import uuid

from config import LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, TRACE_LOG_PATH


class LocalTrace:
    """本地 Trace：写 JSONL 文件，零依赖。"""

    def __init__(self, name: str, session_id: str) -> None:
        self.trace_id = uuid.uuid4().hex[:12]
        self.name = name
        self.session_id = session_id
        self.started = time.time()
        self._events: list[dict] = []
        self._log_path = TRACE_LOG_PATH
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def span(self, name: str, data: dict) -> None:
        self._events.append({
            "ts": round(time.time() - self.started, 3),
            "step": name,
            **data,
        })

    def end(self) -> dict:
        payload = {
            "trace_id": self.trace_id,
            "name": self.name,
            "session_id": self.session_id,
            "duration_s": round(time.time() - self.started, 3),
            "events": self._events,
        }
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except OSError:
            pass
        return payload


class LangfuseTrace:
    """Langfuse v5 真实 Trace（OTel span API，需配置 Key）。

    v5 不再有 v2 的 `Langfuse().trace()`，改用：
    - propagate_attributes：设置 trace 级 session_id / trace_name；
    - start_observation：创建根 span / 子 span；
    - 根 span 的 trace_context 绑定 create_trace_id()，保证 trace_id 可回查。
    """

    def __init__(self, name: str, session_id: str) -> None:
        from contextlib import ExitStack

        from langfuse import Langfuse, propagate_attributes

        self._lf = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
        )
        self.trace_id = self._lf.create_trace_id()
        self.started = time.time()

        # trace 级属性：session_id / trace_name 会传播给后续所有 span
        self._stack = ExitStack()
        self._stack.enter_context(
            propagate_attributes(session_id=session_id, trace_name=name)
        )
        self._root = self._lf.start_observation(
            name=name,
            as_type="span",
            trace_context={"trace_id": self.trace_id},
            input={"session_id": session_id},
        )

    def span(self, name: str, data: dict) -> None:
        child = self._root.start_observation(name=name, as_type="span", input=data)
        child.end()

    def end(self) -> dict:
        duration = round(time.time() - self.started, 3)
        try:
            self._root.update(output={"duration_s": duration})
            self._root.end()
        finally:
            self._stack.close()
            try:
                self._lf.flush()
            except Exception:
                # 观测失败不应阻断主流程；本地 Trace/日志仍可用
                pass
        return {"trace_id": self.trace_id, "provider": "langfuse",
                "duration_s": duration}


def create_trace(name: str, session_id: str):
    """工厂：Key 齐全用 Langfuse，否则本地日志。"""
    if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
        try:
            return LangfuseTrace(name, session_id)
        except Exception:
            pass
    return LocalTrace(name, session_id)
