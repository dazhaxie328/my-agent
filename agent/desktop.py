"""
Desktop Layer — 桌面操作 (鼠标/键盘/窗口)

WSL 环境下自动降级: 没有图形界面时用 shell 命令替代
"""

import json
import time
import subprocess
import os
import platform

# 检测是否有图形环境
HAS_DISPLAY = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
IS_WSL = "microsoft" in platform.uname().release.lower()

# 尝试导入 pyautogui
try:
    if HAS_DISPLAY and not IS_WSL:
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05
        DESKTOP_AVAILABLE = True
    else:
        DESKTOP_AVAILABLE = False
except Exception:
    DESKTOP_AVAILABLE = False


class DesktopLayer:
    """桌面操作层 — 模拟人类操作"""

    # ============================================================
    # 鼠标操作
    # ============================================================

    def mouse_move(self, x: int, y: int, duration: float = 0.3) -> str:
        if not DESKTOP_AVAILABLE:
            return json.dumps({"error": "无图形环境，无法操作鼠标", "hint": "在 WSL 中需要安装 X Server 或使用 Windows 原生环境"})
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return json.dumps({"success": True, "action": "move", "x": x, "y": y})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def mouse_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> str:
        if not DESKTOP_AVAILABLE:
            return json.dumps({"error": "无图形环境，无法点击鼠标"})
        try:
            pyautogui.click(x, y, clicks=clicks, button=button)
            return json.dumps({"success": True, "action": "click", "x": x, "y": y, "button": button, "clicks": clicks})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def mouse_scroll(self, amount: int) -> str:
        if not DESKTOP_AVAILABLE:
            return json.dumps({"error": "无图形环境，无法滚动"})
        try:
            pyautogui.scroll(amount)
            return json.dumps({"success": True, "action": "scroll", "amount": amount})
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ============================================================
    # 键盘操作
    # ============================================================

    def type_text(self, text: str, interval: float = 0.02) -> str:
        if not DESKTOP_AVAILABLE:
            return json.dumps({"error": "无图形环境，无法打字"})
        try:
            pyautogui.typewrite(text, interval=interval)
            return json.dumps({"success": True, "action": "type", "length": len(text)})
        except Exception:
            try:
                pyautogui.write(text)
                return json.dumps({"success": True, "action": "type", "length": len(text)})
            except Exception as e:
                return json.dumps({"error": str(e)})

    def key_press(self, key: str) -> str:
        if not DESKTOP_AVAILABLE:
            return json.dumps({"error": "无图形环境，无法按键"})
        try:
            pyautogui.press(key)
            return json.dumps({"success": True, "action": "key_press", "key": key})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def hotkey(self, *keys) -> str:
        if not DESKTOP_AVAILABLE:
            return json.dumps({"error": "无图形环境，无法按快捷键"})
        try:
            pyautogui.hotkey(*keys)
            return json.dumps({"success": True, "action": "hotkey", "keys": list(keys)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ============================================================
    # 应用/命令操作 (跨平台)
    # ============================================================

    def open_app(self, app_name: str) -> str:
        """打开应用 — 支持 WSL (用 cmd.exe) 和 Linux"""
        try:
            if IS_WSL:
                # WSL: 用 cmd.exe /c start 打开 Windows 应用
                subprocess.Popen(
                    ["cmd.exe", "/c", "start", app_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            else:
                subprocess.Popen(
                    [app_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            time.sleep(1)
            return json.dumps({"success": True, "action": "open_app", "app": app_name, "env": "wsl" if IS_WSL else "linux"})
        except FileNotFoundError:
            return json.dumps({"error": f"找不到应用: {app_name}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def run_shell(self, command: str) -> str:
        """执行 shell 命令"""
        try:
            result = subprocess.run(
                command, shell=True,
                capture_output=True, text=True, timeout=30,
            )
            return json.dumps({
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:500],
                "returncode": result.returncode,
            })
        except subprocess.TimeoutExpired:
            return json.dumps({"error": "命令超时"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ============================================================
    # 辅助方法
    # ============================================================

    def get_mouse_position(self) -> str:
        if not DESKTOP_AVAILABLE:
            return json.dumps({"error": "无图形环境", "env": "wsl" if IS_WSL else "no_display"})
        x, y = pyautogui.position()
        return json.dumps({"x": x, "y": y})

    def get_screen_size(self) -> str:
        if not DESKTOP_AVAILABLE:
            return json.dumps({"width": 1920, "height": 1080, "note": "默认值，无图形环境"})
        w, h = pyautogui.size()
        return json.dumps({"width": w, "height": h})

    def wait(self, seconds: float) -> str:
        time.sleep(seconds)
        return json.dumps({"success": True, "waited": seconds})

    def get_status(self) -> dict:
        """返回桌面层状态"""
        return {
            "has_display": HAS_DISPLAY,
            "is_wsl": IS_WSL,
            "pyautogui_available": DESKTOP_AVAILABLE,
        }
