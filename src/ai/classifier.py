"""ContentClassifier:Tier1 分类+打分,单次 LLM 调用合并分类与打分,JSON 修复重试。

借鉴 Horizon src/ai/analyzer.py:并发控制(Semaphore)+ JSON 修复重试(temperature=0)。
与 Horizon 的差异:合并分类与打分为单次调用(减半 LLM 调用量)。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)

from src.ai.client import AIClient
from src.ai.prompting.classification import (
    analysis_system_prompt,
    analysis_user_prompt,
)
from src.ai.utils import parse_json_response
from src.models import ContentAnalysis, ContentItem
from src.processing.categories import CategoryRegistry

logger = logging.getLogger(__name__)

_DEFAULT_ANALYSIS_MAX_CHARS = 1000


class ContentClassifier:
    """Tier1 分类器:单次 LLM 调用完成分类+打分,JSON 修复重试一次。

    示例:
        classifier = ContentClassifier(client, registry)
        await classifier.classify_and_score(item)
        # item.processing.analysis 现在包含 category_path + score + summary + tags
    """

    def __init__(
        self,
        ai_client: AIClient,
        categories: CategoryRegistry,
        console: Optional[Console] = None,
    ):
        """指定 AI 客户端与分类注册表,console 用于进度条(可选)。"""
        self.client = ai_client
        self.categories = categories
        self.console = console or Console(stderr=True)

    async def classify_and_score(self, item: ContentItem) -> None:
        """单次 LLM 调用分类+打分,失败时一次修复重试(temperature=0)。

        最终失败时写入默认 analysis(score=0.0),不抛异常。
        注意:classify_and_score 自身不捕获 LLM 异常,仅在 classify_batch 中被 try/except 包裹;
        直接调用时需自行处理网络/API 异常。
        """
        category_tree = self.categories.category_tree_json()
        system_prompt = analysis_system_prompt(category_tree)
        user_prompt = analysis_user_prompt(
            title=item.title,
            content=item.content,
            feed_name=item.metadata.get("feed_name", "Unknown"),
            category_hint=item.category,
            max_chars=_DEFAULT_ANALYSIS_MAX_CHARS,
        )

        response = await self.client.complete(system=system_prompt, user=user_prompt)
        result = self._parse_analysis(response)

        if result is None:
            # 修复重试:temperature=0 + 修复提示
            logger.warning("First parse failed for %s, retrying with temperature=0", item.id)
            repair_response = await self.client.complete(
                system=system_prompt,
                user=(
                    user_prompt
                    + "\n\n你上次的响应不是合法 JSON。请仅输出 JSON 对象,包含 "
                    'category/score/summary/tags 字段。'
                ),
                temperature=0,
            )
            result = self._parse_analysis(repair_response)

        if result is None:
            logger.warning("Could not parse analysis for %s after retry, using defaults", item.id)
            result = ContentAnalysis(
                category_path=item.category or "unknown",
                score=0.0,
                summary=item.title,
                tags=[],
                reason="Analysis response parse failed",
            )

        if item.processing is None:
            from src.models import ItemProcessing

            item.processing = ItemProcessing()
        item.processing.analysis = result

    def _parse_analysis(self, response: str) -> ContentAnalysis | None:
        """从 LLM 响应解析 ContentAnalysis,失败返回 None。"""
        parsed = parse_json_response(response)
        if not isinstance(parsed, dict):
            return None
        try:
            category = parsed.get("category", "")
            score = parsed.get("score")
            if score is None:
                return None
            return ContentAnalysis(
                category_path=str(category),
                score=float(score),
                summary=str(parsed.get("summary", "")),
                tags=list(parsed.get("tags", [])),
                reason=parsed.get("reason"),
            )
        except (TypeError, ValueError) as e:
            logger.warning("Analysis parse error: %s", e)
            return None

    async def classify_batch(self, items: list[ContentItem]) -> list[ContentItem]:
        """并发分类批量 item,并发度由 AIClientConfig.analysis_concurrency 控制。

        单条失败不影响其他条目,失败条目写入默认 analysis。
        """
        concurrency = max(self.client.config.analysis_concurrency, 1)
        semaphore = asyncio.Semaphore(concurrency)

        async def _process(item: ContentItem, progress_task) -> ContentItem:
            async with semaphore:
                try:
                    await self.classify_and_score(item)
                except Exception as e:
                    logger.error("Error classifying item %s: %s", item.id, e)
                    if item.processing is None:
                        from src.models import ItemProcessing

                        item.processing = ItemProcessing()
                    item.processing.analysis = ContentAnalysis(
                        category_path=item.category or "unknown",
                        score=0.0,
                        summary=item.title,
                        tags=[],
                        reason=f"Classification failed: {e}",
                    )
            progress.advance(progress_task)
            return item

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task("Classifying", total=len(items))
            coros = [_process(item, task) for item in items]
            results = await asyncio.gather(*coros)

        logger.info("Tier1 classified %d items", len(results))
        return list(results)
