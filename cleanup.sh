#!/bin/bash
# ============================================================
# 星骏 Agent 数据清理脚本
# 用法: ./cleanup.sh [--deep] [--dry-run]
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[SKIP]${NC} $1"; }

DEEP=0
DRY_RUN=0
TOTAL_FREED=0

for arg in "$@"; do
    case $arg in
        --deep) DEEP=1 ;;
        --dry-run) DRY_RUN=1 ;;
        --help|-h)
            echo "星骏 Agent 数据清理"
            echo ""
            echo "用法:"
            echo "  ./cleanup.sh           # 常规清理"
            echo "  ./cleanup.sh --deep    # 深度清理 (包括缓存)"
            echo "  ./cleanup.sh --dry-run # 预览清理内容"
            exit 0
            ;;
    esac
done

get_size() {
    du -sm "$1" 2>/dev/null | awk '{print $1}' || echo 0
}

clean_item() {
    local path=$1
    local desc=$2
    local size=$(get_size "$path" 2>/dev/null || echo 0)
    
    if [ "$size" -gt 0 ] 2>/dev/null; then
        if [ "$DRY_RUN" = "1" ]; then
            info "[预览] $desc: ${size}MB"
        else
            rm -rf "$path" 2>/dev/null || true
            ok "$desc: 已清理 ${size}MB"
            TOTAL_FREED=$((TOTAL_FREED + size))
        fi
    fi
}

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════╗"
echo "║     🧹 星骏数据清理                   ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${NC}"

# ============================================================
# 1. 临时文件
# ============================================================
info "清理临时文件..."

clean_item "/tmp/my-agent/screenshots/*.png" "旧截图 (>1天)"
if [ "$DRY_RUN" = "0" ]; then
    find /tmp/my-agent/screenshots -name "*.png" -mtime +1 -delete 2>/dev/null || true
fi

clean_item "/tmp/pip-*" "pip 临时文件"
clean_item "/tmp/uv-*" "uv 临时文件"

# ============================================================
# 2. 日志文件
# ============================================================
info "清理日志文件..."

# Hermes 日志 (>7天)
if [ -d "$HOME/.hermes/logs" ]; then
    LOG_SIZE=$(find "$HOME/.hermes/logs" -name "*.log" -mtime +7 -exec du -cm {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo 0)
    if [ "$LOG_SIZE" -gt 0 ] 2>/dev/null; then
        if [ "$DRY_RUN" = "0" ]; then
            find "$HOME/.hermes/logs" -name "*.log" -mtime +7 -delete 2>/dev/null || true
            ok "旧 Hermes 日志: 已清理 ${LOG_SIZE}MB"
        else
            info "[预览] 旧 Hermes 日志: ${LOG_SIZE}MB"
        fi
    fi
fi

# crypto-monitor 日志 (>30天，保留最近的)
if [ -d "$HOME/.crypto-monitor" ]; then
    find "$HOME/.crypto-monitor" -name "*.log.*" -mtime +30 -delete 2>/dev/null || true
fi

# ============================================================
# 3. 会话数据
# ============================================================
info "清理旧会话..."

if [ -d "$HOME/.hermes/sessions" ]; then
    SESSION_COUNT=$(find "$HOME/.hermes/sessions" -name "*.json" -mtime +30 2>/dev/null | wc -l)
    if [ "$SESSION_COUNT" -gt 0 ]; then
        if [ "$DRY_RUN" = "0" ]; then
            find "$HOME/.hermes/sessions" -name "*.json" -mtime +30 -delete 2>/dev/null || true
            ok "旧会话 (>30天): 已清理 ${SESSION_COUNT} 个"
        else
            info "[预览] 旧会话 (>30天): ${SESSION_COUNT} 个"
        fi
    fi
fi

# ============================================================
# 4. 星骏记忆清理 (只清理低重要性旧数据)
# ============================================================
info "检查星骏记忆..."

if [ -f "$HOME/.my-agent/memory.db" ]; then
    MEM_SIZE=$(get_size "$HOME/.my-agent/memory.db")
    ok "星骏记忆: ${MEM_SIZE}MB (保留)"
fi

# ============================================================
# 5. 深度清理 (缓存)
# ============================================================
if [ "$DEEP" = "1" ]; then
    info "深度清理: 包管理缓存..."
    
    # uv 缓存
    if command -v uv &> /dev/null; then
        UV_SIZE=$(get_size "$HOME/.cache/uv")
        if [ "$UV_SIZE" -gt 1000 ]; then
            if [ "$DRY_RUN" = "0" ]; then
                uv cache clean 2>/dev/null || true
                ok "uv 缓存: 已清理"
            else
                info "[预览] uv 缓存: ${UV_SIZE}MB"
            fi
        else
            warn "uv 缓存: ${UV_SIZE}MB (较小，跳过)"
        fi
    fi
    
    # pip 缓存
    if command -v pip &> /dev/null; then
        PIP_SIZE=$(get_size "$HOME/.cache/pip")
        if [ "$PIP_SIZE" -gt 500 ]; then
            if [ "$DRY_RUN" = "0" ]; then
                pip cache purge 2>/dev/null || true
                ok "pip 缓存: 已清理"
            else
                info "[预览] pip 缓存: ${PIP_SIZE}MB"
            fi
        else
            warn "pip 缓存: ${PIP_SIZE}MB (较小，跳过)"
        fi
    fi
    
    # yarn 缓存
    if command -v yarn &> /dev/null; then
        YARN_SIZE=$(get_size "$HOME/.cache/yarn")
        if [ "$YARN_SIZE" -gt 500 ]; then
            if [ "$DRY_RUN" = "0" ]; then
                yarn cache clean 2>/dev/null || true
                ok "yarn 缓存: 已清理"
            else
                info "[预览] yarn 缓存: ${YARN_SIZE}MB"
            fi
        fi
    fi
    
    # camoufox 缓存
    clean_item "$HOME/.cache/camoufox" "camoufox 缓存"
    
    # puppeteer 缓存
    clean_item "$HOME/.cache/puppeteer" "puppeteer 缓存"
fi

# ============================================================
# 6. 系统垃圾
# ============================================================
info "清理系统垃圾..."

# 清理 trash
if [ -d "$HOME/.local/share/Trash" ]; then
    TRASH_SIZE=$(get_size "$HOME/.local/share/Trash")
    if [ "$TRASH_SIZE" -gt 100 ]; then
        if [ "$DRY_RUN" = "0" ]; then
            rm -rf "$HOME/.local/share/Trash"/* 2>/dev/null || true
            ok "回收站: 已清理 ${TRASH_SIZE}MB"
        else
            info "[预览] 回收站: ${TRASH_SIZE}MB"
        fi
    fi
fi

# 清理 core dumps
find "$HOME" -name "core.*" -mtime +7 -delete 2>/dev/null || true

# ============================================================
# 总结
# ============================================================
echo ""
if [ "$DRY_RUN" = "1" ]; then
    echo -e "${YELLOW}预览完成，使用 ./cleanup.sh 执行清理${NC}"
else
    echo -e "${GREEN}清理完成！释放约 ${TOTAL_FREED}MB${NC}"
    echo ""
    df -h / | tail -1
fi
