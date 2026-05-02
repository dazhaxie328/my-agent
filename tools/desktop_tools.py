"""
桌面工具集 — 注册所有桌面操作工具到 Registry
"""

import json
from tools.registry import registry
from agent.desktop import DesktopLayer
from agent.vision import VisionLayer

# 创建层实例
desktop = DesktopLayer()
vision = VisionLayer()


# ============================================================
# 鼠标工具
# ============================================================

registry.register(
    name="mouse_click",
    description="点击屏幕上的指定位置。需要提供 x, y 坐标。",
    parameters={
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "屏幕 X 坐标"},
            "y": {"type": "integer", "description": "屏幕 Y 坐标"},
            "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
            "clicks": {"type": "integer", "description": "点击次数 (2=双击)", "default": 1},
        },
        "required": ["x", "y"],
    },
    handler=lambda x, y, button="left", clicks=1: desktop.mouse_click(x, y, button, clicks),
)

registry.register(
    name="mouse_move",
    description="移动鼠标到指定位置",
    parameters={
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "屏幕 X 坐标"},
            "y": {"type": "integer", "description": "屏幕 Y 坐标"},
        },
        "required": ["x", "y"],
    },
    handler=lambda x, y: desktop.mouse_move(x, y),
)

registry.register(
    name="mouse_scroll",
    description="滚动鼠标滚轮。正数=上滚，负数=下滚。",
    parameters={
        "type": "object",
        "properties": {
            "amount": {"type": "integer", "description": "滚动量 (正=上, 负=下)"},
        },
        "required": ["amount"],
    },
    handler=lambda amount: desktop.mouse_scroll(amount),
)

registry.register(
    name="get_mouse_position",
    description="获取当前鼠标位置坐标",
    parameters={"type": "object", "properties": {}},
    handler=lambda: desktop.get_mouse_position(),
)


# ============================================================
# 键盘工具
# ============================================================

registry.register(
    name="type_text",
    description="在当前焦点位置输入文字",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要输入的文字"},
        },
        "required": ["text"],
    },
    handler=lambda text: desktop.type_text(text),
)

registry.register(
    name="key_press",
    description="按下指定按键。常用键: enter, tab, escape, backspace, space, up, down, left, right",
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "键名"},
        },
        "required": ["key"],
    },
    handler=lambda key: desktop.key_press(key),
)

registry.register(
    name="hotkey",
    description="按下组合快捷键。如 ['ctrl', 'c'] 表示复制。",
    parameters={
        "type": "object",
        "properties": {
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "键名列表，如 ['ctrl', 'c']",
            },
        },
        "required": ["keys"],
    },
    handler=lambda keys: desktop.hotkey(*keys),
)


# ============================================================
# 应用/窗口工具
# ============================================================

registry.register(
    name="open_app",
    description="打开指定应用程序",
    parameters={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "应用名，如 firefox, code, terminal"},
        },
        "required": ["app_name"],
    },
    handler=lambda app_name: desktop.open_app(app_name),
)


# ============================================================
# 视觉工具
# ============================================================

registry.register(
    name="screenshot",
    description="截取当前屏幕，返回截图文件路径。用于查看屏幕上有什么内容。",
    parameters={"type": "object", "properties": {}},
    handler=lambda: json.dumps({"path": vision.screenshot(), "screen_size": vision.get_screen_size()}),
)

registry.register(
    name="get_screen_size",
    description="获取屏幕分辨率",
    parameters={"type": "object", "properties": {}},
    handler=lambda: desktop.get_screen_size(),
)

registry.register(
    name="wait",
    description="等待指定秒数。用于等待应用启动或页面加载。",
    parameters={
        "type": "object",
        "properties": {
            "seconds": {"type": "number", "description": "等待秒数"},
        },
        "required": ["seconds"],
    },
    handler=lambda seconds: desktop.wait(seconds),
)


print(f"✅ 已注册 {len(registry.list_tools())} 个工具 (含桌面操作)")
