"""Markdown 简报渲染测试:中文分类、新闻链接名与轻量日期信息。

纯逻辑测试,无网络无 LLM。用真实 ContentItem 数据验证渲染输出。
"""
from datetime import UTC, datetime

from src.models import (
    ContentAnalysis,
    ContentItem,
    ItemProcessing,
    SourceType,
)
from src.render.markdown import render_markdown


def _make_item(
    title: str = "测试标题",
    score: float = 8.0,
    category_path: str = "ai-research/ai-papers",
    summary: str = "一句话摘要",
    url: str = "https://example.com/post",
) -> ContentItem:
    """构造带 Tier1 analysis 的测试 ContentItem。"""
    return ContentItem(
        id="rss_test_abc",
        source_type=SourceType.RSS,
        title=title,
        url=url,
        content="内容",
        author="作者",
        published_at=datetime(2026, 9, 17, tzinfo=UTC),
        category=category_path,
        processing=ItemProcessing(
            analysis=ContentAnalysis(
                category_path=category_path,
                score=score,
                summary=summary,
                tags=["tag1", "tag2"],
            ),
        ),
    )


def test_render_markdown_contains_date():
    """简报包含日期标题。"""
    items = [_make_item()]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=UTC))
    assert "2026" in md
    assert "09" in md or "9" in md


def test_render_markdown_period_overrides_title_date():
    """区间回填:标题用合刊区间串,不再重复单日日期。"""
    md = render_markdown(
        [_make_item()],
        date=datetime(2026, 11, 2, tzinfo=UTC),
        period="2026-10-24 ~ 2026-11-02",
    )
    first = md.lstrip().splitlines()[0]
    assert "2026-10-24 ~ 2026-11-02" in first
    assert "· 2026-11-02" not in first


def test_render_markdown_contains_category_section():
    """分类标题使用配置提供的中文显示名。"""
    items = [_make_item(category_path="ai-research/ai-papers")]
    md = render_markdown(
        items,
        date=datetime(2026, 9, 17, tzinfo=UTC),
        category_labels={"ai-research": "AI 研究"},
    )
    assert "## AI 研究 {#ai-research}" in md
    assert "## ai-research" not in md


def test_render_markdown_uses_chinese_news_sentence_as_source_link():
    """简洁中文新闻句成为原文链接名与大纲标题,不重复显示旧字段。"""
    items = [
        _make_item(
            title="OpenAI announces GPT-5.6 with expanded capabilities",
            summary="OpenAI 发布 GPT-5.6，新增更强的多模态推理能力。",
        )
    ]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=UTC))
    assert "### [OpenAI 发布 GPT-5.6，新增更强的多模态推理能力。](https://example.com/post)" in md
    assert "OpenAI announces GPT-5.6" not in md
    assert "摘要" not in md
    assert "分数" not in md
    assert "标签" not in md


def test_render_markdown_hides_internal_score():
    """内部排序分数不出现在阅读页面。"""
    items = [_make_item(score=8.5)]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=UTC))
    assert "8.5" not in md
    assert "分数" not in md


def test_render_markdown_contains_item_date():
    """每条目用简体中文显示发布日期。"""
    items = [_make_item()]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=UTC))
    assert "发布于 9月17日" in md


def test_render_markdown_falls_back_to_source_title_when_summary_is_empty():
    """LLM 摘要缺失时仍保留可访问的原文链接。"""
    items = [_make_item(title="原始标题", summary="")]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=UTC))
    assert "### [原始标题](https://example.com/post)" in md


def test_render_markdown_groups_items_by_category():
    """同分类的多个条目归入同一分类节。"""
    items = [
        _make_item(title="条目A", summary="新闻A", category_path="ai-research/ai-papers"),
        _make_item(title="条目B", summary="新闻B", category_path="ai-research/ai-papers"),
        _make_item(title="条目C", summary="新闻C", category_path="systems/eng-blog"),
    ]
    md = render_markdown(
        items,
        date=datetime(2026, 9, 17, tzinfo=UTC),
        category_labels={"ai-research": "AI 研究", "systems": "系统工程"},
    )
    idx_a = md.find("新闻A")
    idx_b = md.find("新闻B")
    idx_c = md.find("新闻C")
    assert idx_a < idx_b  # 同分类相邻
    assert idx_c != -1


def test_render_markdown_empty_items():
    """空条目列表:简报仅含标题与说明。"""
    md = render_markdown([], date=datetime(2026, 9, 17, tzinfo=UTC))
    assert isinstance(md, str)
    assert len(md) > 0
    assert "2026" in md


def test_render_markdown_contains_chinese_title():
    """简报用中文标题(每日简报)。"""
    items = [_make_item()]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=UTC))
    assert "简报" in md or "日报" in md or "每日" in md


def test_render_markdown_hides_internal_tags():
    """标签用于筛选分析,不挤进每日阅读面。"""
    items = [_make_item()]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=UTC))
    assert "tag1" not in md
    assert "tag2" not in md


def test_render_markdown_escapes_link_special_chars():
    """新闻句/URL 含 ] 或 ) 时转义,不破坏 Markdown 链接语法。"""
    items = [_make_item(summary="GPT-5 (多模态) 发布 [更新]")]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=UTC))
    assert "GPT-5" in md
    assert "\\(多模态\\)" in md
    assert "\\[更新\\]" in md


def test_render_markdown_escapes_untrusted_html_and_nested_links():
    """RSS/LLM 文本不能注入原始 HTML 或危险 Markdown 链接。"""
    items = [_make_item(summary="<script>alert(1)</script> [点击](javascript:alert(1))")]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=UTC))

    assert "&lt;script&gt;" in md
    assert "[点击]" not in md
    assert "](javascript:" not in md.lower()


def test_render_markdown_rejects_non_http_item_urls():
    """外部 feed URL 不是 HTTP(S) 时不生成可执行链接。"""
    items = [_make_item(url="javascript:alert(1)")]
    md = render_markdown(items, date=datetime(2026, 9, 17, tzinfo=UTC))

    assert "(javascript:" not in md.lower()
    assert "(https://example.com/post)" not in md
