"""
Safety Layer — 操作安全分级

借鉴 ClawdCursor 的安全设计：
- Auto: 自动执行 (读屏幕、读文件、计算)
- Confirm: 需用户确认 (点击、打字、发消息)
- Block: 禁止执行 (rm -rf、格式化、发送密码)

核心思想: 不是所有操作都应该自动执行
"""

import json
from enum import Enum
from typing import Callable


class SafetyTier(Enum):
    """安全等级"""
    AUTO = "auto"          # 自动执行
    CONFIRM = "confirm"    # 需要用户确认
    BLOCK = "block"        # 禁止执行


# ============================================================
# 操作 → 安全等级映射
# ============================================================

SAFETY_RULES = {
    # === AUTO: 自动执行 ===
    "read_file": SafetyTier.AUTO,
    "calculator": SafetyTier.AUTO,
    "screenshot": SafetyTier.AUTO,
    "get_mouse_position": SafetyTier.AUTO,
    "get_screen_size": SafetyTier.AUTO,
    "wait": SafetyTier.AUTO,

    # === CONFIRM: 需要确认 ===
    "run_command": SafetyTier.CONFIRM,
    "write_file": SafetyTier.CONFIRM,
    "mouse_click": SafetyTier.CONFIRM,
    "mouse_move": SafetyTier.CONFIRM,
    "mouse_drag": SafetyTier.CONFIRM,
    "mouse_scroll": SafetyTier.CONFIRM,
    "type_text": SafetyTier.CONFIRM,
    "key_press": SafetyTier.CONFIRM,
    "hotkey": SafetyTier.CONFIRM,
    "open_app": SafetyTier.CONFIRM,

    # === BLOCK: 禁止执行 ===
    # (通过命令黑名单实现)
}

# 危险命令黑名单
BLOCKED_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=",
    ":(){:|:&};:",  # fork bomb
    "chmod -R 777 /",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "> /dev/sda",
]


class SafetyLayer:
    """安全层 — 操作分级和确认"""

    def __init__(self, auto_approve: bool = False):
        """
        参数:
            auto_approve: True = 跳过所有确认 (危险! 仅测试用)
        """
        self.auto_approve = auto_approve
        self.confirm_callback: Callable[[str, dict], bool] | None = None

    def set_confirm_callback(self, callback: Callable[[str, dict], bool]):
        """设置确认回调函数 (UI 层注入)"""
        self.confirm_callback = callback

    def check(self, tool_name: str, arguments: dict) -> tuple[SafetyTier, str]:
        """
        检查操作安全等级

        返回:
            (tier, reason) — tier 是安全等级，reason 是说明
        """
        # 1. 检查是否在黑名单
        if tool_name == "run_command":
            cmd = arguments.get("command", "")
            for pattern in BLOCKED_PATTERNS:
                if pattern in cmd:
                    return SafetyTier.BLOCK, f"危险命令: 包含 '{pattern}'"

        # 2. 查找安全等级
        tier = SAFETY_RULES.get(tool_name, SafetyTier.CONFIRM)

        # 3. 生成说明
        reasons = {
            SafetyTier.AUTO: f"✅ {tool_name}: 安全操作，自动执行",
            SafetyTier.CONFIRM: f"⚠️  {tool_name}: 需要确认",
            SafetyTier.BLOCK: f"🚫 {tool_name}: 被安全策略阻止",
        }

        return tier, reasons[tier]

    def approve(self, tool_name: str, arguments: dict) -> bool:
        """
        请求用户批准

        返回:
            True = 批准, False = 拒绝
        """
        tier, reason = self.check(tool_name, arguments)

        # 自动执行
        if tier == SafetyTier.AUTO:
            return True

        # 禁止执行
        if tier == SafetyTier.BLOCK:
            print(f"\n{reason}")
            return False

        # 需要确认
        if self.auto_approve:
            return True

        # 调用外部确认回调
        if self.confirm_callback:
            return self.confirm_callback(tool_name, arguments)

        # 默认: 终端交互确认
        return self._terminal_confirm(tool_name, arguments, reason)

    def _terminal_confirm(self, tool_name: str, arguments: dict, reason: str) -> bool:
        """终端确认交互"""
        print(f"\n{reason}")
        print(f"  工具: {tool_name}")

        # 简化参数显示
        args_str = json.dumps(arguments, ensure_ascii=False)
        if len(args_str) > 200:
            args_str = args_str[:200] + "..."
        print(f"  参数: {args_str}")

        try:
            answer = input("  执行? [y/N] ").strip().lower()
            return answer in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False
