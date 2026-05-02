"""
Vision Layer — 截图 + 视觉分析

WSL 环境下用 scrot 或 import 命令截图
"""

import io
import base64
import json
import time
import subprocess
import os
import platform
from pathlib import Path

IS_WSL = "microsoft" in platform.uname().release.lower()
HAS_DISPLAY = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class VisionLayer:
    """视觉层 — 截图和屏幕分析"""

    def __init__(self, screenshot_dir: str = None):
        self.screenshot_dir = Path(screenshot_dir or "/tmp/my-agent/screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def screenshot(self, region: tuple = None) -> str:
        """
        截取屏幕

        WSL 方案:
        1. 有 DISPLAY → 用 scrot 或 import
        2. 无 DISPLAY → 用 PowerShell 截 Windows 屏幕
        """
        timestamp = int(time.time())
        filepath = self.screenshot_dir / f"screen_{timestamp}.png"

        try:
            if IS_WSL:
                return self._screenshot_wsl(filepath)
            elif HAS_DISPLAY:
                return self._screenshot_linux(filepath, region)
            else:
                return json.dumps({"error": "无图形环境，无法截图"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _screenshot_wsl(self, filepath: Path) -> str:
        """WSL 环境截图 — 调用 PowerShell"""
        ps_cmd = f'''
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
        $bitmap.Save("{filepath}")
        $graphics.Dispose()
        $bitmap.Dispose()
        '''
        try:
            result = subprocess.run(
                ["powershell.exe", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=10,
            )
            if filepath.exists():
                return str(filepath)
            return json.dumps({"error": f"PowerShell 截图失败: {result.stderr[:200]}"})
        except Exception as e:
            return json.dumps({"error": f"WSL 截图失败: {str(e)}"})

    def _screenshot_linux(self, filepath: Path, region: tuple = None) -> str:
        """Linux 原生截图"""
        try:
            # 尝试用 scrot
            cmd = ["scrot", str(filepath)]
            subprocess.run(cmd, capture_output=True, timeout=5)
            if filepath.exists():
                return str(filepath)
        except FileNotFoundError:
            pass

        try:
            # 尝试用 import (ImageMagick)
            cmd = ["import", "-window", "root", str(filepath)]
            subprocess.run(cmd, capture_output=True, timeout=5)
            if filepath.exists():
                return str(filepath)
        except FileNotFoundError:
            pass

        # 尝试用 pyautogui
        try:
            import pyautogui
            img = pyautogui.screenshot()
            img.save(str(filepath))
            return str(filepath)
        except Exception:
            pass

        return json.dumps({"error": "没有可用的截图工具，请安装 scrot 或 imagemagick"})

    def screenshot_base64(self, region: tuple = None) -> str:
        """截图并转成 base64"""
        path = self.screenshot()
        if path.startswith("{"):  # JSON error
            return ""

        try:
            if PIL_AVAILABLE:
                img = Image.open(path)
                img = self._resize(img, max_width=1280)
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                return base64.b64encode(buffer.getvalue()).decode()
            else:
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode()
        except Exception:
            return ""

    def get_screen_size(self) -> str:
        """获取屏幕尺寸"""
        if IS_WSL:
            try:
                result = subprocess.run(
                    ["powershell.exe", "-Command", "([System.Windows.Forms.Screen]::PrimaryScreen.Bounds).Width,([System.Windows.Forms.Screen]::PrimaryScreen.Bounds).Height"],
                    capture_output=True, text=True, timeout=5,
                )
                parts = result.stdout.strip().split(",")
                return json.dumps({"width": int(parts[0]), "height": int(parts[1])})
            except Exception:
                pass
        return json.dumps({"width": 1920, "height": 1080, "note": "默认值"})

    def _resize(self, img: 'Image.Image', max_width: int = 1280) -> 'Image.Image':
        if img.width <= max_width:
            return img
        ratio = max_width / img.width
        new_size = (max_width, int(img.height * ratio))
        return img.resize(new_size, Image.LANCZOS)
