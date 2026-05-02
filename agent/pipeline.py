"""
Pipeline — 任务分类和路由

借鉴 ClawdCursor 的 "Two Brains" 设计：
- Stage 0: 快捷命令 (零 LLM) — 简单任务直接执行
- Stage 1: 文本推理 (LLM) — 复杂任务规划执行
- Stage 2: 视觉辅助 (Vision LLM) — 需要看屏幕时启用

核心思想: 不是所有任务都需要 LLM，简单任务走快车道
"""

import json
import re
from enum import Enum
from typing import Any


class TaskType(Enum):
    """任务类型"""
    QUICK = "quick"      # 快捷命令: 打开应用、按键、简单计算
    CHAT = "chat"        # 普通对话: 问答、闲聊
    TOOL = "tool"        # 工具调用: 需要使用工具完成
    VISUAL = "visual"    # 视觉任务: 需要看屏幕 (截图+分析)


# ============================================================
# 快捷命令模式 (Stage 0: 零 LLM)
# ============================================================

QUICK_PATTERNS = [
    # 打开应用
    (r"^(打开|open|启动|launch)\s+(.+)", "open_app"),
    # 按键
    (r"^(按|press|按下)\s+(.+)", "key_press"),
    # 快捷键
    (r"^(快捷键|hotkey|组合键)\s+(.+)", "hotkey"),
    # 输入文字
    (r"^(输入|type|打字)\s+(.+)", "type_text"),
    # 简单计算
    (r"^(计算|算|calculate|calc)\s+(.+)", "calculator"),
    # 截图
    (r"^(截图|screenshot|截屏|屏幕)", "screenshot"),
    # 鼠标位置
    (r"^(鼠标|mouse|光标).*(位置|在哪|position)", "get_mouse_position"),
    # 等待
    (r"^(等待|wait|等)\s*(\d+)\s*(秒|s)", "wait"),
]


class Pipeline:
    """任务分类和路由"""

    def __init__(self, vision_enabled: bool = False):
        self.vision_enabled = vision_enabled

    def classify(self, user_input: str) -> tuple[TaskType, dict | None]:
        """
        分类用户输入

        返回:
            (task_type, quick_action)
            - quick_action 不为 None 时，表示可以直接执行
        """
        text = user_input.strip().lower()

        # Stage 0: 尝试匹配快捷命令
        for pattern, action in QUICK_PATTERNS:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                quick = self._build_quick_action(action, groups)
                if quick:
                    return TaskType.QUICK, quick

        # 检查是否需要视觉
        visual_keywords = ["看到", "屏幕上", "显示", "当前页面", "什么在", "what's on"]
        if any(kw in text for kw in visual_keywords) and self.vision_enabled:
            return TaskType.VISUAL, None

        # 检查是否是简单对话
        chat_keywords = ["你好", "谢谢", "你是谁", "hello", "hi", "thanks"]
        if any(kw == text for kw in chat_keywords):
            return TaskType.CHAT, None

        # 默认走工具调用
        return TaskType.TOOL, None

    def _build_quick_action(self, action: str, groups: tuple) -> dict | None:
        """构建快捷动作参数"""
        try:
            if action == "open_app":
                return {"tool": "open_app", "args": {"app_name": groups[1].strip()}}

            elif action == "key_press":
                key = groups[1].strip().lower()
                # 中文键名映射
                key_map = {
                    "回车": "enter", "确认": "enter", "回格": "backspace",
                    "删除": "delete", "制表": "tab", "退出": "escape",
                    "空格": "space", "上": "up", "下": "down",
                    "左": "left", "右": "right",
                }
                key = key_map.get(key, key)
                return {"tool": "key_press", "args": {"key": key}}

            elif action == "hotkey":
                keys = re.split(r'[\s+]+', groups[1].strip().lower())
                return {"tool": "hotkey", "args": {"keys": keys}}

            elif action == "type_text":
                return {"tool": "type_text", "args": {"text": groups[1].strip()}}

            elif action == "calculator":
                return {"tool": "calculator", "args": {"expression": groups[1].strip()}}

            elif action == "screenshot":
                return {"tool": "screenshot", "args": {}}

            elif action == "get_mouse_position":
                return {"tool": "get_mouse_position", "args": {}}

            elif action == "wait":
                seconds = int(groups[1])
                return {"tool": "wait", "args": {"seconds": seconds}}

        except Exception:
            pass

        return None
