# -*- coding: utf-8 -*-
"""长期记忆：SQLite 持久化工单记录 + 坐席队列。

- 工单表 tickets：query/create/update（4 个工具中的 3 个读写这里）
- 队列表 queue  ：转人工时写入，模拟「坐席工作台」待办
- 全部使用 ? 参数化查询，杜绝 SQL 注入
"""

import json
import sqlite3
from pathlib import Path

from config import TICKET_DB_PATH

_STATUS_ALLOWED = {"待处理", "处理中", "已完成", "已关闭"}


class TicketStore:
    """工单与坐席队列的关系型存储。"""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path or TICKET_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row  # 按列名取值，不用下标
        self._init_tables()

    def _init_tables(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT '待处理',
                    created_at TEXT NOT NULL,
                    note TEXT DEFAULT ''
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    payload TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            self._seed_tickets()

    def _seed_tickets(self) -> None:
        """种子工单：让 action 分支开箱即可演示查询。"""
        seeds = [
            ("TK001", "张伟", "订单88888888物流异常", "处理中", "2026-10-28 10:00:00", "快递滞留 2 天"),
            ("TK002", "李娜", "订单66666666申请退款", "待处理", "2026-10-29 14:30:00", "七天无理由退款"),
        ]
        for s in seeds:
            self._conn.execute(
                "INSERT OR IGNORE INTO tickets (id, user_name, title, status, created_at, note) "
                "VALUES (?, ?, ?, ?, ?, ?)", s
            )

    # ---------- 工单 CRUD ----------
    def query_ticket(self, ticket_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        return dict(row) if row else None

    def create_ticket(self, user_name: str, title: str, note: str = "") -> dict:
        import datetime
        ticket_id = "TK" + datetime.datetime.now().strftime("%H%M%S%f")[:-4]
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conn:
            self._conn.execute(
                "INSERT INTO tickets (id, user_name, title, status, created_at, note) "
                "VALUES (?, ?, ?, '待处理', ?, ?)",
                (ticket_id, user_name, title, created_at, note),
            )
        return {"id": ticket_id, "user_name": user_name, "title": title,
                "status": "待处理", "created_at": created_at, "note": note}

    def update_ticket_status(self, ticket_id: str, status: str) -> dict:
        if status not in _STATUS_ALLOWED:
            return {"ok": False, "error": f"非法状态: {status}，允许值: {sorted(_STATUS_ALLOWED)}"}
        cur = self._conn.execute(
            "UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id)
        )
        self._conn.commit()
        if cur.rowcount == 0:
            return {"ok": False, "error": f"工单不存在: {ticket_id}"}
        return {"ok": True, "ticket_id": ticket_id, "status": status}

    # ---------- 坐席队列 ----------
    def enqueue_escalation(self, ticket_id: str, reason: str, payload: dict | None = None) -> dict:
        import datetime
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO queue (ticket_id, reason, payload, created_at) VALUES (?, ?, ?, ?)",
                (ticket_id, reason, json.dumps(payload or {}, ensure_ascii=False), created_at),
            )
        return {"queue_id": cur.lastrowid, "ticket_id": ticket_id,
                "reason": reason, "created_at": created_at, "status": "已进入坐席队列"}

    def list_queue(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM queue ORDER BY id DESC LIMIT 50"
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
