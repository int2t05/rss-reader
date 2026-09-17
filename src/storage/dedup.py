"""SQLite 去重状态:记录已处理的 item_id + fetched_at,避免重复分析。"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class DedupStore:
    """SQLite 去重存储:item_id → fetched_at。

    示例:
        store = DedupStore("data/dedup.db")
        if not store.is_processed(item.id):
            await analyze(item)
            store.mark_processed(item.id)
    """

    def __init__(self, db_path: Path | str):
        """打开 SQLite 文件,自动建表。"""
        # TODO: 未设 WAL 模式,并发写抛 "database is locked";应 PRAGMA journal_mode=WAL
        # TODO: 未设 check_same_thread=False,async 场景跨线程使用会抛错
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_items (
                item_id TEXT PRIMARY KEY,
                fetched_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def is_processed(self, item_id: str) -> bool:
        """查询 item_id 是否已处理。"""
        cur = self._conn.execute(
            "SELECT 1 FROM processed_items WHERE item_id = ?", (item_id,)
        )
        return cur.fetchone() is not None

    def mark_processed(self, item_id: str) -> None:
        """标记 item_id 为已处理(INSERT OR IGNORE,幂等)。"""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT OR IGNORE INTO processed_items (item_id, fetched_at) VALUES (?, ?)",
            (item_id, now),
        )
        self._conn.commit()

    def batch_unprocessed(self, item_ids: list[str]) -> list[str]:
        """批量查询:返回未处理的 item_id 列表,保持输入顺序。"""
        if not item_ids:
            return []
        placeholders = ",".join("?" * len(item_ids))
        cur = self._conn.execute(
            f"SELECT item_id FROM processed_items WHERE item_id IN ({placeholders})",
            item_ids,
        )
        processed = {row[0] for row in cur.fetchall()}
        return [iid for iid in item_ids if iid not in processed]

    def get_processed_at(self, item_id: str) -> datetime | None:
        """返回 item_id 的处理时间,未处理返回 None。"""
        cur = self._conn.execute(
            "SELECT fetched_at FROM processed_items WHERE item_id = ?", (item_id,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(row[0])

    def clear(self) -> None:
        """清空去重表,用于 re-run 场景。"""
        self._conn.execute("DELETE FROM processed_items")
        self._conn.commit()

    def close(self) -> None:
        """关闭数据库连接。"""
        self._conn.close()

    def __enter__(self) -> DedupStore:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
