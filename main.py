"""
My Agent v4 — 从零造的 AI Agent 框架 (完整版)

功能: 桌面操作 | 工具调用 | 安全分级 | 长期记忆 | 121 个 Skills

用法:
    uv run python main.py                    # 交互式对话
    uv run python main.py -q "你的问题"       # 单次问答
    uv run python main.py --desktop           # 启用桌面操作
    uv run python main.py --skill-stats      # 查看 Skill 统计
    uv run python main.py --memory-stats      # 查看记忆统计
"""

import argparse
import os
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="My Agent v4 — 完整版 AI Agent")
    parser.add_argument("-q", "--query", help="单次问答模式")
    parser.add_argument("--model", default=None, help="模型名称")
    parser.add_argument("--base-url", default=None, help="API Base URL")
    parser.add_argument("--api-key", default=None, help="API Key")
    parser.add_argument("--system", default=None, help="自定义系统提示词")
    parser.add_argument("--desktop", action="store_true", help="启用桌面操作工具")
    parser.add_argument("--auto-approve", action="store_true", help="自动批准所有操作")
    parser.add_argument("--vision", action="store_true", help="启用视觉分析")
    parser.add_argument("--memory-stats", action="store_true", help="查看记忆统计")
    parser.add_argument("--skill-stats", action="store_true", help="查看 Skill 统计")
    parser.add_argument("--skill-search", help="搜索 Skills")
    args = parser.parse_args()

    # 读取配置
    api_key = args.api_key or os.getenv("OPENAI_API_KEY", "")
    base_url = args.base_url or os.getenv("OPENAI_BASE_URL")
    model = args.model or os.getenv("MODEL_NAME", "gpt-4o-mini")

    if not api_key:
        print("❌ 请设置 API Key:")
        print("   方式1: export OPENAI_API_KEY=sk-xxx")
        print("   方式2: 创建 .env 文件写入 OPENAI_API_KEY=sk-xxx")
        print("   方式3: --api-key sk-xxx")
        return

    # 初始化 LLM Client
    from agent.llm_client import LLMClient
    llm = LLMClient(api_key=api_key, base_url=base_url, model=model)

    # 初始化记忆系统
    from agent.memory import MemoryStore
    memory = MemoryStore()

    # 初始化 Skill 系统
    from agent.skills import SkillRegistry
    skills = SkillRegistry()
    skill_count = skills.scan()

    # 注入 skill registry 到 skill_tools
    import tools.skill_tools as skill_tools_mod
    skill_tools_mod.set_skill_registry(skills)

    # Skill 搜索模式
    if args.skill_search:
        results = skills.search(args.skill_search, limit=10)
        for s in results:
            print(f"  [{s.category}] {s.name}: {s.description[:80]}")
        return

    # Skill 统计模式
    if args.skill_stats:
        import json
        stats = skills.stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        print("\n分类:")
        for cat, count in sorted(stats["by_category"].items()):
            print(f"  {cat}: {count} 个")
        return

    # 记忆统计模式
    if args.memory_stats:
        import json
        stats = memory.stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        print("\n最近记忆:")
        for m in memory.get_recent(limit=10):
            print(f"  [{m['type']}] {m['content'][:80]}")
        return

    # 注册工具
    import tools.builtin
    import tools.memory_tools
    import tools.skill_tools

    if args.desktop:
        import tools.desktop_tools
        print("🖥️  桌面操作已启用")

    # 初始化 Agent
    from agent.core import Agent
    agent = Agent(
        llm=llm,
        system_prompt=args.system,
        auto_approve=args.auto_approve,
        vision_enabled=args.vision,
        memory_store=memory,
        skill_registry=skills,
    )

    # 运行
    if args.query:
        response = agent.run(args.query)
        print(response)
    else:
        agent.chat_loop()


if __name__ == "__main__":
    main()
