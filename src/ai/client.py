"""AIClient:OpenAI 兼容 LLM 客户端,支持 OpenAI/Claude/Gemini/DeepSeek/Doubao/MiniMax/Ollama 等。

借鉴 Horizon src/ai/client.py:通过 api_key_env + base_url 适配多 provider,
所有 OpenAI 兼容端点共用 /v1/chat/completions 接口。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class AIClientConfig:
    """AI 客户端配置:provider + model + api_key_env + base_url + 并发/节流参数。

    示例:
        cfg = AIClientConfig(provider="openai", model="gpt-4o-mini", api_key_env="OPENAI_API_KEY")
    """

    provider: str
    model: str
    api_key_env: str
    base_url: str | None = None
    analysis_concurrency: int = 5
    throttle_sec: float = 0.0


class AIClient:
    """OpenAI 兼容 LLM 客户端:complete() 调用 /v1/chat/completions 返回文本。

    所有 OpenAI 兼容 provider(OpenAI/DeepSeek/Gemini/Ollama 等)共用此客户端,
    仅靠 base_url + api_key + model 三参数差异化。
    """

    def __init__(self, config: AIClientConfig):
        """从 config 读取 API key(从 api_key_env 指定的环境变量),构造 AsyncOpenAI 客户端。"""
        self.config = config
        # TODO: AIClientConfig.throttle_sec 从未消费,应在此处或调用方实现节流,或从配置删除
        # TODO: AsyncOpenAI 未传 timeout 参数,默认 600s,Tier1 批量场景慢请求会阻塞 semaphore
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise ValueError(
                f"Environment variable {config.api_key_env} is not set. "
                f"Please set it in .env or your environment."
            )
        self.api_key = api_key
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=config.base_url,
        )

    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """调用 LLM,返回文本响应(system + user 两条消息)。

        temperature: 0.7 默认(创造性),0 用于 JSON 修复重试。
        max_tokens: None 时由模型自行决定。
        """
        response = await self._client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
