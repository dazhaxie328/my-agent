# 星骏 (Xīngjùn)

星骏 — 从零造的 AI Agent 框架 — 学习 Agent 底层原理的实战项目。

## 一键部署

```bash
# 方式1: 直接运行
curl -fsSL https://raw.githubusercontent.com/dazhaxie328/my-agent/main/deploy.sh | bash

# 方式2: 下载后运行
wget https://raw.githubusercontent.com/dazhaxie328/my-agent/main/deploy.sh
chmod +x deploy.sh
./deploy.sh
```

## 快速启动

```bash
cd ~/my-agent

# 交互模式
./start.sh

# 启用桌面操作
./start.sh --desktop

# 后台运行 (tmux)
./start.sh --desktop --background

# 单次问答
./start.sh -q "你的问题"

# 查看帮助
./start.sh --help
```

## 特性

- 🧠 **LLM 对话** — 支持任意 OpenAI 兼容模型
- 🔧 **23 个工具** — 计算、文件、命令、桌面操作、记忆、知识库
- 📚 **121 个 Skills** — 预置知识库覆盖 Web3、GitHub、社交媒体
- 💾 **长期记忆** — SQLite 持久化，跨对话记住用户信息
- 🖥️ **桌面操作** — 鼠标、键盘、截图、打开应用
- 🛡️ **安全分级** — Auto/Confirm/Block 三级安全控制
- ⚡ **Pipeline** — 快捷命令零 LLM 直接执行

## 架构

```
用户输入
   │
   ▼
Pipeline (任务分类)
   │
   ├─ 快捷命令 → 直接执行 (零 LLM)
   │
   └─ 复杂任务 → LLM 对话循环
                    │
                    ├─ 记忆上下文 (SQLite)
                    ├─ Skill 上下文 (121 个知识库)
                    │
                    └─ 工具调用
                         ├─ 安全检查
                         └─ 执行返回
```

## 快速开始

```bash
# 克隆
git clone https://github.com/dazhaxie328/my-agent.git
cd my-agent

# 安装依赖
uv sync

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 运行
uv run python main.py

# 启用桌面操作
uv run python main.py --desktop
```

## 使用方式

```bash
# 交互式对话
uv run python main.py

# 单次问答
uv run python main.py -q "你的问题"

# 桌面操作
uv run python main.py --desktop

# 查看记忆统计
uv run python main.py --memory-stats

# 搜索 Skills
uv run python main.py --skill-search "crypto"

# 查看 Skill 统计
uv run python main.py --skill-stats
```

## 对话示例

```
你> 计算 math.sqrt(256) + 100
⚡ 快捷命令: calculator
✅ 已执行: calculator
{"result": 116.0}

你> 我叫大闸蟹，做 Web3 撸毛投研
🔧 调用工具: memory_save
已记住 ✅

你> 我叫什么？
🔧 调用工具: memory_search
你叫大闸蟹 🦀

你> 搜索一下关于 crypto 的 skill
🔧 调用工具: skill_search
找到: crypto-monitor, crypto-operations, polymarket...
```

## 项目结构

```
my-agent/
├── main.py                 # 入口
├── .env.example            # API 配置模板
├── agent/
│   ├── llm_client.py       # LLM 调用层
│   ├── core.py             # Agent 核心循环
│   ├── vision.py           # 视觉层 (截图)
│   ├── desktop.py          # 桌面操作 (鼠标/键盘)
│   ├── pipeline.py         # 任务分类路由
│   ├── safety.py           # 安全层 (操作分级)
│   ├── memory.py           # 记忆系统 (SQLite)
│   └── skills.py           # Skill 系统
└── tools/
    ├── registry.py          # 工具注册中心
    ├── builtin.py           # 基础工具
    ├── desktop_tools.py     # 桌面工具
    ├── memory_tools.py      # 记忆工具
    └── skill_tools.py       # Skill 工具
```

## 核心设计 (借鉴 ClawdCursor)

1. **Pipeline** — 任务分级，简单任务零 LLM
2. **Safety Layer** — 操作安全三级控制
3. **Memory** — SQLite 持久化长期记忆
4. **Skills** — 121 个预置知识库按需加载

## 配置

支持的模型 (通过 .env 配置):

| Provider | Base URL | Model |
|----------|----------|-------|
| OpenAI | https://api.openai.com/v1 | gpt-4o-mini |
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat |
| 小米 MiMo | https://token-plan-cn.xiaomimimo.com/v1 | mimo-v2.5-pro |
| 本地 Ollama | http://localhost:11434/v1 | llama3 |

## License

MIT
