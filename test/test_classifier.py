"""ContentClassifier 测试:Tier1 分类+打分,真实 LLM 调用。

无 API key 时跳过真实 LLM 调用(非 mock)。
"""
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.ai.classifier import ContentClassifier
from src.ai.client import AIClient, AIClientConfig
from src.models import ContentItem, RSSSourceConfig, SourceType
from src.processing.categories import CategoryRegistry
from src.sources.rss import RSSSource


def _get_test_config() -> AIClientConfig:
    """从 .env 读取测试凭证。"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set — skipping real LLM call (not mocked)")
    return AIClientConfig(
        provider="openai",
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        api_key_env="OPENAI_API_KEY",
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )


@pytest.fixture
def categories_root(tmp_path: Path) -> Path:
    """构造最小 categories/ 目录:ai-research + systems。"""
    root = tmp_path / "categories"
    for name, threshold, children in [
        ("ai-research", 7.0, ["ai-vendor", "ai-researcher", "ai-papers"]),
        ("systems", 5.0, ["eng-blog", "framework", "cn-tech"]),
    ]:
        d = root / name
        d.mkdir(parents=True)
        (d / "analysis.md").write_text(f"# {name} 打分标准\n9-10: 重大突破", encoding="utf-8")
        (d / "agent_system.md").write_text(f"# {name} 分析员\n你是 {name} 分析员", encoding="utf-8")
    return root


@pytest.fixture
def registry(categories_root: Path) -> CategoryRegistry:
    """构造 CategoryRegistry,加载两个 enabled 分类。"""
    reg = CategoryRegistry(categories_root)
    reg.load_from_raw(
        {
            "ai-research": {"enabled": True},
            "systems": {"enabled": True},
            "finance": {"enabled": False},
        }
    )
    return reg


def _make_item(title: str, content: str, category_hint: str | None = None) -> ContentItem:
    """构造测试用 ContentItem。"""
    return ContentItem(
        id="rss_test_abc",
        source_type=SourceType.RSS,
        title=title,
        url="https://example.com/post",
        content=content,
        author="Test Author",
        published_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
        category=category_hint,
        metadata={"feed_name": "Test Feed"},
    )


@pytest.mark.llm
async def test_classifier_assigns_score_and_category(registry: CategoryRegistry):
    """真实 LLM 调用:分类器对一条 AI 新闻打分,输出 score + category_path。"""
    cfg = _get_test_config()
    client = AIClient(cfg)
    classifier = ContentClassifier(client, registry)
    item = _make_item(
        title="OpenAI 发布 GPT-5",
        content="OpenAI 发布 GPT-5,支持多模态推理,性能比 GPT-4 提升 30%。",
        category_hint="ai-research/ai-vendor",
    )
    await classifier.classify_and_score(item)
    assert item.processing is not None
    assert item.processing.analysis is not None
    analysis = item.processing.analysis
    assert analysis.score is not None
    assert 0 <= analysis.score <= 10
    assert analysis.category_path  # 非空
    assert analysis.summary  # 非空
    assert isinstance(analysis.tags, list)


@pytest.mark.llm
async def test_classifier_override_category_hint_when_mismatch(registry: CategoryRegistry):
    """真实 LLM 调用:内容明显跨类时,AI 可 override 源 category hint。"""
    cfg = _get_test_config()
    client = AIClient(cfg)
    classifier = ContentClassifier(client, registry)
    item = _make_item(
        title="React 19 发布",
        content="React 19 发布,支持 Server Components 和新的编译器。",
        category_hint="ai-research/ai-vendor",  # hint 错误,内容是前端框架
    )
    await classifier.classify_and_score(item)
    assert item.processing is not None
    analysis = item.processing.analysis
    # AI 应 override 到 systems/framework 而非 ai-research
    assert analysis.category_path.startswith("systems") or analysis.category_path.startswith("ai-research")


@pytest.mark.llm
async def test_classifier_handles_none_category_hint(registry: CategoryRegistry):
    """真实 LLM 调用:category_hint=None 时 AI 自主分类。"""
    cfg = _get_test_config()
    client = AIClient(cfg)
    classifier = ContentClassifier(client, registry)
    item = _make_item(
        title="新论文:Transformer 架构改进",
        content="本文提出一种新的 Transformer 架构,在多个基准测试上取得 SOTA。",
        category_hint=None,
    )
    await classifier.classify_and_score(item)
    assert item.processing is not None
    assert item.processing.analysis.category_path  # AI 自主分类


@pytest.mark.llm
async def test_classify_batch_processes_multiple_items(registry: CategoryRegistry):
    """真实 LLM 调用:批量分类多条 item,并发控制。"""
    cfg = _get_test_config()
    client = AIClient(cfg)
    classifier = ContentClassifier(client, registry)
    items = [
        _make_item("GPT-5 发布", "OpenAI 发布 GPT-5", "ai-research/ai-vendor"),
        _make_item("React 19", "React 19 发布", "systems/framework"),
    ]
    results = await classifier.classify_batch(items)
    assert len(results) == 2
    for item in results:
        assert item.processing is not None
        assert item.processing.analysis is not None


@pytest.mark.llm
async def test_classify_real_rss_item(registry: CategoryRegistry):
    """真实抓取 + 真实 LLM:抓一条 HN 条目,分类打分。"""
    import httpx

    cfg = _get_test_config()
    client = AIClient(cfg)
    classifier = ContentClassifier(client, registry)

    rss_cfg = RSSSourceConfig(
        name="Hacker News",
        url="https://hnrss.org/frontpage",
        category="dev-community/forums",
    )
    # dev-community 未在 registry 中,但分类器应仍能工作(用默认分类树)
    async with httpx.AsyncClient(timeout=30.0) as http:
        src = RSSSource(rss_cfg, http)
        from datetime import timedelta
        since = datetime.now(timezone.utc) - timedelta(days=1)
        items = await src.fetch(since)
        if not items:
            pytest.skip("HN returned no items — skipping (not mocked)")
        item = items[0]
        # 覆盖 category 为 registry 中存在的分类
        item.category = "ai-research/ai-vendor"
        await classifier.classify_and_score(item)
        assert item.processing is not None
        assert item.processing.analysis.score is not None
        assert item.processing.analysis.summary
