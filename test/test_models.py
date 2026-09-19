"""模型层测试:ContentItem / RSSSourceConfig / CategoryConfig / ContentAnalysis。"""
from datetime import datetime, timezone

from src.models import (
    CategoryConfig,
    ContentAnalysis,
    ContentItem,
    ItemProcessing,
    RSSSourceConfig,
    SourceType,
)


def test_content_item_minimal():
    """ContentItem 最小字段可构造。"""
    item = ContentItem(
        id="rss_test_abc",
        source_type=SourceType.RSS,
        title="测试标题",
        url="https://example.com/post",
        content="正文",
        author="作者",
        published_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
    )
    assert item.category is None
    assert item.metadata == {}
    assert item.processing is None


def test_content_item_with_category_hint_and_metadata():
    """源级 category hint 与 metadata 可携带。"""
    item = ContentItem(
        id="rss_test_abc",
        source_type=SourceType.RSS,
        title="测试",
        url="https://example.com/post",
        content="正文",
        author="作者",
        published_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
        category="ai-research/ai-vendor",
        metadata={"feed_name": "Anthropic", "tags": ["llm", "safety"]},
    )
    assert item.category == "ai-research/ai-vendor"
    assert item.metadata["tags"] == ["llm", "safety"]


def test_rss_source_config_defaults():
    """RSSSourceConfig enabled 默认 True,content_extractor 默认 None。"""
    cfg = RSSSourceConfig(
        name="Anthropic News",
        url="https://www.anthropic.com/news/rss.xml",
        category="ai-research/ai-vendor",
    )
    assert cfg.enabled is True
    assert cfg.content_extractor is None


def test_rss_source_config_disabled():
    """enabled 可被显式关闭。"""
    cfg = RSSSourceConfig(
        name="Dead Feed",
        url="https://example.com/feed.xml",
        category="tech-news/cn-news",
        enabled=False,
    )
    assert cfg.enabled is False


def test_category_config_reserved_finance_disabled():
    """财经预留分类 enabled 默认 False。"""
    cfg = CategoryConfig(
        name="finance",
        enabled=False,
        display_name="财经",
        threshold=6.0,
        digest_limit=3,
        children=[],
    )
    assert cfg.enabled is False
    assert cfg.display_name == "财经"


def test_category_config_with_children():
    """ai-research 分类含三个子类。"""
    cfg = CategoryConfig(
        name="ai-research",
        enabled=True,
        display_name="AI 研究",
        threshold=7.0,
        digest_limit=8,
        children=["ai-vendor", "ai-researcher", "ai-papers"],
    )
    assert len(cfg.children) == 3
    assert cfg.threshold == 7.0


def test_content_analysis_score_and_tags():
    """Tier1 输出:分类路径 + 分数 + 摘要 + 标签。"""
    analysis = ContentAnalysis(
        category_path="ai-research/ai-papers",
        score=8.5,
        summary="一句话摘要",
        tags=["llm", "reasoning"],
    )
    assert analysis.score == 8.5
    assert analysis.tags == ["llm", "reasoning"]
    assert analysis.reason is None


def test_item_processing_holds_tier1_analysis():
    """ItemProcessing 容纳 Tier1 分析结果。"""
    proc = ItemProcessing(
        analysis=ContentAnalysis(
            category_path="research/arxiv-cs",
            score=7.0,
            summary="新论文",
            tags=["transformer"],
        ),
    )
    assert proc.analysis is not None
    assert proc.analysis.score == 7.0


def test_source_type_is_str_enum():
    """SourceType 是 str enum,值可序列化为字符串。"""
    assert SourceType.RSS == "rss"
    assert SourceType.API == "api"
