#!/bin/bash
# ============================================================
# 星骏 Agent 一键部署脚本
# 用法: curl -fsSL https://raw.githubusercontent.com/dazhaxie328/my-agent/main/deploy.sh | bash
# ============================================================

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 打印函数
info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }

echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════════╗"
echo "  ║       🌟 星骏 Agent 一键部署          ║"
echo "  ║   从零造的 AI Agent 框架              ║"
echo "  ╚═══════════════════════════════════════╝"
echo -e "${NC}"

# ============================================================
# Step 1: 检测环境
# ============================================================
info "检测系统环境..."

# 检测 OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     PLATFORM="Linux";;
    Darwin*)    PLATFORM="macOS";;
    *)          PLATFORM="Unknown";;
esac
ok "系统: ${PLATFORM}"

# 检测架构
ARCH="$(uname -m)"
ok "架构: ${ARCH}"

# ============================================================
# Step 2: 检查/安装依赖
# ============================================================
info "检查依赖..."

# Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    ok "Python: ${PYTHON_VERSION}"
else
    err "Python3 未安装"
    info "安装 Python3..."
    if [ "$PLATFORM" = "Linux" ]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update -qq && sudo apt-get install -y -qq python3
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3
        fi
    elif [ "$PLATFORM" = "macOS" ]; then
        brew install python3
    fi
fi

# uv (Python 包管理)
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version 2>&1 | awk '{print $2}')
    ok "uv: ${UV_VERSION}"
else
    info "安装 uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    if command -v uv &> /dev/null; then
        ok "uv 安装成功"
    else
        err "uv 安装失败，请手动安装: https://docs.astral.sh/uv/"
        exit 1
    fi
fi

# Git
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version 2>&1 | awk '{print $3}')
    ok "Git: ${GIT_VERSION}"
else
    err "Git 未安装，请先安装 Git"
    exit 1
fi

# tmux (可选，用于后台运行)
if command -v tmux &> /dev/null; then
    ok "tmux: 已安装"
else
    warn "tmux 未安装 (可选，用于后台运行)"
    info "安装 tmux..."
    if [ "$PLATFORM" = "Linux" ]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y -qq tmux 2>/dev/null || true
        fi
    elif [ "$PLATFORM" = "macOS" ]; then
        brew install tmux 2>/dev/null || true
    fi
fi

# ============================================================
# Step 3: 克隆项目
# ============================================================
INSTALL_DIR="${HOME}/my-agent"

if [ -d "$INSTALL_DIR" ]; then
    warn "目录已存在: ${INSTALL_DIR}"
    read -p "是否覆盖? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
    else
        info "跳过克隆，使用现有目录"
    fi
fi

if [ ! -d "$INSTALL_DIR" ]; then
    info "克隆项目..."
    git clone https://github.com/dazhaxie328/my-agent.git "$INSTALL_DIR"
    ok "克隆完成"
fi

cd "$INSTALL_DIR"

# ============================================================
# Step 4: 安装依赖
# ============================================================
info "安装 Python 依赖..."
uv sync 2>&1 | tail -3
ok "依赖安装完成"

# ============================================================
# Step 5: 配置 API Key
# ============================================================
ENV_FILE="$INSTALL_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    ok ".env 已存在"
else
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo -e "${CYAN}  配置 API Key${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo ""
    echo "  支持的 Provider:"
    echo "    1. OpenAI     (https://api.openai.com/v1)"
    echo "    2. DeepSeek   (https://api.deepseek.com/v1)"
    echo "    3. 小米 MiMo  (https://token-plan-cn.xiaomimimo.com/v1)"
    echo "    4. 自定义"
    echo ""
    read -p "  选择 [1-4]: " PROVIDER_CHOICE

    case $PROVIDER_CHOICE in
        1)
            BASE_URL="https://api.openai.com/v1"
            MODEL="gpt-4o-mini"
            ;;
        2)
            BASE_URL="https://api.deepseek.com/v1"
            MODEL="deepseek-chat"
            ;;
        3)
            BASE_URL="https://token-plan-cn.xiaomimimo.com/v1"
            MODEL="mimo-v2.5-pro"
            ;;
        4)
            read -p "  Base URL: " BASE_URL
            read -p "  Model: " MODEL
            ;;
        *)
            BASE_URL="https://api.openai.com/v1"
            MODEL="gpt-4o-mini"
            ;;
    esac

    read -p "  API Key: " API_KEY

    cat > "$ENV_FILE" << EOF
OPENAI_API_KEY=${API_KEY}
OPENAI_BASE_URL=${BASE_URL}
MODEL_NAME=${MODEL}
EOF

    ok ".env 已创建"
fi

# ============================================================
# Step 6: 验证安装
# ============================================================
info "验证安装..."

# 测试 API 连接
TEST_RESULT=$(uv run python main.py -q "你好" 2>&1 | head -5)
if echo "$TEST_RESULT" | grep -q "星骏"; then
    ok "API 连接正常"
else
    warn "API 连接可能有问题，请检查 API Key"
    echo "$TEST_RESULT"
fi

# ============================================================
# Step 7: 完成
# ============================================================
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       ✅ 星骏 Agent 部署完成！        ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}项目目录:${NC} ${INSTALL_DIR}"
echo -e "  ${CYAN}配置文件:${NC} ${ENV_FILE}"
echo ""
echo -e "  ${YELLOW}启动方式:${NC}"
echo ""
echo "    # 交互模式"
echo "    cd ~/my-agent && uv run python main.py"
echo ""
echo "    # 启用桌面操作"
echo "    cd ~/my-agent && uv run python main.py --desktop"
echo ""
echo "    # 后台运行 (tmux)"
echo "    tmux new-session -d -s xingjun 'cd ~/my-agent && uv run python main.py --desktop'"
echo "    tmux attach -t xingjun"
echo ""
echo "    # 单次问答"
echo "    cd ~/my-agent && uv run python main.py -q '你的问题'"
echo ""
echo -e "  ${YELLOW}快捷命令:${NC}"
echo ""
echo "    alias xingjun='cd ~/my-agent && uv run python main.py --desktop'"
echo "    alias xj='cd ~/my-agent && uv run python main.py -q'"
echo ""
echo -e "  ${CYAN}GitHub:${NC} https://github.com/dazhaxie328/my-agent"
echo ""
