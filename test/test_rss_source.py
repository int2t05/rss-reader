"""RSS 源抓取测试:真实抓取公开 RSS feed,验证 ContentItem 结构与日期过滤。

非 mock:抓取真实公开 RSS feed(hnrss.org / github.blog),验证端到端。
"""

import httpx
import pytest

from src.models import ContentItem, RSSSourceConfig, SourceType
from src.sources.base import Source
from src.sources.registry import SourceRegistry
from src.sources.rss import RSSSource
from src.sources.rsshub import build_source


@pytest.fixture
async def http_client():
    """共享 httpx 异步客户端。trust_env=False 避免系统代理干扰(Windows IE 代理)。"""
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        yield client


def test_rss_source_is_source_protocol():
    """RSSSource 符合 Source Protocol(category 属性 + fetch 方法)。"""
    cfg = RSSSourceConfig(name="Test", url="https://example.com/feed", category="test/sub")
    src = RSSSource(cfg, http_client=None)  # type: ignore[arg-type]
    assert isinstance(src, Source)
    assert src.category == "test/sub"
    assert callable(src.fetch)


def test_rsshub_source_when_no_base_url_skips():
    """rsshub_base_url=None 时,RSSHub 路由源(/ 开头)返回 None。"""
    cfg = RSSSourceConfig(name="Solidot", url="/solidot", category="tech-news/cn-news")
    src = build_source(cfg, rsshub_base_url=None, http_client=None)  # type: ignore[arg-type]
    assert src is None


def test_rsshub_source_when_base_url_prepends():
    """rsshub_base_url 存在时,/solidot 解析为 {base}/solidot。"""
    cfg = RSSSourceConfig(name="Solidot", url="/solidot", category="tech-news/cn-news")
    src = build_source(cfg, rsshub_base_url="https://rsshub.app", http_client=None)  # type: ignore[arg-type]
    assert src is not None
    assert isinstance(src, RSSSource)
    assert src.config.url == "https://rsshub.app/solidot"


def test_rsshub_source_passthrough_for_http_url():
    """http 开头的直链源不受 rsshub_base_url 影响。"""
    cfg = RSSSourceConfig(name="HN", url="https://hnrss.org/frontpage", category="dev-community/forums")
    src = build_source(cfg, rsshub_base_url="https://rsshub.app", http_client=None)  # type: ignore[arg-type]
    assert src is not None
    assert src.config.url == "https://hnrss.org/frontpage"


@pytest.mark.network
async def test_fetch_real_rss_returns_content_items(http_client: httpx.AsyncClient):
    """真实抓取 hnrss.org frontpage,返回非空 ContentItem 列表,字段完整。"""
    cfg = RSSSourceConfig(
        name="Hacker News",
        url="https://hnrss.org/frontpage",
        category="dev-community/forums",
    )
    src = RSSSource(cfg, http_client)
    items = await src.fetch()
    assert len(items) > 0, "hnrss.org frontpage 应返回非空条目"
    first = items[0]
    assert isinstance(first, ContentItem)
    assert first.source_type == SourceType.RSS
    assert first.title
    assert first.url.startswith("http")
    assert first.published_at is not None
    assert first.metadata.get("feed_name") == "Hacker News"


@pytest.mark.network
async def test_fetch_invalid_url_returns_empty_not_raises(http_client: httpx.AsyncClient):
    """无效 URL 不抛异常,返回空列表(单源失败不中断)。"""
    cfg = RSSSourceConfig(
        name="Bad",
        url="https://this-domain-does-not-exist-xyz123.invalid/feed.xml",
        category="test/sub",
    )
    src = RSSSource(cfg, http_client)
    items = await src.fetch()
    assert items == []


def test_source_registry_register_and_by_category():
    """SourceRegistry 注册源,按分类过滤。"""
    cfg1 = RSSSourceConfig(name="A", url="https://a.example.com/feed", category="ai-research/ai-vendor")
    cfg2 = RSSSourceConfig(name="B", url="https://b.example.com/feed", category="systems/eng-blog")
    s1 = RSSSource(cfg1, http_client=None)  # type: ignore[arg-type]
    s2 = RSSSource(cfg2, http_client=None)  # type: ignore[arg-type]
    reg = SourceRegistry()
    reg.register(s1)
    reg.register(s2)
    assert len(reg.all()) == 2
    ai = reg.by_category("ai-research")
    assert s1 in ai and s2 not in ai


@pytest.mark.network
async def test_fetch_arxiv_cs_ai_returns_items(http_client: httpx.AsyncClient):
    """真实抓取 arXiv cs.AI RSS,验证 arXiv 子类可订阅。"""
    cfg = RSSSourceConfig(
        name="arXiv cs.AI",
        url="https://rss.arxiv.org/rss/cs.AI",
        category="research/arxiv-cs",
    )
    src = RSSSource(cfg, http_client)
    items = await src.fetch()
    # arXiv RSS 可能为空(新论文每日更新),但抓取不应抛异常
    for it in items:
        assert it.source_type == SourceType.RSS
        assert it.category == "research/arxiv-cs"
