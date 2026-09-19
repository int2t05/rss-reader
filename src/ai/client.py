"""AIClient:OpenAI 兼容 LLM 客户端,支持 OpenAI/Claude/Gemini/DeepSeek/Doubao/MiniMax/Ollama 等。

借鉴 Horizon src/ai/client.py:通过 api_key_env + base_url 适配多 provider,
所有 OpenAI 兼容端点共用 /v1/chat/completions 接口。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from openai import APIConnectionError, APIStatusError, AsyncOpenAI, RateLimitError
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# 可重试的瞬时异常:连接/限流/5xx(4xx 认证/参数错误不重试)
_RETRYABLE = (APIConnectionError, RateLimitError, TimeoutError)


def _is_retryable(exc: Exception) -> bool:
    """判断是否为可重试的瞬时错误:连接/限流/超时/5xx。"""
    if isinstance(exc, _RETRYABLE):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code >= 500:
        return True
    return False


@dataclass
class AIClientConfig:
    """AI 客户端配置:provider + model + api_key_env + base_url + 并发参数。

    示例:
        cfg = AIClientConfig(provider="openai", model="gpt-4o-mini", api_key_env="OPENAI_API_KEY")
    """

    provider: str
    model: str
    api_key_env: str
    base_url: str | None = None
    analysis_concurrency: int = 5


class AIClient:
    """OpenAI 兼容 LLM 客户端:complete() 调用 /v1/chat/completions 返回文本。

    所有 OpenAI 兼容 provider(OpenAI/DeepSeek/Gemini/Ollama 等)共用此客户端,
    仅靠 base_url + api_key + model 三参数差异化。
    """

    def __init__(self, config: AIClientConfig):
        """从 config 读取 API key(从 api_key_env 指定的环境变量),构造 AsyncOpenAI 客户端。"""
        self.config = config
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
            timeout=60.0,  # 避免 Tier1 并发场景慢请求阻塞 semaphore
        )

    async def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """调用 LLM,返回文本响应(system + user 单轮)。

        temperature: 0.7 默认(创造性),0 用于 JSON 修复重试。
        max_tokens: None 时由模型自行决定。
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        # 网络重试:连接/限流/5xx 指数退避(最多 3 次),4xx 认证/参数错误不重试
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception(_is_retryable),
            reraise=True,
        ):
            with attempt:
                response = await self._client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content or ""
        return ""  # 不可达(tenacity reraise 或 return 在循环内)
