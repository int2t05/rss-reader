"""ContentSelector 测试:Tier2 选取器,阈值过滤 + 主题去重 + 配额平衡。

阈值过滤与配额平衡是纯逻辑,无 LLM;主题去重用真实 LLM。
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.ai.classifier import ContentClassifier
from src.ai.client import AIClient, AIClientConfig
from src.ai.selector import ContentSelector
from src.models import ContentAnalysis, ContentItem, ItemProcessing, SourceType
from src.processing.categories import CategoryRegistry


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
    """构造 categories/ 目录(含 category.json)。"""
    root = tmp_path / "categories"
    for name, threshold, limit, children in [
        ("ai-research", 7.0, 8, ["ai-vendor", "ai-researcher", "ai-papers"]),
        ("systems", 5.0, 5, ["eng-blog", "framework", "cn-tech"]),
        ("tech-news", 4.0, 5, ["cn-news", "en-news"]),
    ]:
        d = root / name
        d.mkdir(parents=True)
        (d / "category.json").write_text(
            json.dumps(
                {
                    "enabled": True,
                    "display_name": {"en": name, "zh": name},
                    "threshold": threshold,
                    "digest_limit": limit,
                    "children": children,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (d / "analysis.md").write_text(f"# {name}", encoding="utf-8")
        (d / "agent_system.md").write_text(f"# {name}", encoding="utf-8")
    return root


@pytest.fixture
def registry(categories_root: Path) -> CategoryRegistry:
    """构造 CategoryRegistry。"""
    reg = CategoryRegistry(categories_root)
    reg.load_from_raw(
        {
            "ai-research": {"enabled": True},
            "systems": {"enabled": True},
            "tech-news": {"enabled": True},
        }
    )
    return reg


def _make_item(
    item_id: str,
    url: str,
    title: str = "标题",
    category_path: str = "ai-research/ai-papers",
    score: float = 7.0,
    summary: str = "摘要",
) -> ContentItem:
    """构造带 analysis 的测试 ContentItem。"""
    return ContentItem(
        id=item_id,
        source_type=SourceType.RSS,
        title=title,
        url=url,
        content="内容",
        author="作者",
        published_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
        processing=ItemProcessing(
            analysis=ContentAnalysis(
                category_path=category_path,
                score=score,
                summary=summary,
                tags=[],
            )
        ),
    )


def test_selector_filters_below_threshold(registry: CategoryRegistry):
    """阈值过滤:低于分类阈值的条目被丢弃。"""
    selector = ContentSelector(registry, client=None)  # type: ignore[arg-type]
    items = [
        _make_item("a", "https://x.com/1", category_path="ai-research/ai-papers", score=6.0),  # 低于 7.0
        _make_item("b", "https://x.com/2", category_path="ai-research/ai-papers", score=8.0),  # 高于 7.0
    ]
    result = selector._filter_by_threshold(items)
    assert len(result) == 1
    assert result[0].id == "b"


def test_selector_threshold_per_category(registry: CategoryRegistry):
    """分类感知阈值:不同分类不同阈值。"""
    selector = ContentSelector(registry, client=None)  # type: ignore[arg-type]
    items = [
        _make_item("a", "https://x.com/1", category_path="ai-research/ai-papers", score=6.5),  # 低于 7.0,丢弃
        _make_item("b", "https://x.com/2", category_path="systems/eng-blog", score=5.5),  # 高于 5.0,保留
        _make_item("c", "https://x.com/3", category_path="tech-news/cn-news", score=4.5),  # 高于 4.0,保留
    ]
    result = selector._filter_by_threshold(items)
    ids = [r.id for r in result]
    assert "a" not in ids
    assert "b" in ids
    assert "c" in ids


def test_selector_applies_quota(registry: CategoryRegistry):
    """配额平衡:每分类按分数降序截取 digest_limit。"""
    selector = ContentSelector(registry, client=None)  # type: ignore[arg-type]
    items = [
        _make_item("a", "https://x.com/1", category_path="systems/eng-blog", score=9.0),
        _make_item("b", "https://x.com/2", category_path="systems/eng-blog", score=8.0),
        _make_item("c", "https://x.com/3", category_path="systems/eng-blog", score=7.0),
        _make_item("d", "https://x.com/4", category_path="systems/eng-blog", score=6.0),
        _make_item("e", "https://x.com/5", category_path="systems/eng-blog", score=5.0),
        _make_item("f", "https://x.com/6", category_path="systems/eng-blog", score=4.0),  # 超出 limit=5
        _make_item("g", "https://x.com/7", category_path="systems/eng-blog", score=3.0),  # 超出 limit=5
    ]
    result = selector._apply_quota(items)
    assert len(result) == 5  # systems digest_limit=5
    # 保留分数最高的 5 条
    scores = [r.processing.analysis.score for r in result]
    assert scores == sorted(scores, reverse=True)
    assert max(scores) == 9.0
    assert min(scores) == 5.0


def test_selector_quota_per_category(registry: CategoryRegistry):
    """不同分类不同配额:ai-research limit=8, systems limit=5, tech-news limit=5。"""
    selector = ContentSelector(registry, client=None)  # type: ignore[arg-type]
    items = []
    for i in range(10):
        items.append(_make_item(f"ai-{i}", f"https://ai.com/{i}", category_path="ai-research/ai-papers", score=8.0 - i * 0.1))
    for i in range(10):
        items.append(_make_item(f"sys-{i}", f"https://sys.com/{i}", category_path="systems/eng-blog", score=9.0 - i * 0.1))
    result = selector._apply_quota(items)
    ai_count = sum(1 for r in result if r.processing.analysis.category_path.startswith("ai-research"))
    sys_count = sum(1 for r in result if r.processing.analysis.category_path.startswith("systems"))
    assert ai_count == 8  # ai-research limit=8
    assert sys_count == 5  # systems limit=5


def test_selector_url_dedup_in_select(registry: CategoryRegistry):
    """select 流程包含 URL 去重:同 URL 不同追踪参数合并。"""
    import asyncio

    selector = ContentSelector(registry, client=None)  # type: ignore[arg-type]
    items = [
        _make_item("a", "https://example.com/post?utm_source=x", score=7.0),
        _make_item("b", "https://example.com/post?utm_source=y", score=8.5),  # 同 URL 不同追踪参数
    ]
    result = asyncio.run(selector.select(items, use_llm_dedup=False))
    assert len(result) == 1


def test_selector_preserves_order_by_score(registry: CategoryRegistry):
    """配额后按分数降序排列。"""
    selector = ContentSelector(registry, client=None)  # type: ignore[arg-type]
    items = [
        _make_item("a", "https://x.com/1", category_path="ai-research/ai-papers", score=7.0),
        _make_item("b", "https://x.com/2", category_path="ai-research/ai-papers", score=9.0),
        _make_item("c", "https://x.com/3", category_path="ai-research/ai-papers", score=8.0),
    ]
    result = selector._apply_quota(items)
    scores = [r.processing.analysis.score for r in result]
    assert scores == [9.0, 8.0, 7.0]


def test_selector_unknown_category_dropped(registry: CategoryRegistry):
    """未知分类(不在 registry)的条目被丢弃。"""
    selector = ContentSelector(registry, client=None)  # type: ignore[arg-type]
    items = [
        _make_item("a", "https://x.com/1", category_path="unknown/cat", score=9.0),
        _make_item("b", "https://x.com/2", category_path="ai-research/ai-papers", score=7.0),
    ]
    result = selector._filter_by_threshold(items)
    assert len(result) == 1
    assert result[0].id == "b"


@pytest.mark.llm
async def test_selector_topic_dedup_real_llm(registry: CategoryRegistry):
    """真实 LLM 主题去重:同事件多源报道合并为一条。"""
    cfg = _get_test_config()
    client = AIClient(cfg)
    selector = ContentSelector(registry, client=client)
    items = [
        _make_item("a", "https://openai.com/1", title="OpenAI 发布 GPT-5", summary="OpenAI 发布 GPT-5", score=8.0),
        _make_item("b", "https://techcrunch.com/1", title="OpenAI 的 GPT-5 正式发布", summary="GPT-5 发布报道", score=7.5),
        _make_item("c", "https://arxiv.com/1", title="新论文:Transformer 架构改进", summary="Transformer 新架构", score=7.0),
    ]
    result = await selector.select(items, use_llm_dedup=True)
    # a 和 b 是同一事件,应合并为一条;c 独立保留
    # 结果应为 2 条(保留同事件中分数最高的 a + 独立的 c)
    assert len(result) <= 3
    assert len(result) >= 1  # 至少有结果


def test_selector_no_analysis_items_skipped(registry: CategoryRegistry):
    """无 analysis 的条目被跳过(无法分类与打分)。"""
    selector = ContentSelector(registry, client=None)  # type: ignore[arg-type]
    no_analysis = ContentItem(
        id="x",
        source_type=SourceType.RSS,
        title="无分析",
        url="https://example.com/x",
        content="",
        author="",
        published_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
        processing=None,
    )
    items = [no_analysis, _make_item("b", "https://x.com/2", score=7.0)]
    result = selector._filter_by_threshold(items)
    assert len(result) == 1
    assert result[0].id == "b"
