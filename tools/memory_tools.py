"""
Memory Tools — 让 Agent 能读写记忆的工具集
"""

import json
from tools.registry import registry
from agent.memory import MemoryStore

# 全局记忆存储实例
memory_store = MemoryStore()


# ============================================================
# 保存记忆
# ============================================================

registry.register(
    name="memory_save",
    description="""保存一条记忆到长期存储。

记忆类型:
- fact: 事实 (用户告诉你的信息，如名字、职业、项目)
- preference: 偏好 (用户喜欢什么，如风格、语言)
- learning: 学习 (你学到的知识，如工具用法、项目信息)
- conversation: 对话摘要 (重要对话的总结)

什么时候保存:
- 用户告诉你个人信息 → type=fact
- 用户表达喜好/习惯 → type=preference
- 你学到了新知识 → type=learning
- 一段重要对话结束 → type=conversation""",
    parameters={
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["fact", "preference", "learning", "conversation"],
                "description": "记忆类型",
            },
            "content": {
                "type": "string",
                "description": "记忆内容，简洁明确",
            },
            "importance": {
                "type": "integer",
                "description": "重要性 1-5 (5=最重要)",
                "default": 3,
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "标签列表，用于分类检索",
                "default": [],
            },
        },
        "required": ["type", "content"],
    },
    handler=lambda type, content, importance=3, tags=[]: json.dumps(
        {"id": memory_store.add(type, content, "agent", importance, tags), "success": True}
    ),
)


# ============================================================
# 搜索记忆
# ============================================================

registry.register(
    name="memory_search",
    description="搜索记忆。用关键词查找之前保存的信息。",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词",
            },
            "type": {
                "type": "string",
                "enum": ["fact", "preference", "learning", "conversation"],
                "description": "过滤记忆类型 (可选)",
            },
            "limit": {
                "type": "integer",
                "description": "返回数量 (默认5)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
    handler=lambda query, type=None, limit=5: json.dumps(
        memory_store.search(query, type, limit), ensure_ascii=False, default=str
    ),
)


# ============================================================
# 查看最近记忆
# ============================================================

registry.register(
    name="memory_recent",
    description="查看最近保存的记忆",
    parameters={
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["fact", "preference", "learning", "conversation"],
                "description": "过滤类型 (可选)",
            },
            "limit": {
                "type": "integer",
                "description": "返回数量 (默认10)",
                "default": 10,
            },
        },
    },
    handler=lambda type=None, limit=10: json.dumps(
        memory_store.get_recent(type, limit), ensure_ascii=False, default=str
    ),
)


# ============================================================
# 查看重要记忆
# ============================================================

registry.register(
    name="memory_important",
    description="查看最重要的记忆 (按重要性排序)",
    parameters={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "返回数量 (默认10)",
                "default": 10,
            },
        },
    },
    handler=lambda limit=10: json.dumps(
        memory_store.get_important(limit), ensure_ascii=False, default=str
    ),
)


# ============================================================
# 删除记忆
# ============================================================

registry.register(
    name="memory_delete",
    description="删除指定 ID 的记忆",
    parameters={
        "type": "object",
        "properties": {
            "id": {"type": "integer", "description": "记忆 ID"},
        },
        "required": ["id"],
    },
    handler=lambda id: (memory_store.delete(id), json.dumps({"success": True, "deleted_id": id}))[-1],
)


# ============================================================
# 记忆统计
# ============================================================

registry.register(
    name="memory_stats",
    description="查看记忆存储统计信息",
    parameters={"type": "object", "properties": {}},
    handler=lambda: json.dumps(memory_store.stats(), ensure_ascii=False),
)


print(f"✅ 记忆系统已加载 (共 {memory_store.stats()['total']} 条记忆)")
