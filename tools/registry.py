# -*- coding: utf-8 -*-
"""4 个工具：全部走 SQLite / 检索层，Agent 只负责「选哪个、传什么参」。"""

import json

from memory.long_term import TicketStore
from tools.base import Tool

_store = TicketStore()


# ---------- 工具 1：查工单 ----------
def _query_ticket(ticket_id: str) -> dict:
    row = _store.query_ticket(ticket_id)
    if not row:
        return {"found": False, "error": f"工单 {ticket_id} 不存在"}
    return {"found": True, **row}


# ---------- 工具 2：建工单 ----------
def _create_ticket(user_name: str, title: str, note: str = "") -> dict:
    if not user_name or not title:
        return {"ok": False, "error": "user_name 与 title 必填"}
    return _store.create_ticket(user_name, title, note)


# ---------- 工具 3：改状态 ----------
def _update_ticket_status(ticket_id: str, status: str) -> dict:
    return _store.update_ticket_status(ticket_id, status)


# ---------- 工具 4：知识库检索 ----------
def _rag_search(query: str, top_k: int = 3) -> dict:
    from retrieval.search import search
    hits = search(query, top_k=top_k)
    return {"results": [h.model_dump() for h in hits]}


def build_tools() -> dict[str, Tool]:
    """返回 {名字: Tool} 注册表。"""
    return {
        "rag_search": Tool(
            name="rag_search",
            description="在客服知识库中做语义检索，返回与问题最相关的 Top-K 资料及置信度",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要检索的问题或关键词"},
                    "top_k": {"type": "integer", "description": "返回条数，默认 3"},
                },
                "required": ["query"],
            },
            func=_rag_search,
        ),
        "query_ticket": Tool(
            name="query_ticket",
            description="按工单号查询工单详情（状态、用户、标题）",
            parameters={
                "type": "object",
                "properties": {"ticket_id": {"type": "string", "description": "工单号，如 TK123"}},
                "required": ["ticket_id"],
            },
            func=_query_ticket,
        ),
        "create_ticket": Tool(
            name="create_ticket",
            description="为用户创建一张新工单，返回工单号",
            parameters={
                "type": "object",
                "properties": {
                    "user_name": {"type": "string", "description": "用户名"},
                    "title": {"type": "string", "description": "工单标题/问题概述"},
                    "note": {"type": "string", "description": "补充说明，可选"},
                },
                "required": ["user_name", "title"],
            },
            func=_create_ticket,
        ),
        "update_ticket_status": Tool(
            name="update_ticket_status",
            description="更新工单处理状态（待处理/处理中/已完成/已关闭）",
            parameters={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string", "description": "工单号"},
                    "status": {"type": "string", "description": "目标状态"},
                },
                "required": ["ticket_id", "status"],
            },
            func=_update_ticket_status,
        ),
    }


def tool_schemas() -> list[dict]:
    """全部工具说明，供 Prompt / Langfuse 使用。"""
    return [t.to_schema() for t in build_tools().values()]
