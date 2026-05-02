"""
Memory Store — SQLite 持久化记忆存储

记忆类型:
- fact: 事实 (用户告诉我的信息)
- preference: 偏好 (用户喜欢什么)
- learning: 学习 (我学到的知识)
- conversation: 对话摘要 (重要对话的总结)

每条记忆有:
- id: 自增主键
- type: 记忆类型
- content: 记忆内容
- source: 来源 (哪次对话)
- importance: 重要性 (1-5)
- created_at: 创建时间
- last_accessed: 最后访问时间
- access_count: 访问次数
- tags: 标签 (逗号分隔)
"""

import json
import sqlite3
import time
from pathlib import Path
from datetime import datetime


class MemoryStore:
    """SQLite 持久化记忆存储"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / ".my-agent" / "memory.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT DEFAULT '',
                    importance INTEGER DEFAULT 3,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    tags TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_type ON memories(type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at DESC)
            """)
            # FTS 全文搜索索引
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    content, tags, type, source,
                    content='memories',
                    content_rowid='id'
                )
            """)
            # 触发器: 自动同步 FTS
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, content, tags, type, source)
                    VALUES (new.id, new.content, new.tags, new.type, new.source);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content, tags, type, source)
                    VALUES ('delete', old.id, old.content, old.tags, old.type, old.source);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content, tags, type, source)
                    VALUES ('delete', old.id, old.content, old.tags, old.type, old.source);
                    INSERT INTO memories_fts(rowid, content, tags, type, source)
                    VALUES (new.id, new.content, new.tags, new.type, new.source);
                END
            """)
            conn.commit()

    def add(self, type: str, content: str, source: str = "",
            importance: int = 3, tags: list[str] = None) -> int:
        """
        添加一条记忆

        参数:
            type:       记忆类型 (fact/preference/learning/conversation)
            content:    记忆内容
            source:     来源描述
            importance: 重要性 1-5
            tags:       标签列表

        返回:
            记忆 ID
        """
        now = datetime.now().isoformat()
        tags_str = ",".join(tags) if tags else ""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO memories (type, content, source, importance, created_at, last_accessed, access_count, tags)
                   VALUES (?, ?, ?, ?, ?, ?, 0, ?)""",
                (type, content, source, importance, now, now, tags_str)
            )
            return cursor.lastrowid

    def search(self, query: str, type: str = None, limit: int = 5) -> list[dict]:
        """
        全文搜索记忆

        参数:
            query: 搜索关键词
            type:  过滤记忆类型 (可选)
            limit: 返回数量

        返回:
            记忆列表
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if type:
                rows = conn.execute(
                    """SELECT m.*, rank
                       FROM memories_fts fts
                       JOIN memories m ON m.id = fts.rowid
                       WHERE memories_fts MATCH ? AND m.type = ?
                       ORDER BY rank
                       LIMIT ?""",
                    (query, type, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT m.*, rank
                       FROM memories_fts fts
                       JOIN memories m ON m.id = fts.rowid
                       WHERE memories_fts MATCH ?
                       ORDER BY rank
                       LIMIT ?""",
                    (query, limit)
                ).fetchall()

            # 更新访问时间
            now = datetime.now().isoformat()
            for row in rows:
                conn.execute(
                    "UPDATE memories SET last_accessed = ?, access_count = access_count + 1 WHERE id = ?",
                    (now, row["id"])
                )
            conn.commit()

            return [dict(row) for row in rows]

    def get_recent(self, type: str = None, limit: int = 10) -> list[dict]:
        """获取最近的记忆"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if type:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE type = ? ORDER BY created_at DESC LIMIT ?",
                    (type, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()

            return [dict(row) for row in rows]

    def get_important(self, limit: int = 10) -> list[dict]:
        """获取最重要的记忆"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY importance DESC, created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_by_type(self, type: str, limit: int = 20) -> list[dict]:
        """按类型获取记忆"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memories WHERE type = ? ORDER BY importance DESC, created_at DESC LIMIT ?",
                (type, limit)
            ).fetchall()
            return [dict(row) for row in rows]

    def update(self, id: int, content: str = None, importance: int = None, tags: list[str] = None):
        """更新记忆"""
        updates = []
        params = []
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if importance is not None:
            updates.append("importance = ?")
            params.append(importance)
        if tags is not None:
            updates.append("tags = ?")
            params.append(",".join(tags))

        if not updates:
            return

        params.append(id)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE memories SET {', '.join(updates)} WHERE id = ?",
                params
            )

    def delete(self, id: int):
        """删除记忆"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memories WHERE id = ?", (id,))

    def stats(self) -> dict:
        """获取记忆统计"""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            by_type = {}
            for row in conn.execute("SELECT type, COUNT(*) as cnt FROM memories GROUP BY type"):
                by_type[row[0]] = row[1]

            return {
                "total": total,
                "by_type": by_type,
                "db_path": self.db_path,
            }

    def format_for_context(self, memories: list[dict], max_chars: int = 2000) -> str:
        """
        将记忆格式化为 LLM 上下文

        参数:
            memories: 记忆列表
            max_chars: 最大字符数

        返回:
            格式化的记忆文本
        """
        if not memories:
            return ""

        lines = ["## 已有记忆"]
        total = 0

        for m in memories:
            type_emoji = {
                "fact": "📌",
                "preference": "⭐",
                "learning": "📖",
                "conversation": "💬",
            }.get(m["type"], "📝")

            line = f"- {type_emoji} [{m['type']}] {m['content']}"
            if total + len(line) > max_chars:
                break
            lines.append(line)
            total += len(line)

        return "\n".join(lines)
