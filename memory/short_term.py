# -*- coding: utf-8 -*-
"""短期记忆：最近 N 轮对话 + 已抽取实体。

- 首选 Redis（独立进程，Web 刷新不丢状态——实训单指定方案）
- Redis 不可用时自动降级为进程内 dict（保证零部署可演示）
- 对外接口一致，上层无感知
"""

import json

import redis

from config import MAX_CONTEXT_TURNS, REDIS_URL


class _MemoryBackend:
    """内存降级实现。"""

    def __init__(self) -> None:
        self._data: dict[str, list[dict]] = {}

    def push(self, key: str, msg: dict) -> None:
        self._data.setdefault(key, []).append(msg)

    def get(self, key: str, tail: int) -> list[dict]:
        return self._data.get(key, [])[-tail:]

    def clear(self, key: str) -> None:
        self._data.pop(key, None)


class RedisBackend:
    """Redis 实现：list 存消息，rpush + lrange 取最近 N 条。"""

    def __init__(self, url: str) -> None:
        self._client = redis.Redis.from_url(url, decode_responses=True)

    def push(self, key: str, msg: dict) -> None:
        self._client.rpush(key, json.dumps(msg, ensure_ascii=False))
        # 只保留最近 50 条，防止无限增长
        self._client.ltrim(key, -50, -1)

    def get(self, key: str, tail: int) -> list[dict]:
        raw = self._client.lrange(key, -tail, -1)
        out = []
        for item in raw:
            try:
                out.append(json.loads(item))
            except json.JSONDecodeError:
                continue
        return out

    def clear(self, key: str) -> None:
        self._client.delete(key)


class ShortTermMemory:
    """短期记忆门面：优先 Redis，失败降级内存。"""

    def __init__(self) -> None:
        self._backend = self._try_redis() or _MemoryBackend()
        self.using_redis = isinstance(self._backend, RedisBackend)

    def _try_redis(self):
        try:
            b = RedisBackend(REDIS_URL)
            b.get("__probe__", 1)
            return b
        except Exception:
            return None

    def add_user(self, session_id: str, text: str) -> None:
        self._backend.push(f"hist:{session_id}", {"role": "user", "content": text})

    def add_assistant(self, session_id: str, text: str) -> None:
        self._backend.push(f"hist:{session_id}", {"role": "assistant", "content": text})

    def history(self, session_id: str) -> list[dict]:
        return self._backend.get(f"hist:{session_id}", MAX_CONTEXT_TURNS)

    def clear(self, session_id: str) -> None:
        """清空某个会话的历史（Web 的“清空会话”会用到）。"""
        self._backend.clear(f"hist:{session_id}")
