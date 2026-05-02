"""
Tool Registry — 工具注册中心

核心概念：
- 每个工具 = 一个 Python 函数 + 一个 JSON Schema 描述
- Registry 管理所有工具的注册、查找、执行
- LLM 通过 JSON Schema 知道有哪些工具可用
- LLM 返回 tool_call，Registry 路由到对应函数执行
"""

import json
from typing import Any, Callable


class Tool:
    """单个工具的封装"""

    def __init__(self, name: str, description: str, parameters: dict, handler: Callable):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler  # 实际执行的 Python 函数

    def to_schema(self) -> dict:
        """转换成 OpenAI tools 格式，传给 LLM"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }

    def execute(self, **kwargs) -> str:
        """执行工具，返回结果字符串"""
        return self.handler(**kwargs)


class ToolRegistry:
    """工具注册中心 — 管理所有工具"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, name: str, description: str, parameters: dict, handler: Callable):
        """注册一个新工具"""
        self._tools[name] = Tool(name, description, parameters, handler)

    def get(self, name: str) -> Tool | None:
        """根据名字查找工具"""
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """列出所有已注册工具"""
        return list(self._tools.values())

    def to_schemas(self) -> list[dict]:
        """生成所有工具的 JSON Schema，传给 LLM"""
        return [t.to_schema() for t in self._tools.values()]

    def execute(self, name: str, arguments: str) -> str:
        """
        执行工具调用

        参数:
            name:      工具名 (LLM 返回的 tool_call.function.name)
            arguments: JSON 字符串参数 (LLM 返回的 tool_call.function.arguments)
        """
        tool = self.get(name)
        if not tool:
            return json.dumps({"error": f"工具 '{name}' 不存在"})

        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
            result = tool.execute(**args)
            return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})


# 全局注册中心实例
registry = ToolRegistry()
