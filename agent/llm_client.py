"""
LLM Client — 调用大模型的统一接口

核心概念：
- 所有大模型都兼容 OpenAI 的 API 格式
- 一个 client 可以对接 OpenAI、DeepSeek、本地模型等
- 返回的都是统一的 message 格式
"""

import json
from openai import OpenAI


class LLMClient:
    """大模型调用客户端"""

    def __init__(self, api_key: str, base_url: str = None, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,  # None = OpenAI 官方，传值 = 兼容 API
        )

    def chat(self, messages: list[dict], tools: list[dict] = None) -> dict:
        """
        核心调用方法

        参数:
            messages: 对话历史 [{"role": "user", "content": "..."}]
            tools:    工具定义 [{"type": "function", "function": {...}}]

        返回:
            LLM 的响应 (message dict)
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
        }

        # 如果有工具，传给 LLM 让它决定是否调用
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"  # 让 LLM 自己决定要不要调工具

        response = self.client.chat.completions.create(**kwargs)

        # 提取第一条消息返回
        return response.choices[0].message


# 测试用
if __name__ == "__main__":
    import os

    client = LLMClient(
        api_key=os.getenv("OPENAI_API_KEY", "test"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
    )

    resp = client.chat([{"role": "user", "content": "你好，用一句话介绍你自己"}])
    print(resp.content)
