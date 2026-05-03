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


def _setup_api_interactive() -> tuple:
    """首次启动交互式 API 配置向导"""
    import sys

    print()
    print("  ╔═══════════════════════════════════════╗")
    print("  ║       🌟 星骏 Agent API 配置          ║")
    print("  ╚═══════════════════════════════════════╝")
    print()
    print("  首次启动，请选择 API 提供商:")
    print()
    print("  1. OpenAI      (https://api.openai.com/v1)")
    print("  2. DeepSeek    (https://api.deepseek.com/v1)")
    print("  3. 小米 MiMo   (https://token-plan-cn.xiaomimimo.com/v1)")
    print("  4. 自定义")
    print()

    try:
        choice = input("  选择 [1-4]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消")
        return ("", "", "")

    providers = {
        "1": ("https://api.openai.com/v1", "gpt-4o-mini"),
        "2": ("https://api.deepseek.com/v1", "deepseek-chat"),
        "3": ("https://token-plan-cn.xiaomimimo.com/v1", "mimo-v2.5-pro"),
    }

    if choice in providers:
        base_url, model = providers[choice]
    elif choice == "4":
        try:
            base_url = input("  Base URL: ").strip()
            model = input("  Model 名称: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已取消")
            return ("", "", "")
    else:
        print("  ❌ 无效选择")
        return ("", "", "")

    try:
        api_key = input("  API Key: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消")
        return ("", "", "")

    if not api_key:
        print("  ❌ API Key 不能为空")
        return ("", "", "")

    # 保存到 .env
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(env_path, "w") as f:
            f.write(f"OPENAI_API_KEY={api_key}\n")
            f.write(f"OPENAI_BASE_URL={base_url}\n")
            f.write(f"MODEL_NAME={model}\n")
        print(f"\n  ✅ 配置已保存到 {env_path}")
    except Exception as e:
        print(f"\n  ⚠️  保存失败: {e}")
        print("  请手动创建 .env 文件")

    print(f"  📡 Provider: {base_url}")
    print(f"  🤖 Model: {model}")
    print()

    return (api_key, base_url, model)


def main():
    parser = argparse.ArgumentParser(description="星骏 Agent — 完整版 AI Agent")
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
    parser.add_argument("--setup", action="store_true", help="重新配置 API")
    args = parser.parse_args()

    # --setup: 重新配置 API
    if args.setup:
        _setup_api_interactive()
        return

    # 读取配置
    api_key = args.api_key or os.getenv("OPENAI_API_KEY", "")
    base_url = args.base_url or os.getenv("OPENAI_BASE_URL")
    model = args.model or os.getenv("MODEL_NAME", "gpt-4o-mini")

    # 没有 API Key 时，启动交互式配置
    if not api_key:
        api_key, base_url, model = _setup_api_interactive()
        if not api_key:
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

    # 检测 Termux 环境
    _is_termux = bool(os.environ.get("TERMUX_VERSION")) or os.path.exists("/data/data/com.termux")

    if args.desktop and _is_termux:
        print("⚠️  Termux 环境不支持桌面操作，已自动跳过 --desktop")
    elif args.desktop:
        import tools.desktop_tools
        print("🖥️  桌面操作已启用")
    else:
        # 非桌面模式也要导入 (注册空壳工具或完整工具)
        import tools.desktop_tools

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
