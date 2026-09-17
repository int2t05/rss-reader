"""源注册表:管理所有 Source 实例,支持按分类过滤。"""

from __future__ import annotations

from src.sources.base import Source


class SourceRegistry:
    """扁平源注册表:按分类过滤,供 orchestrator 并发抓取。"""

    def __init__(self) -> None:
        self._sources: list[Source] = []

    def register(self, source: Source) -> None:
        """注册单个源。"""
        self._sources.append(source)

    def all(self) -> list[Source]:
        """返回所有已注册源。"""
        return list(self._sources)

    def by_category(self, category_prefix: str) -> list[Source]:
        """按分类前缀过滤(如 "ai-research" 匹配 "ai-research/ai-vendor")。"""
        return [s for s in self._sources if s.category.startswith(category_prefix)]

    def __len__(self) -> int:
        return len(self._sources)
