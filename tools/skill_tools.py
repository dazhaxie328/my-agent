"""
Skill Tools — 让 Agent 能搜索、加载、使用 Skills
"""

import json
from tools.registry import registry


# 延迟初始化 — 在 main.py 中调用 set_skill_registry 注入
_skill_registry = None


def set_skill_registry(reg):
    """注入 skill registry 实例"""
    global _skill_registry
    _skill_registry = reg


def _get_registry():
    """获取 skill registry"""
    global _skill_registry
    if _skill_registry is None:
        from agent.skills import SkillRegistry
        _skill_registry = SkillRegistry()
        _skill_registry.scan()
    return _skill_registry


# ============================================================
# 列出 Skills
# ============================================================

registry.register(
    name="skill_list",
    description="""列出所有可用的 Skills (知识库)。

Skill 是预定义的知识和操作指南，包含:
- 项目分析方法、工具使用教程、操作流程规范、最佳实践

返回 skill 名称、描述、分类、标签。""",
    parameters={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "按分类过滤 (可选)。如: web3, github, social-media",
            },
            "limit": {
                "type": "integer",
                "description": "返回数量 (默认20)",
                "default": 20,
            },
        },
    },
    handler=lambda category=None, limit=20: json.dumps([
        {"name": s.name, "description": s.description[:100], "category": s.category, "tags": s.tags}
        for s in _get_registry().list_skills(category)[:limit]
    ], ensure_ascii=False),
)


# ============================================================
# 搜索 Skills
# ============================================================

registry.register(
    name="skill_search",
    description="搜索 Skills。用关键词查找相关的知识和操作指南。",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词",
            },
            "limit": {
                "type": "integer",
                "description": "返回数量 (默认5)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
    handler=lambda query, limit=5: json.dumps([
        {"name": s.name, "description": s.description[:100], "category": s.category}
        for s in _get_registry().search(query, limit)
    ], ensure_ascii=False),
)


# ============================================================
# 加载 Skill (读取完整内容)
# ============================================================

registry.register(
    name="skill_load",
    description="""加载指定 Skill 的完整内容。

当任务需要特定知识时，加载对应的 Skill。
例如:
- 要分析 crypto 项目 → 加载 crypto-operations
- 要发推文 → 加载 xitter
- 要操作 GitHub → 加载 github-repo-management

加载后，Skill 的内容会作为上下文指导你的操作。""",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Skill 名称",
            },
            "max_chars": {
                "type": "integer",
                "description": "最大字符数 (默认4000)",
                "default": 4000,
            },
        },
        "required": ["name"],
    },
    handler=lambda name, max_chars=4000: _load_skill(name, max_chars),
)


def _load_skill(name: str, max_chars: int) -> str:
    """加载 skill 内容"""
    reg = _get_registry()
    skill = reg.get(name)
    if not skill:
        results = reg.search(name, limit=1)
        if results:
            skill = results[0]
        else:
            return json.dumps({"error": f"Skill '{name}' 未找到"})

    reg.mark_loaded(skill.name)

    return json.dumps({
        "name": skill.name,
        "description": skill.description,
        "category": skill.category,
        "content": skill.content[:max_chars],
        "linked_files": {
            k: [f.split("/")[-1] for f in v]
            for k, v in skill.linked_files.items()
        },
        "loaded": True,
    }, ensure_ascii=False)


# ============================================================
# Skill 统计
# ============================================================

registry.register(
    name="skill_stats",
    description="查看 Skill 系统统计信息",
    parameters={"type": "object", "properties": {}},
    handler=lambda: json.dumps(_get_registry().stats(), ensure_ascii=False),
)


# ============================================================
# 读取 Skill 关联文件
# ============================================================

registry.register(
    name="skill_read_file",
    description="读取 Skill 目录下的关联文件 (references, templates, scripts)",
    parameters={
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "Skill 名称",
            },
            "file_path": {
                "type": "string",
                "description": "文件相对路径，如 'references/api.md'",
            },
        },
        "required": ["skill_name", "file_path"],
    },
    handler=lambda skill_name, file_path: _read_skill_file(skill_name, file_path),
)


def _read_skill_file(skill_name: str, file_path: str) -> str:
    """读取 skill 关联文件"""
    import os
    reg = _get_registry()
    skill = reg.get(skill_name)
    if not skill:
        return json.dumps({"error": f"Skill '{skill_name}' 未找到"})

    full_path = os.path.join(skill.path, file_path)
    if not os.path.exists(full_path):
        return json.dumps({"error": f"文件不存在: {file_path}"})

    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(10000)
        return json.dumps({"path": file_path, "content": content}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
