"""
Skill Loader — 解析和管理 Hermes Skills

Skills 存储在 ~/.hermes/skills/ 下，每个 skill 是一个目录，包含:
- SKILL.md: 主文件 (YAML frontmatter + Markdown 内容)
- references/: 参考文档
- templates/: 模板文件
- scripts/: 脚本文件

设计思想 (借鉴 Hermes):
- 不是所有 skill 都加载，而是按需加载
- Agent 根据用户任务自动选择合适的 skill
- Skill 内容注入到 system prompt 中
"""

import os
import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Skill:
    """单个 Skill 的结构"""
    name: str
    description: str
    category: str
    path: str
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)
    content: str = ""  # SKILL.md 的 markdown 内容 (不含 frontmatter)
    linked_files: dict = field(default_factory=dict)  # references/templates/scripts

    def to_context(self, max_chars: int = 4000) -> str:
        """将 skill 转换为 LLM 上下文"""
        header = f"## Skill: {self.name}\n{self.description}\n"
        body = self.content[:max_chars - len(header)]
        if len(self.content) > max_chars - len(header):
            body += "\n...(内容已截断)"
        return header + "\n" + body


class SkillRegistry:
    """Skill 注册中心 — 管理所有可用 Skills"""

    def __init__(self, skills_dir: str = None):
        self.skills_dir = Path(skills_dir or Path.home() / ".hermes" / "skills")
        self._skills: dict[str, Skill] = {}
        self._loaded: set[str] = set()  # 已加载到上下文的 skill

    def scan(self) -> int:
        """扫描 skills 目录，解析所有 SKILL.md"""
        count = 0
        for skill_md in self.skills_dir.rglob("SKILL.md"):
            try:
                skill = self._parse_skill(skill_md)
                if skill:
                    self._skills[skill.name] = skill
                    count += 1
            except Exception:
                continue
        return count

    def _parse_skill(self, path: Path) -> Skill | None:
        """解析单个 SKILL.md 文件"""
        content = path.read_text(encoding="utf-8", errors="ignore")

        # 解析 YAML frontmatter
        frontmatter, markdown = self._split_frontmatter(content)

        if not frontmatter:
            # 没有 frontmatter，用文件名作为 skill 名
            name = path.parent.name
            return Skill(
                name=name,
                description=markdown[:100].split("\n")[0],
                category=self._get_category(path),
                path=str(path.parent),
                content=markdown,
            )

        name = frontmatter.get("name", path.parent.name)
        description = frontmatter.get("description", "")
        version = frontmatter.get("version", "1.0.0")
        tags = frontmatter.get("tags", [])

        # 如果 tags 在 metadata.hermes 下
        metadata = frontmatter.get("metadata", {})
        if isinstance(metadata, dict):
            hermes = metadata.get("hermes", {})
            if isinstance(hermes, dict) and not tags:
                tags = hermes.get("tags", [])

        # 扫描 linked files
        linked = self._scan_linked_files(path.parent)

        return Skill(
            name=name,
            description=description,
            category=self._get_category(path),
            path=str(path.parent),
            version=version,
            tags=tags,
            content=markdown,
            linked_files=linked,
        )

    def _split_frontmatter(self, content: str) -> tuple[dict, str]:
        """分离 YAML frontmatter 和 markdown 内容"""
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
        if match:
            try:
                frontmatter = yaml.safe_load(match.group(1))
                return frontmatter or {}, match.group(2)
            except yaml.YAMLError:
                return {}, content
        return {}, content

    def _get_category(self, path: Path) -> str:
        """从路径提取分类"""
        parts = path.parts
        skills_idx = parts.index("skills") if "skills" in parts else -1
        if skills_idx >= 0 and skills_idx + 1 < len(parts) - 1:
            return parts[skills_idx + 1]
        return "general"

    def _scan_linked_files(self, skill_dir: Path) -> dict:
        """扫描 skill 目录下的关联文件"""
        linked = {}
        for subdir in ["references", "templates", "scripts", "assets"]:
            dir_path = skill_dir / subdir
            if dir_path.is_dir():
                linked[subdir] = [
                    str(f) for f in dir_path.iterdir() if f.is_file()
                ]
        return linked

    def list_skills(self, category: str = None) -> list[Skill]:
        """列出所有 skill"""
        skills = list(self._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return sorted(skills, key=lambda s: s.name)

    def get(self, name: str) -> Skill | None:
        """根据名字获取 skill"""
        return self._skills.get(name)

    def search(self, query: str, limit: int = 5) -> list[Skill]:
        """搜索 skill (关键词匹配)"""
        query_lower = query.lower()
        results = []

        for skill in self._skills.values():
            score = 0
            # 名字匹配
            if query_lower in skill.name.lower():
                score += 10
            # 描述匹配
            if query_lower in skill.description.lower():
                score += 5
            # 标签匹配
            for tag in skill.tags:
                if query_lower in tag.lower():
                    score += 3
            # 内容匹配
            if query_lower in skill.content.lower():
                score += 1

            if score > 0:
                results.append((score, skill))

        results.sort(key=lambda x: -x[0])
        return [s for _, s in results[:limit]]

    def categories(self) -> list[str]:
        """列出所有分类"""
        return sorted(set(s.category for s in self._skills.values()))

    def mark_loaded(self, name: str):
        """标记 skill 已加载到上下文"""
        self._loaded.add(name)

    def is_loaded(self, name: str) -> bool:
        """检查 skill 是否已加载"""
        return name in self._loaded

    def stats(self) -> dict:
        """统计信息"""
        return {
            "total": len(self._skills),
            "loaded": len(self._loaded),
            "categories": len(self.categories()),
            "by_category": {
                cat: len([s for s in self._skills.values() if s.category == cat])
                for cat in self.categories()
            },
        }
