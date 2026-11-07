# -*- coding: utf-8 -*-
"""节点 ③：RAG 检索（faq 分支）。

向量检索知识库，Top-K + 相似度 + grounded 标记；结果进入 State，
供回答合成与升级判定使用。"""

from config import GROUNDED_THRESHOLD
from app.state import AgentState
from retrieval.search import search


def rag_search_node(state: AgentState) -> dict:
    hits = search(state.user_input, top_k=3, threshold=GROUNDED_THRESHOLD)
    return {"kb_results": hits}
