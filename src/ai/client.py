"""AIClient:Anthropic Messages 协议 LLM 客户端,api_key_env + base_url 适配多 provider,统一 /v1/messages。"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from anthropic import APIConnectionError, APIStatusError, AsyncAnthropic, RateLimitError
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# 可重试的瞬时异常:连接/限流/5xx(4xx 认证/参数错误不重试)
_RETRYABLE = (APIConnectionError, RateLimitError, TimeoutError)

# Anthropic 协议必填 max_tokens;分类/摘要的输出含 reasoning 计入,8192 富余
_DEFAULT_MAX_TOKENS = 8_192


def _is_retryable(exc: Exception) -> bool:
    """判断是否为可重试的瞬时错误:连接/限流/超时/5xx。"""
    if isinstance(exc, _RETRYABLE):
        return True
    return bool(isinstance(exc, APIStatusError) and exc.status_code >= 500)


@dataclass
class AIClientConfig:
    """AI 客户端配置:provider + model + api_key_env + base_url + 并发参数。

    示例:
        cfg = AIClientConfig(provider="anthropic", model="glm-5.3-flash", api_key_env="OPENAI_API_KEY")
    """

    provider: str
    model: str
    api_key_env: str
    base_url: str | None = None
    analysis_concurrency: int = 5


def _normalize_base_url(base_url: str) -> str:
    """规整 base_url:anthropic SDK 自行拼 /v1/messages,配置里的 /v1 后缀要去掉。

    兼容两种 secret 形态(带 /v1 的 openai 风格、不带的裸网关地址),secret 值不可读,
    这里统一收敛成 SDK 期望的形态。
    """
    trimmed = base_url.rstrip("/")
    if trimmed.endswith("/v1"):
        trimmed = trimmed[: -len("/v1")]
    return trimmed


class AIClient:
    """Anthropic Messages 协议 LLM 客户端:complete() 调用 /v1/messages 返回文本。

    网关认证走 Authorization: Bearer(auth_token 参数),不认 anthropic 默认的 x-api-key;
    响应体是 content blocks,正文取全部 text block 拼接(reasoning/thinking block 不进正文)。
    """

    def __init__(self, config: AIClientConfig):
        """从 config 读取 API key(从 api_key_env 指定的环境变量),构造 AsyncAnthropic 客户端。"""
        self.config = config
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise ValueError(
                f"Environment variable {config.api_key_env} is not set. "
                f"Please set it in .env or your environment."
            )
        self.api_key = api_key
        self._client = AsyncAnthropic(
            auth_token=api_key,
            base_url=_normalize_base_url(config.base_url) if config.base_url else None,
            timeout=60.0,  # 避免 Tier1 并发场景慢请求阻塞 semaphore
        )

    async def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int | None = None,
    ) -> str:
        """调用 LLM,返回文本响应(system + user 单轮)。

        max_tokens: None 时用 _DEFAULT_MAX_TOKENS(Anthropic 协议必填)。
        """
        # 网络重试:连接/限流/5xx 指数退避(最多 3 次),4xx 认证/参数错误不重试
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception(_is_retryable),
            reraise=True,
        ):
            with attempt:
                response = await self._client.messages.create(
                    model=self.config.model,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    max_tokens=max_tokens if max_tokens is not None else _DEFAULT_MAX_TOKENS,
                )
                return "".join(block.text for block in response.content if block.type == "text")
        return ""  # 不可达(tenacity reraise 或 return 在循环内)
