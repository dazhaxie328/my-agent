#!/bin/bash
# ============================================================
# 星骏 Agent 一键部署脚本
# 支持: Linux / macOS / WSL / Termux (Android)
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

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

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

# 检测 Termux
IS_TERMUX=0
if [ -n "$TERMUX_VERSION" ] || [ -d "/data/data/com.termux" ]; then
    IS_TERMUX=1
    PLATFORM="Termux (Android)"
    ok "检测到 Termux 环境"
else
    OS="$(uname -s)"
    case "${OS}" in
        Linux*)     PLATFORM="Linux";;
        Darwin*)    PLATFORM="macOS";;
        *)          PLATFORM="Unknown";;
    esac
fi

# 检测 WSL
IS_WSL=0
if grep -qi "microsoft" /proc/version 2>/dev/null; then
    IS_WSL=1
    PLATFORM="WSL (Windows)"
    ok "检测到 WSL 环境"
fi

ok "系统: ${PLATFORM}"

# ============================================================
# Step 2: 安装依赖
# ============================================================
info "检查并安装依赖..."

install_pkg() {
    local pkg=$1
    if command -v "$pkg" &> /dev/null; then
        ok "$pkg: 已安装"
        return 0
    fi

    info "安装 $pkg..."
    if [ "$IS_TERMUX" = "1" ]; then
        pkg install -y "$pkg" 2>/dev/null || true
    elif [ "$PLATFORM" = "macOS" ]; then
        brew install "$pkg" 2>/dev/null || true
    else
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y -qq "$pkg" 2>/dev/null || true
        elif command -v yum &> /dev/null; then
            sudo yum install -y "$pkg" 2>/dev/null || true
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm "$pkg" 2>/dev/null || true
        fi
    fi

    if command -v "$pkg" &> /dev/null; then
        ok "$pkg: 安装成功"
    else
        warn "$pkg: 安装失败，可能需要手动安装"
    fi
}

# Termux 特殊依赖
if [ "$IS_TERMUX" = "1" ]; then
    info "Termux 环境: 安装基础依赖..."
    pkg update -y 2>/dev/null || true
    pkg install -y python git openssh 2>/dev/null || true
    
    # Termux 的 python 就是 python3
    if ! command -v python3 &> /dev/null && command -v python &> /dev/null; then
        ln -sf "$(which python)" "$PREFIX/bin/python3" 2>/dev/null || true
    fi
fi

# 通用依赖
install_pkg python3
install_pkg git

# uv (Python 包管理)
if command -v uv &> /dev/null; then
    ok "uv: 已安装"
else
    info "安装 uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # 添加到 PATH
    export PATH="$HOME/.local/bin:$PATH"
    if [ -f "$HOME/.cargo/env" ]; then
        source "$HOME/.cargo/env" 2>/dev/null || true
    fi
    
    if command -v uv &> /dev/null; then
        ok "uv: 安装成功"
    else
        err "uv 安装失败，请手动安装: https://docs.astral.sh/uv/"
    fi
fi

# tmux (可选)
if command -v tmux &> /dev/null; then
    ok "tmux: 已安装"
else
    if [ "$IS_TERMUX" = "1" ]; then
        info "Termux: 安装 tmux..."
        pkg install -y tmux 2>/dev/null || true
    elif [ "$PLATFORM" = "macOS" ]; then
        brew install tmux 2>/dev/null || true
    else
        install_pkg tmux
    fi
fi

# ============================================================
# Step 3: 克隆项目
# ============================================================
INSTALL_DIR="$HOME/my-agent"

if [ -d "$INSTALL_DIR/.git" ]; then
    ok "项目已存在，更新中..."
    cd "$INSTALL_DIR"
    git pull 2>/dev/null || true
else
    info "克隆项目..."
    [ -d "$INSTALL_DIR" ] && rm -rf "$INSTALL_DIR"
    git clone https://github.com/dazhaxie328/my-agent.git "$INSTALL_DIR"
    ok "克隆完成"
fi

cd "$INSTALL_DIR"

# ============================================================
# Step 4: 安装 Python 依赖
# ============================================================
info "安装 Python 依赖..."

# Termux 需要特殊处理
if [ "$IS_TERMUX" = "1" ]; then
    # Termux 上不安装桌面依赖 (pyautogui/pytesseract 需要图形环境)
    export CFLAGS="-Wno-error"
    uv sync 2>&1 | tail -5 || {
        warn "部分依赖可能安装失败，尝试跳过可选依赖..."
        uv sync --no-deps 2>/dev/null || true
    }
else
    uv sync 2>&1 | tail -3
    # 桌面环境额外安装桌面依赖 (可选)
    if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
        uv sync --extra desktop 2>&1 | tail -3 || true
    fi
fi

ok "依赖安装完成"

# ============================================================
# Step 5: 配置 API Key
# ============================================================
ENV_FILE="$INSTALL_DIR/.env"

if [ -f "$ENV_FILE" ] && grep -q "OPENAI_API_KEY" "$ENV_FILE"; then
    ok ".env 已存在且已配置"
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
        1) BASE_URL="https://api.openai.com/v1"; MODEL="gpt-4o-mini" ;;
        2) BASE_URL="https://api.deepseek.com/v1"; MODEL="deepseek-chat" ;;
        3) BASE_URL="https://token-plan-cn.xiaomimimo.com/v1"; MODEL="mimo-v2.5-pro" ;;
        4) read -p "  Base URL: " BASE_URL; read -p "  Model: " MODEL ;;
        *) BASE_URL="https://api.openai.com/v1"; MODEL="gpt-4o-mini" ;;
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
# Step 6: 注册命令 (星骏)
# ============================================================
info "注册启动命令..."

SHELL_RC=""
if [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
elif [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.profile" ]; then
    SHELL_RC="$HOME/.profile"
fi

# 创建启动脚本
LAUNCHER="$HOME/.local/bin/xingjun"
mkdir -p "$HOME/.local/bin"

cat > "$LAUNCHER" << 'LAUNCHER_EOF'
#!/bin/bash
# 星骏 Agent 启动器
cd "$HOME/my-agent" 2>/dev/null || { echo "❌ 项目目录不存在，请先运行部署脚本"; exit 1; }

# 检查参数
DESKTOP=""
QUERY=""
BG=""

for arg in "$@"; do
    case $arg in
        --desktop|-d) DESKTOP="--desktop" ;;
        --background|-b) BG="1" ;;
        --help|-h)
            echo "🌟 星骏 Agent"
            echo ""
            echo "用法:"
            echo "  星骏                    # 交互模式"
            echo "  星骏 --desktop          # 启用桌面操作"
            echo "  星骏 --background       # 后台运行"
            echo "  星骏 -q '问题'          # 单次问答"
            echo "  星骏 --skill-stats      # 查看 Skills"
            echo "  星骏 --memory-stats     # 查看记忆"
            exit 0
            ;;
    esac
done

# 后台模式
if [ -n "$BG" ]; then
    SESSION="xingjun"
    if tmux has-session -t "$SESSION" 2>/dev/null; then
        echo "⚠️  星骏已在运行"
        echo "   进入: tmux attach -t $SESSION"
        echo "   关闭: tmux kill-session -t $SESSION"
        exit 0
    fi
    tmux new-session -d -s "$SESSION" "uv run python main.py $DESKTOP"
    sleep 2
    echo "✅ 星骏已后台运行"
    echo "   进入: tmux attach -t $SESSION"
    exit 0
fi

# 单次问答
if [ -n "$1" ] && [ "$1" = "-q" ] && [ -n "$2" ]; then
    shift
    uv run python main.py $DESKTOP -q "$*"
    exit 0
fi

# 交互模式
uv run python main.py $DESKTOP
LAUNCHER_EOF

chmod +x "$LAUNCHER"

# 添加到 PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
    
    if [ -n "$SHELL_RC" ]; then
        if ! grep -q '.local/bin' "$SHELL_RC" 2>/dev/null; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
            ok "已添加 PATH 到 $SHELL_RC"
        fi
    fi
fi

# 创建中文别名
ALIAS_NAME="星骏"
ALIAS_CMD='alias 星骏="$HOME/.local/bin/xingjun"'

if [ -n "$SHELL_RC" ]; then
    if ! grep -q "alias 星骏" "$SHELL_RC" 2>/dev/null; then
        echo "$ALIAS_CMD" >> "$SHELL_RC"
        ok "已注册命令: 星骏"
    else
        ok "命令已存在: 星骏"
    fi
fi

# 同时创建 xingjun 别名
ALIAS_CMD2='alias xingjun="$HOME/.local/bin/xingjun"'
if [ -n "$SHELL_RC" ]; then
    if ! grep -q "alias xingjun=" "$SHELL_RC" 2>/dev/null; then
        echo "$ALIAS_CMD2" >> "$SHELL_RC"
    fi
fi

# ============================================================
# Step 7: Termux 特殊优化
# ============================================================
if [ "$IS_TERMUX" = "1" ]; then
    info "Termux 优化..."
    
    # Termux 通知支持
    if command -v termux-notification &> /dev/null; then
        ok "Termux API 可用"
    else
        warn "可选安装 Termux API: pkg install termux-api"
    fi
    
    # 防止 Termux 休眠
    echo ""
    echo "  💡 Termux 提示:"
    echo "     - 保持后台运行: termux-wake-lock"
    echo "     - 安装 Termux API: pkg install termux-api"
    echo "     - 建议安装 Termux:Boot 实现开机自启"
fi

# ============================================================
# Step 8: 完成
# ============================================================
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       ✅ 星骏 Agent 部署完成！        ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}项目目录:${NC} ${INSTALL_DIR}"
echo -e "  ${CYAN}配置文件:${NC} ${ENV_FILE}"
echo ""
echo -e "  ${YELLOW}启动命令 (重新打开终端后生效):${NC}"
echo ""
echo "    星骏                    # 交互模式"
echo "    星骏 --desktop          # 启用桌面操作"
echo "    星骏 --background       # 后台运行"
echo "    星骏 -q '你的问题'      # 单次问答"
echo "    星骏 --help             # 查看帮助"
echo ""
echo -e "  ${YELLOW}当前终端立即生效:${NC}"
echo ""
echo "    source ${SHELL_RC:-~/.bashrc}"
echo "    星骏"
echo ""
echo -e "  ${CYAN}GitHub:${NC} https://github.com/dazhaxie328/my-agent"
echo ""

# 提示重新加载 shell
if [ -n "$SHELL_RC" ]; then
    echo -e "  ${YELLOW}运行以下命令使命令立即可用:${NC}"
    echo "    source $SHELL_RC"
fi
