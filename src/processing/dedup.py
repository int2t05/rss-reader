"""Tier2 去重与分组:跨源 URL 去重(保留高分)+ 按分类路径分组。

URL 去重依赖 utils/url.normalize_url 规范化(去 fragment/追踪参数/统一 https/小写 host)。
分类分组支持按完整路径或父分类前缀分组(主题去重时按父分组降低 prompt 大小)。
"""

from __future__ import annotations

from collections import defaultdict

from src.models import ContentItem
from src.utils.url import normalize_url


def dedup_by_url(items: list[ContentItem]) -> list[ContentItem]:
    """跨源 URL 去重:规范化 URL 后按 URL 合并,同 URL 保留分数最高的。

    示例:
        items = [item_from_hn, item_from_reddit_same_url]
        result = dedup_by_url(items)  # 保留 score 更高的那条
    """
    by_url: dict[str, ContentItem] = {}
    for item in items:
        norm = normalize_url(item.url)
        existing = by_url.get(norm)
        if existing is None:
            by_url[norm] = item
            continue
        # 比较 score,保留高分
        existing_score = existing.processing.analysis.score if existing.processing and existing.processing.analysis else 0.0
        new_score = item.processing.analysis.score if item.processing and item.processing.analysis else 0.0
        if new_score > existing_score:
            by_url[norm] = item
    return list(by_url.values())


def group_by_category(
    items: list[ContentItem],
    by_parent: bool = False,
) -> dict[str, list[ContentItem]]:
    """按 analysis.category_path 分组。

    by_parent=False:按完整路径(如 "ai-research/ai-papers")分组
    by_parent=True: 按父分类前缀(如 "ai-research")分组,用于主题去重

    无 analysis 的条目被跳过(无分类路径)。
    """
    grouped: dict[str, list[ContentItem]] = defaultdict(list)
    for item in items:
        if not item.processing or not item.processing.analysis:
            continue
        path = item.processing.analysis.category_path
        if not path:
            continue
        key = path.split("/", 1)[0] if by_parent and "/" in path else path
        grouped[key].append(item)
    return dict(grouped)
