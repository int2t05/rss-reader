"""数据模型:ContentItem 及其处理结果,贯穿三段式 pipeline。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """信息源类型:RSS 为主要类型,API 为未来扩展预留。"""

    RSS = "rss"
    API = "api"


class RSSSourceConfig(BaseModel):
    """RSS 源配置:feeds/*.yml 中单条源的映射。

    示例:
        cfg = RSSSourceConfig(name="Anthropic", url="https://...", category="ai-research/ai-vendor")
    """

    name: str
    url: str
    category: str
    enabled: bool = True
    content_extractor: str | None = None


class CategoryConfig(BaseModel):
    """分类配置:分类树的节点,驱动 Tier2 阈值过滤与配额平衡。"""

    name: str
    enabled: bool
    display_name: str  # 中文显示名
    threshold: float
    digest_limit: int
    children: list[str] = Field(default_factory=list)


class ContentAnalysis(BaseModel):
    """Tier1 输出:分类路径 + 分数 + 摘要 + 标签。"""

    category_path: str
    score: float
    summary: str
    tags: list[str] = Field(default_factory=list)
    reason: str | None = None


class ItemProcessing(BaseModel):
    """单条 ContentItem 的处理中间态:Tier1 分析结果。"""

    analysis: ContentAnalysis | None = None


class ContentItem(BaseModel):
    """信息条目:Source 层产出,三段式 pipeline 的核心载体。

    category 字段为源级 category hint(如 "ai-research/ai-vendor"),
    Tier1 可 override,默认沿用。
    """

    id: str
    source_type: SourceType
    title: str
    url: str
    content: str
    author: str
    published_at: datetime
    category: str | None = None
    metadata: dict = Field(default_factory=dict)
    processing: ItemProcessing | None = None
