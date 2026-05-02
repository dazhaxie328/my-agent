#!/bin/bash
# ============================================================
# 星骏 Agent 快速启动脚本
# 用法: ./start.sh [--desktop] [--background]
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 解析参数
DESKTOP=""
BACKGROUND=""
QUERY=""

for arg in "$@"; do
    case $arg in
        --desktop|-d)
            DESKTOP="--desktop"
            ;;
        --background|-b)
            BACKGROUND="1"
            ;;
        --query|-q)
            shift
            QUERY="$1"
            ;;
        --help|-h)
            echo "星骏 Agent 启动脚本"
            echo ""
            echo "用法:"
            echo "  ./start.sh                    # 交互模式"
            echo "  ./start.sh --desktop          # 启用桌面操作"
            echo "  ./start.sh --background       # 后台运行 (tmux)"
            echo "  ./start.sh -q '你的问题'      # 单次问答"
            echo ""
            echo "组合:"
            echo "  ./start.sh --desktop --background  # 后台+桌面操作"
            exit 0
            ;;
    esac
done

# 检查 .env
if [ ! -f ".env" ]; then
    echo "❌ .env 不存在，请先运行 deploy.sh 配置 API Key"
    exit 1
fi

# 后台模式
if [ -n "$BACKGROUND" ]; then
    SESSION_NAME="xingjun"
    
    # 检查是否已有会话
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo "⚠️  星骏已在运行中"
        echo "   进入: tmux attach -t $SESSION_NAME"
        echo "   关闭: tmux kill-session -t $SESSION_NAME"
        exit 0
    fi
    
    echo "🌟 星骏后台启动中..."
    tmux new-session -d -s "$SESSION_NAME" -x 120 -y 30 \
        "cd $SCRIPT_DIR && uv run python main.py $DESKTOP"
    sleep 2
    
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo "✅ 星骏已后台运行"
        echo ""
        echo "   进入对话: tmux attach -t $SESSION_NAME"
        echo "   退出对话: Ctrl+B, D"
        echo "   关闭星骏: tmux kill-session -t $SESSION_NAME"
    else
        echo "❌ 启动失败，请检查日志"
    fi
    exit 0
fi

# 单次问答
if [ -n "$QUERY" ]; then
    uv run python main.py $DESKTOP -q "$QUERY"
    exit 0
fi

# 交互模式
echo "🌟 启动星骏 Agent..."
uv run python main.py $DESKTOP
