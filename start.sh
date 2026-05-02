#!/bin/bash
# 星骏 Agent 快速启动
cd "$HOME/my-agent" 2>/dev/null || { echo "❌ 请先运行部署脚本"; exit 1; }
uv run python main.py "$@"
