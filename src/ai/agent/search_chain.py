"""SearchChain 降级链:Exa(可选)→ DuckDuckGo(零配置兜底),首个成功返回。

借鉴 Cognik server/internal/infra/adapter/search_client.go:32-61 的 SearchChain 模式:
按优先级尝试后端,首个成功返回,全部失败返回空列表。末位必须是零配置兜底后端。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """单条搜索结果:title + url + snippet。"""

    title: str
    url: str
    snippet: str


class SearchClient(Protocol):
    """搜索后端协议:返回 SearchResult 列表。"""

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]: ...


class ExaClient:
    """Exa 语义搜索后端:需要 EXA_API_KEY。"""

    def __init__(self) -> None:
        import os

        api_key = os.environ.get("EXA_API_KEY")
        if not api_key:
            raise ValueError("EXA_API_KEY environment variable is not set")
        self._api_key = api_key
        self._base_url = "https://api.exa.ai"

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """调用 Exa /search 接口,x-api-key 认证。"""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._base_url}/search",
                headers={"x-api-key": self._api_key, "Content-Type": "application/json"},
                json={
                    "query": query,
                    "numResults": max_results,
                    "contents": {"text": {"maxCharacters": 200}},
                },
            )
            response.raise_for_status()
            data = response.json()

        results: list[SearchResult] = []
        for hit in data.get("results", []):
            title = hit.get("title", "")
            url = hit.get("url", "")
            snippet = (hit.get("text") or "")[:200]
            if url:
                results.append(SearchResult(title=title, url=url, snippet=snippet))
        return results


class DuckDuckGoClient:
    """DuckDuckGo 搜索后端:零配置兜底,用 ddgs 库。"""

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """调用 ddgs 库搜索,无需 API Key。"""
        from ddgs import DDGS

        results: list[SearchResult] = []
        # ddgs 是同步库,在 thread executor 中调用
        import asyncio

        def _sync_search() -> list[SearchResult]:
            with DDGS() as ddgs:
                hits = list(ddgs.text(query, max_results=max_results))
            return [
                SearchResult(
                    title=h.get("title", ""),
                    url=h.get("href") or h.get("url", ""),
                    snippet=h.get("body") or h.get("snippet", ""),
                )
                for h in hits
                if h.get("href") or h.get("url")
            ]

        return await asyncio.to_thread(_sync_search)


class SearchChain:
    """搜索降级链:按优先级尝试后端,首个成功返回,全部失败返回空列表。

    示例:
        chain = SearchChain.build_default(exa_api_key=os.environ.get("EXA_API_KEY"))
        results = await chain.search("query")
    """

    def __init__(self, backends: list[SearchClient]):
        self._backends = backends

    @classmethod
    def build_default(cls, exa_api_key: str | None = None) -> "SearchChain":
        """构建默认降级链:Exa(若有 key)→ DuckDuckGo(始终兜底)。"""
        backends: list[SearchClient] = []
        if exa_api_key:
            try:
                backends.append(ExaClient())
            except ValueError:
                logger.info("EXA_API_KEY invalid, skipping Exa backend")
        backends.append(DuckDuckGoClient())  # 永远兜底
        return cls(backends)

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """按优先级尝试后端,首个成功(非空)返回;全部失败返回空列表。"""
        for backend in self._backends:
            try:
                results = await backend.search(query, max_results)
                if results:
                    return results
                logger.debug("Backend %s returned empty results", backend.__class__.__name__)
            except Exception as e:
                logger.warning("Backend %s failed: %s", backend.__class__.__name__, e)
                continue
        return []
