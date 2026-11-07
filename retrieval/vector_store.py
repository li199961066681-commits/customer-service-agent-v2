# -*- coding: utf-8 -*-
"""向量库：文档向量的存取与检索。

- ChromaBackend：真实 Chroma（持久化到 data/chroma），可安装时优先启用
- MemoryBackend：进程内 numpy 余弦（Chroma 不可用时的零依赖兜底）
- 两种后端实现同一接口，上层无感知
"""

from config import DATA_DIR

_EMB = None  # 延迟导入避免循环


def _emb():
    global _EMB
    if _EMB is None:
        from retrieval.embeddings import MockEmbedding
        _EMB = MockEmbedding()
    return _EMB


class MemoryBackend:
    """内存向量库：numpy 矩阵 + 余弦相似度。"""

    def __init__(self) -> None:
        import numpy as np
        self._np = np
        self._ids: list[str] = []
        self._matrix = self._np.zeros((0, _emb().DIM), dtype=self._np.float32)

    def add(self, doc_id: str, text: str) -> None:
        vec = self._np.array(_emb().embed(text), dtype=self._np.float32)
        self._ids.append(doc_id)
        self._matrix = self._np.vstack([self._matrix, vec])

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        if not self._ids:
            return []
        q = self._np.array(_emb().embed(query), dtype=self._np.float32)
        scores = self._matrix @ q  # 已归一化，点积即余弦
        idx = self._np.argsort(-scores)[:top_k]
        return [(self._ids[i], float(scores[i])) for i in idx]


class ChromaBackend:
    """Chroma 持久化向量库（使用本项目的中文 embedding 函数，避免默认英文模型）。"""

    def __init__(self) -> None:
        import chromadb
        from chromadb.utils import embedding_functions

        class _Fn(embedding_functions.EmbeddingFunction):
            def __call__(self, input):  # type: ignore[override]
                from retrieval.embeddings import MockEmbedding
                emb = MockEmbedding()
                return [emb.embed(doc) for doc in input]

        self._client = chromadb.PersistentClient(path=str(DATA_DIR / "chroma"))
        self._col = self._client.get_or_create_collection(
            name="cs_kb",
            embedding_function=_Fn(),
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, doc_id: str, text: str) -> None:
        self._col.upsert(ids=[doc_id], documents=[text])

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        res = self._col.query(query_texts=[query], n_results=top_k)
        ids = res["ids"][0]
        dists = res["distances"][0]
        # cosine distance -> similarity
        return [(i, 1.0 - float(d)) for i, d in zip(ids, dists)]


def get_backend():
    """优先 Chroma；不可用则内存。"""
    try:
        from chromadb.errors import InvalidDimensionException  # noqa
    except Exception:
        pass
    try:
        b = ChromaBackend()
        b.add("__probe__", "探针")
        b.search("探针", 1)
        return b
    except Exception:
        return MemoryBackend()
