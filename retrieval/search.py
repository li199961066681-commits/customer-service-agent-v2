# -*- coding: utf-8 -*-
"""知识库加载 + 检索主入口。

- load_kb()：从 data/kb.json 读取全部资料
- search() ：向量检索 → 组装 KbHit（含 score / grounded 标记）
"""

import json

from config import KB_PATH
from app.state import KbHit

_DOCS: list[dict] | None = None


def load_kb() -> list[dict]:
    """读取知识库（懒加载 + 缓存）。"""
    global _DOCS
    if _DOCS is None:
        with open(KB_PATH, encoding="utf-8") as f:
            _DOCS = json.load(f)
    return _DOCS


def search(query: str, top_k: int = 3, threshold: float = 0.0) -> list[KbHit]:
    """检索主入口：向量相似度 → KbHit 列表。

    grounded=True 表示 score 达到可作答门槛（默认 0.25，可调）。
    """
    from retrieval.vector_store import get_backend

    backend = get_backend()
    docs = load_kb()
    # 首次调用时把知识库灌入向量库
    if not hasattr(backend, "_loaded"):
        for d in docs:
            backend.add(d["id"], d["title"] + "。" + d["content"])
        backend._loaded = True  # type: ignore[attr-defined]

    hits = backend.search(query, top_k)
    by_id = {d["id"]: d for d in docs}
    out = []
    for doc_id, score in hits:
        doc = by_id.get(doc_id)
        if not doc:
            continue
        out.append(KbHit(
            id=doc["id"], title=doc["title"], content=doc["content"],
            score=round(score, 4), grounded=score >= threshold,
        ))
    return out
