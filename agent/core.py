"""
Agent Loop — 核心对话循环 (v4: 集成 Skill 系统)

v4 新增:
- Skill 系统: 121 个预置知识库
- 自动匹配: 根据用户任务自动加载相关 Skill
- Skill 上下文: Skill 内容注入 system prompt 指导操作

记忆 + Skill + 安全 + Pipeline = 完整的 Agent 架构
"""

import json
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from agent.llm_client import LLMClient
from agent.pipeline import Pipeline, TaskType
from agent.safety import SafetyLayer, SafetyTier
from agent.memory import MemoryStore
from agent.skills import SkillRegistry
from tools.registry import registry

console = Console()


class Agent:
    """AI Agent — 对话循环引擎 (v4)"""

    def __init__(self, llm: LLMClient, system_prompt: str = None,
                 auto_approve: bool = False, vision_enabled: bool = False,
                 memory_store: MemoryStore = None,
                 skill_registry: SkillRegistry = None):
        self.llm = llm
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.messages: list[dict] = []
        self.max_iterations = 10

        # 核心组件
        self.pipeline = Pipeline(vision_enabled=vision_enabled)
        self.safety = SafetyLayer(auto_approve=auto_approve)
        self.memory = memory_store or MemoryStore()
        self.skills = skill_registry or SkillRegistry()
        self.conversation_turns = 0

        # 扫描 skills
        skill_count = self.skills.scan()
        console.print(f"  [dim]📚 已加载 {skill_count} 个 Skills[/dim]")

    def _default_system_prompt(self) -> str:
        return """你是一个有桌面操作能力、长期记忆和知识库的 AI 助手。

核心能力:
1. 工具调用: 计算、文件操作、执行命令、桌面操作
2. 长期记忆: 保存和检索用户信息、偏好、学习内容
3. 知识库: 121 个 Skills 覆盖 Web3、GitHub、社交媒体、开发工具等

工具使用规则:
- calculator: 数学计算
- run_command: 执行 shell 命令
- read_file / write_file: 文件操作
- mouse_click / type_text / hotkey: 桌面操作
- screenshot: 截图查看屏幕
- memory_save / memory_search: 记忆操作
- skill_search / skill_load: 知识库操作

Skill 使用规则:
- 遇到专业任务时，先 skill_search 查找相关知识
- 找到后用 skill_load 加载完整内容
- 按 Skill 的指导执行操作
- Skill 覆盖: web3, github, social-media, crypto, 开发工具等

记忆使用规则:
- 用户个人信息 → memory_save type=fact
- 用户偏好 → memory_save type=preference
- 新知识 → memory_save type=learning
- 需要回忆 → memory_search

回答规则:
- 简洁明了，用中文回复
- 专业术语保留英文 (TVL, APY, Sybil 等)
- 优先使用 Skill 中的最佳实践
- 重要信息记得保存到记忆"""

    def _build_context(self, user_input: str) -> str:
        """构建完整的上下文 (记忆 + Skill)"""
        parts = [self.system_prompt]

        # 1. 加载相关记忆
        try:
            memories = self.memory.search(user_input, limit=5)
            if not memories:
                memories = self.memory.get_important(limit=3)
            if memories:
                parts.append(self.memory.format_for_context(memories))
        except Exception:
            pass

        # 2. 自动匹配相关 Skill (轻量级: 只加载描述)
        try:
            matched_skills = self.skills.search(user_input, limit=3)
            if matched_skills:
                skill_hints = "\n## 相关知识库 (可 skill_load 加载)\n"
                for s in matched_skills:
                    skill_hints += f"- **{s.name}**: {s.description[:80]}\n"
                parts.append(skill_hints)
        except Exception:
            pass

        return "\n\n".join(parts)

    def _auto_save_memory(self, user_input: str, response: str):
        """自动检测并保存重要信息"""
        import re
        save_triggers = [
            (r"我叫|我的名字是|我是", "fact", 4),
            (r"我做|我的工作是|我在.*工作", "fact", 4),
            (r"我喜欢|我偏好|我习惯", "preference", 3),
            (r"我的项目|我在做|我负责", "fact", 4),
            (r"记住|记下来|别忘了", "learning", 4),
        ]

        for pattern, mem_type, importance in save_triggers:
            if re.search(pattern, user_input):
                content = user_input[:200]
                self.memory.add(
                    type=mem_type,
                    content=content,
                    source="对话自动提取",
                    importance=importance,
                    tags=["auto_save"],
                )
                console.print(f"  [dim]💾 自动保存记忆: {content[:50]}...[/dim]")
                break

    def run(self, user_input: str) -> str:
        """处理一轮用户输入"""
        self.conversation_turns += 1

        # ========== Stage 0: Pipeline 快捷命令 ==========
        task_type, quick_action = self.pipeline.classify(user_input)

        if task_type == TaskType.QUICK and quick_action:
            tool_name = quick_action["tool"]
            tool_args = quick_action["args"]

            console.print(f"  [yellow]⚡ 快捷命令: {tool_name}[/yellow]")

            if not self.safety.approve(tool_name, tool_args):
                return "操作被取消"

            result = registry.execute(tool_name, json.dumps(tool_args, ensure_ascii=False))
            return f"✅ 已执行: {tool_name}\n{result}"

        # ========== 构建上下文 (记忆 + Skill) ==========
        context = self._build_context(user_input)

        # 替换 system message
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = context
        else:
            self.messages.insert(0, {"role": "system", "content": context})

        # ========== Stage 1+: LLM 对话循环 ==========
        self.messages.append({"role": "user", "content": user_input})

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            console.print(f"  [dim]💭 思考中... (第{iteration}轮)[/dim]")
            response = self.llm.chat(
                messages=self.messages,
                tools=registry.to_schemas() if registry.list_tools() else None,
            )

            # 分支A: LLM 要调用工具
            if response.tool_calls:
                self.messages.append(response)

                for tool_call in response.tool_calls:
                    func_name = tool_call.function.name
                    func_args = tool_call.function.arguments

                    try:
                        args_dict = json.loads(func_args) if isinstance(func_args, str) else func_args
                    except json.JSONDecodeError:
                        args_dict = {}

                    # 安全检查 (记忆和 skill 操作不需要确认)
                    is_safe_op = func_name.startswith("memory_") or func_name.startswith("skill_")
                    if not is_safe_op and not self.safety.approve(func_name, args_dict):
                        result = json.dumps({"error": "操作被用户拒绝"})
                    else:
                        console.print(f"  [cyan]🔧 调用工具: {func_name}[/cyan]")
                        result = registry.execute(func_name, func_args)
                        console.print(f"  [dim]   结果: {result[:200]}[/dim]")

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })

            # 分支B: LLM 返回纯文字 → 结束
            elif response.content:
                self.messages.append({"role": "assistant", "content": response.content})
                self._auto_save_memory(user_input, response.content)
                return response.content

            else:
                return "[Agent 未返回有效内容]"

        return "[达到最大迭代次数，停止]"

    def chat_loop(self):
        """交互式对话循环"""
        mem_stats = self.memory.stats()
        skill_stats = self.skills.stats()

        console.print(Panel.fit(
            f"[bold green]🤖 My Agent v4[/bold green]\n"
            f"[dim]桌面操作 | 工具调用 | 安全分级 | 长期记忆 | 知识库[/dim]\n"
            f"[dim]记忆: {mem_stats['total']} 条 | Skills: {skill_stats['total']} 个[/dim]\n"
            f"[dim]输入消息开始对话，'quit' 退出[/dim]",
            border_style="green",
        ))

        while True:
            try:
                user_input = console.input("\n[bold blue]你> [/bold blue]").strip()
            except (EOFError, KeyboardInterrupt):
                self._save_conversation_summary()
                console.print("\n[dim]再见！[/dim]")
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                self._save_conversation_summary()
                console.print("[dim]再见！[/dim]")
                break

            response = self.run(user_input)

            console.print()
            console.print(Panel(
                Markdown(response),
                title="[bold green]Agent[/bold green]",
                border_style="green",
            ))

    def _save_conversation_summary(self):
        """对话结束时保存摘要"""
        if self.conversation_turns < 3:
            return

        user_msgs = [m["content"] for m in self.messages if m.get("role") == "user"]
        if not user_msgs:
            return

        summary = "对话摘要: " + "; ".join(user_msgs[:5])
        if len(summary) > 500:
            summary = summary[:500] + "..."

        self.memory.add(
            type="conversation",
            content=summary,
            source="自动保存",
            importance=2,
            tags=["auto_summary"],
        )
        console.print(f"  [dim]💾 对话摘要已保存[/dim]")
