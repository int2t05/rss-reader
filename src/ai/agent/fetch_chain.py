"""FetchChain 降级链:Firecrawl(可选)→ trafilatura → httpx+regex,首个成功返回。

借鉴 Cognik server/internal/infra/adapter/fetch_client.go:32-64 的 FetchChain 模式。
内置 SSRF 防护:调用后端前 validate_url,拒绝 localhost/内网/云元数据。
"""

from __future__ import annotations

import logging
from typing import Protocol

from src.ai.agent.ssrf import validate_url

logger = logging.getLogger(__name__)


class FetchClient(Protocol):
    """抓取后端协议:返回网页正文 Markdown。"""

    async def fetch(self, url: str) -> str: ...


class FirecrawlClient:
    """Firecrawl 抓取后端:JS 渲染 + 干净 Markdown,需要 FIRECRAWL_API_KEY。"""

    def __init__(self) -> None:
        import os

        api_key = os.environ.get("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY environment variable is not set")
        self._api_key = api_key
        self._base_url = "https://api.firecrawl.dev/v1"

    async def fetch(self, url: str) -> str:
        """调用 Firecrawl /scrape 接口,返回 Markdown 正文。"""
        import httpx

        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            response = await client.post(
                f"{self._base_url}/scrape",
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                json={"url": url, "formats": ["markdown"]},
            )
            response.raise_for_status()
            data = response.json()
        return data.get("data", {}).get("markdown", "") or ""


class TrafilaturaClient:
    """trafilatura 抓取后端:零配置,从 HTML 提取正文。"""

    async def fetch(self, url: str) -> str:
        """httpx 抓取 HTML,trafilatura 提取正文。"""
        import asyncio

        import httpx
        import trafilatura

        def _sync_extract(html: str) -> str:
            return trafilatura.extract(html) or ""

        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            html = response.text

        # trafilatura.extract 是 CPU 密集,在 thread executor 中调用
        return await asyncio.to_thread(_sync_extract, html)


class LocalHttpClient:
    """本地 HTTP 抓取后端:最终兜底,httpx + 简单 HTML→text 正则。"""

    async def fetch(self, url: str) -> str:
        """httpx 抓取,正则去标签,返回纯文本。"""
        import re

        import httpx

        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            html = response.text

        # 去 script/style
        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # 去标签
        text = re.sub(r"<[^>]+>", " ", html)
        # 压缩空白
        text = re.sub(r"\s+", " ", text).strip()
        return text[:12000]  # 截断,控制 LLM 输入长度


class FetchChain:
    """抓取降级链:内置 SSRF 防护,按优先级尝试后端,首个成功返回。

    示例:
        chain = FetchChain.build_default(firecrawl_api_key=os.environ.get("FIRECRAWL_API_KEY"))
        markdown = await chain.fetch("https://example.com/post")
    """

    def __init__(self, backends: list[FetchClient]):
        self._backends = backends

    @classmethod
    def build_default(cls, firecrawl_api_key: str | None = None) -> "FetchChain":
        """构建默认降级链:Firecrawl(若有 key)→ trafilatura → httpx+regex。"""
        backends: list[FetchClient] = []
        if firecrawl_api_key:
            try:
                backends.append(FirecrawlClient())
            except ValueError:
                logger.info("FIRECRAWL_API_KEY invalid, skipping Firecrawl backend")
        backends.append(TrafilaturaClient())  # 零配置
        backends.append(LocalHttpClient())    # 永远兜底
        return cls(backends)

    async def fetch(self, url: str) -> str:
        """SSRF 防护 + 降级链抓取:首个成功返回,全部失败返回空字符串。"""
        # TODO: 仅验证入口 URL,后端 follow_redirects=True 的重定向目标不经 SSRF 校验,可绕过
        validate_url(url)  # SSRF 防护,失败抛 ValidationError

        for backend in self._backends:
            try:
                content = await backend.fetch(url)
                if content:
                    return content
                logger.debug("Backend %s returned empty content", backend.__class__.__name__)
            except Exception as e:
                logger.warning("Backend %s failed: %s", backend.__class__.__name__, e)
                continue
        return ""
