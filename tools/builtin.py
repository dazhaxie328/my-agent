"""
内置工具集 — Agent 自带的基础工具

每个工具都是一个函数 + 注册调用
"""

import json
import subprocess
import math
from tools.registry import registry


# ============================================================
# 工具1: 计算器
# ============================================================
def calculator(expression: str) -> str:
    """安全的数学表达式计算"""
    try:
        # 只允许数学运算，不允许任意代码
        allowed = {
            "__builtins__": {},
            "abs": abs, "round": round,
            "min": min, "max": max,
            "sum": sum, "pow": pow,
            "int": int, "float": float,
            "math": math,
        }
        result = eval(expression, allowed)
        return json.dumps({"result": result})
    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="calculator",
    description="计算数学表达式。支持基本运算和 math 模块函数。",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式，如 '2+3*4' 或 'math.sqrt(144)'",
            }
        },
        "required": ["expression"],
    },
    handler=calculator,
)


# ============================================================
# 工具2: Shell 命令执行
# ============================================================
def run_command(command: str) -> str:
    """执行 shell 命令并返回输出"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return json.dumps({
            "stdout": result.stdout[:2000],  # 截断防止太长
            "stderr": result.stderr[:500],
            "returncode": result.returncode,
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "命令超时 (30s)"})
    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="run_command",
    description="执行 shell 命令。返回 stdout、stderr 和返回码。",
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "要执行的 shell 命令",
            }
        },
        "required": ["command"],
    },
    handler=run_command,
)


# ============================================================
# 工具3: 读取文件
# ============================================================
def read_file(path: str) -> str:
    """读取文件内容"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read(10000)  # 限制读取大小
        return json.dumps({"content": content, "truncated": len(content) >= 10000})
    except FileNotFoundError:
        return json.dumps({"error": f"文件不存在: {path}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="read_file",
    description="读取指定路径的文件内容",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文件路径",
            }
        },
        "required": ["path"],
    },
    handler=read_file,
)


# ============================================================
# 工具4: 写入文件
# ============================================================
def write_file(path: str, content: str) -> str:
    """写入内容到文件"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return json.dumps({"success": True, "path": path, "bytes_written": len(content)})
    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="write_file",
    description="将内容写入指定路径的文件（会覆盖已有内容）",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文件路径",
            },
            "content": {
                "type": "string",
                "description": "要写入的内容",
            }
        },
        "required": ["path", "content"],
    },
    handler=write_file,
)


print(f"✅ 已注册 {len(registry.list_tools())} 个内置工具")
