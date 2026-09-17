"""ContentSelector:Tier2 选取器,纯程序逻辑(URL 去重 + 阈值过滤 + 配额平衡)+ 可选主题去重。

四步流程:
1. 跨源 URL 去重(规范化 URL 合并,保留高分)
2. 分类感知阈值过滤(每分类独立 threshold)
3. 主题去重(可选,按父分类分组,LLM 判断同事件)
4. 分类配额平衡(每分类 digest_limit,按分数降序截取)

借鉴 Horizon merge_topic_duplicates:按分类分组降低 prompt 大小。
"""

from __future__ import annotations

import logging
from typing import Optional

from src.ai.client import AIClient
from src.ai.prompting.deduplication import (
    topic_dedup_system_prompt,
    topic_dedup_user_prompt,
)
from src.ai.utils import parse_json_response
from src.models import ContentItem
from src.processing.categories import CategoryRegistry
from src.processing.dedup import dedup_by_url, group_by_category

logger = logging.getLogger(__name__)


class ContentSelector:
    """Tier2 选取器:URL 去重 → 阈值过滤 → 主题去重 → 配额平衡。

    示例:
        selector = ContentSelector(registry, client=ai_client)
        selected = await selector.select(items)
        # selected 为 30-50 条精选条目,按分类分组、分数降序
    """

    def __init__(self, categories: CategoryRegistry, client: Optional[AIClient] = None):
        """指定分类注册表与 AI 客户端(主题去重时必需,纯逻辑步骤可传 None)。"""
        self.categories = categories
        self.client = client

    async def select(
        self,
        items: list[ContentItem],
        use_llm_dedup: bool = True,
    ) -> list[ContentItem]:
        """四步选取流程:URL 去重 → 阈值过滤 → 主题去重(可选)→ 配额平衡。

        use_llm_dedup=False 时跳过 LLM 主题去重,仅纯程序逻辑(用于测试/低成本场景)。
        """
        # 1. 跨源 URL 去重
        items = dedup_by_url(items)

        # 2. 分类感知阈值过滤
        items = self._filter_by_threshold(items)

        # 3. 主题去重(可选,需 LLM)
        if use_llm_dedup and self.client is not None and len(items) > 1:
            items = await self._topic_dedup(items)

        # 4. 分类配额平衡
        items = self._apply_quota(items)

        return items

    def _filter_by_threshold(self, items: list[ContentItem]) -> list[ContentItem]:
        """分类感知阈值过滤:每分类独立 threshold,低于阈值的丢弃。

        未知分类(不在 registry)的条目也被丢弃。
        """
        result: list[ContentItem] = []
        for item in items:
            if not item.processing or not item.processing.analysis:
                continue
            path = item.processing.analysis.category_path
            cat = self.categories.get_by_path(path)
            if cat is None:
                logger.debug("Dropping item %s: unknown category %s", item.id, path)
                continue
            if item.processing.analysis.score >= cat.threshold:
                result.append(item)
        return result

    async def _topic_dedup(self, items: list[ContentItem]) -> list[ContentItem]:
        """主题去重:按父分类分组,每组内 LLM 判断同事件,保留分数最高的。

        借鉴 Horizon merge_topic_duplicates,但按父分类分组降低 prompt 大小。
        """
        grouped = group_by_category(items, by_parent=True)
        result: list[ContentItem] = []

        for parent_cat, cat_items in grouped.items():
            if len(cat_items) <= 1:
                result.extend(cat_items)
                continue

            clusters = await self._cluster_by_topic(parent_cat, cat_items)
            for cluster in clusters:
                if not cluster:
                    continue
                # 每簇保留分数最高的
                best = max(
                    cluster,
                    key=lambda x: x.processing.analysis.score if x.processing and x.processing.analysis else 0.0,
                )
                result.append(best)

        return result

    async def _cluster_by_topic(
        self, parent_cat: str, items: list[ContentItem]
    ) -> list[list[ContentItem]]:
        """让 LLM 判断同组内哪些条目是同一事件,返回聚类。"""
        items_summary = "\n".join(
            f"{i + 1}. [ID: {it.id}] {it.title} {(it.processing.analysis.summary if it.processing and it.processing.analysis else '')[:60]}"
            for i, it in enumerate(items)
        )

        system_prompt = topic_dedup_system_prompt()
        user_prompt = topic_dedup_user_prompt(category=parent_cat, items_summary=items_summary)

        response = await self.client.complete(system=system_prompt, user=user_prompt, temperature=0)
        # TODO: parse_json_response 仅返回 dict,主题去重期望 list[list[str]],此处为 workaround;
        # 应在 ai/utils.py 增加 parse_json_array_response,消除此处脆弱解析
        parsed = parse_json_response(response)

        # parse_json_response 要求返回 dict,但此处期望 list;手动解析
        if parsed is not None:
            # 极少数 LLM 把数组包成 {"clusters": [...]}
            if "clusters" in parsed:
                clusters_raw = parsed["clusters"]
            else:
                clusters_raw = [list(parsed.values())]
        else:
            # 尝试直接解析为 JSON 数组
            import json

            try:
                clusters_raw = json.loads(response.strip().removeprefix("```json").removesuffix("```").strip())
            except (json.JSONDecodeError, ValueError):
                logger.warning("Topic dedup parse failed for %s, keeping all items", parent_cat)
                return [[item] for item in items]

        # 映射 ID → item
        id_to_item = {it.id: it for it in items}
        clusters: list[list[ContentItem]] = []
        seen_ids: set[str] = set()
        for group in clusters_raw:
            if not isinstance(group, list):
                continue
            cluster_items = [id_to_item[iid] for iid in group if iid in id_to_item and iid not in seen_ids]
            if cluster_items:
                clusters.append(cluster_items)
                seen_ids.update(it.id for it in cluster_items)

        # 未被任何簇包含的条目,各自成簇
        for it in items:
            if it.id not in seen_ids:
                clusters.append([it])

        return clusters

    def _apply_quota(self, items: list[ContentItem]) -> list[ContentItem]:
        """分类配额平衡:每分类按分数降序截取 digest_limit。"""
        grouped = group_by_category(items)
        result: list[ContentItem] = []
        for cat_path, cat_items in grouped.items():
            cat = self.categories.get_by_path(cat_path)
            limit = cat.digest_limit if cat else 5
            # 按分数降序
            cat_items.sort(
                key=lambda x: x.processing.analysis.score if x.processing and x.processing.analysis else 0.0,
                reverse=True,
            )
            result.extend(cat_items[:limit])
        # 最终按分数降序
        result.sort(
            key=lambda x: x.processing.analysis.score if x.processing and x.processing.analysis else 0.0,
            reverse=True,
        )
        return result
